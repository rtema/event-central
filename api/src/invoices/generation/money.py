"""Monetary and VAT computation for invoice generation.

All arithmetic uses :class:`~decimal.Decimal` with banker-free ``ROUND_HALF_UP``
to two decimals, matching how invoice software and EN16931 validators expect
amounts to round.

Per the API spec the incoming ``pricePerUnit`` is **VAT-inclusive**, so the net
unit price is derived from the gross. Document totals are built bottom-up from
the VAT breakdown (taxable amount per category × rate), which is what EN16931's
business rules (BR-CO-*, BR-S-08, BR-E-08) require — not from a naive sum of
gross line amounts.
"""

from __future__ import annotations

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from src.invoices.generation.model import DocumentLine, TaxBreakdownEntry

_CENTS = Decimal("0.01")

# Default human-readable exemption reason for the German "Verein" case when the
# caller supplies neither a reason text nor a code (EN16931 BR-E-10 needs one).
DEFAULT_EXEMPTION_REASON = "Steuerbefreite Leistung gemäß § 4 UStG"


def money(value: object) -> Decimal:
    """Coerce to a 2-decimal Decimal, robust against float inputs."""
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(_CENTS, rounding=ROUND_HALF_UP)


def _rate(value: object) -> Decimal:
    return Decimal(str(value)).quantize(_CENTS, rounding=ROUND_HALF_UP)


def classify_tax(
    *,
    tax_type: str | None,
    rate: object,
    exemption_reason: str | None,
    exemption_reason_code: str | None,
) -> tuple[str, Decimal, str | None, str | None]:
    """Resolve (category, effective_rate, reason, reason_code) for a tax rate.

    ``exempt-verein`` (or any zero rate) maps to EN16931 category ``E`` at 0 %
    with an exemption reason; everything else is standard-rated ``S``.
    """
    r = _rate(rate)
    is_exempt = (tax_type == "exempt-verein") or r == Decimal("0.00")
    if is_exempt:
        reason = exemption_reason or DEFAULT_EXEMPTION_REASON
        return "E", Decimal("0.00"), reason, exemption_reason_code
    return "S", r, None, None


def build_line(
    *,
    position: int,
    name: str,
    quantity: object,
    price_per_unit_gross: object,
    category: str,
    rate: Decimal,
    exemption_reason: str | None = None,
    exemption_reason_code: str | None = None,
    ticket_label: str | None = None,
) -> DocumentLine:
    """Compute a single line's net/tax/gross from a VAT-inclusive unit price.

    IMPORTANT — rounding order: the line's gross total is derived as
    ``quantity * unit_gross``, rounded to the cent exactly once. Net and tax
    are then derived *from that already-rounded gross total*
    (``net = gross / factor``, ``tax = gross - net``) rather than from a
    per-unit net price that gets rounded before being multiplied by quantity.

    Rounding the *unit* net price first (``net_unit = round(unit_gross /
    factor)``) and then multiplying by quantity was the previous approach, and
    it's wrong: 19%/7% VAT divisions essentially never terminate, so
    ``net_unit`` almost always carries a sub-cent rounding error. Multiplying
    that error by ``quantity`` scales it up — for large quantities the line's
    reconstructed gross (``net_unit * qty`` grossed back up) can drift by many
    cents from ``quantity * price_per_unit_gross``, which is the amount that
    was actually charged. Rounding the total once, up front, keeps
    ``gross == quantity * price_per_unit_gross`` exactly and makes
    ``net + tax == gross`` hold by construction (via subtraction) instead of
    by coincidence.

    Note the SAME principle applies to ``price_per_unit_gross`` itself: it must
    stay full-precision (not pre-rounded to cents via ``money()``) until *after*
    it has been multiplied by quantity. The incoming unit price is not
    guaranteed to already be a whole number of cents (e.g. a unit price of
    ``0.5592`` split across a bulk quantity) — rounding it to ``0.56`` before
    multiplying by ``7`` gives ``3.92``, while the amount actually charged is
    ``7 * 0.5592 = 3.9144 -> 3.91``. Rounding the unit price early silently
    changes the total by a cent. Only ``gross`` (the product) gets rounded;
    the unit price is kept as an exact ``Decimal`` all the way through the
    multiplication.

    ``net_unit_price`` is still computed and returned (documents display it),
    but purely for presentation — it is never used to derive the totals below.
    """
    qty = Decimal(str(quantity))
    # Full precision — do NOT round this before multiplying by qty.
    raw_unit_gross = Decimal(str(price_per_unit_gross))
    factor = Decimal("1") + (rate / Decimal("100"))

    # Single rounding point for the line total — must equal qty * unit price
    # computed at full precision, matching what was actually charged.
    gross = money(raw_unit_gross * qty)

    net = money(gross / factor) if factor != 0 else gross
    tax = money(gross - net)  # by construction: net + tax == gross, always

    # Presentation-only rounded unit price / net-unit price; not used above.
    unit_gross = money(raw_unit_gross)
    net_unit = money(raw_unit_gross / factor) if factor != 0 else unit_gross

    return DocumentLine(
        position=position,
        name=name,
        quantity=qty,
        price_per_unit_gross=unit_gross,
        net_unit_price=net_unit,
        net=net,
        tax=tax,
        gross=gross,
        tax_category=category,
        tax_rate=rate,
        exemption_reason=exemption_reason,
        exemption_reason_code=exemption_reason_code,
        ticket_label=ticket_label,
    )


def build_tax_breakdown(lines: list[DocumentLine]) -> list[TaxBreakdownEntry]:
    """Group lines into EN16931 VAT subtotals (BG-23), one per category+rate.

    Each subtotal's taxable ``basis`` (BT-116) is the running sum of the
    constituent lines' already-rounded ``net`` amounts. The VAT ``amount``
    (BT-117) is then derived from that finished basis as a *single* rounding of
    ``basis × rate / 100`` — it is NOT the running sum of the per-line ``tax``
    values.

    This is mandated by EN16931 rule BR-CO-17: "VAT category tax amount
    (BT-117) = VAT category taxable amount (BT-116) × (VAT category rate
    (BT-119) / 100), rounded to two decimals." A conformance validator
    (KoSIT / XRechnung) recomputes BT-117 exactly this way and rejects the
    document if it differs, so BT-117 has to equal ``round(basis × rate)``.

    Summing the per-line ``tax`` amounts instead — the previous approach here —
    can drift from ``round(basis × rate)`` by a cent or more once a category
    holds several lines, because each per-line ``tax`` was independently
    rounded to the cent. That drift both violates BR-CO-17 and, via
    ``totals()``, propagates into the header ``TaxTotalAmount`` /
    ``GrandTotalAmount`` / ``DuePayableAmount``. It is exactly the bug behind a
    payable of 10950.17 for a 19 % basis of 9201.83, where the compliant value
    is ``round(9201.83 × 0.19) = 1748.35`` → grand total ``10950.18``.

    Note EN16931 keeps no per-line VAT amount in the totals chain: a line
    carries only its net (BT-131), and VAT is a strictly category-level
    quantity. The per-line ``tax`` on :class:`DocumentLine` is retained only
    for persistence/human-readable display and is deliberately not summed into
    the category amount here.
    """
    groups: OrderedDict[tuple[str, str], TaxBreakdownEntry] = OrderedDict()
    for line in lines:
        key = (line.tax_category, str(line.tax_rate))
        entry = groups.get(key)
        if entry is None:
            entry = TaxBreakdownEntry(
                category=line.tax_category,
                rate=line.tax_rate,
                basis=Decimal("0.00"),
                amount=Decimal("0.00"),
                exemption_reason=line.exemption_reason,
                exemption_reason_code=line.exemption_reason_code,
            )
            groups[key] = entry
        entry.basis = money(entry.basis + line.net)
        # Keep the first non-empty exemption reason seen for the category.
        if entry.exemption_reason is None and line.exemption_reason:
            entry.exemption_reason = line.exemption_reason
        if entry.exemption_reason_code is None and line.exemption_reason_code:
            entry.exemption_reason_code = line.exemption_reason_code

    # BR-CO-17: once each category's taxable basis is fully accumulated, derive
    # its VAT amount from that basis with a single rounding of basis × rate.
    # (Exempt categories carry rate 0, so this yields 0.00 as required.)
    for entry in groups.values():
        entry.amount = money(entry.basis * entry.rate / Decimal("100"))

    return list(groups.values())


def totals(breakdown: list[TaxBreakdownEntry]) -> tuple[Decimal, Decimal, Decimal]:
    """Return (total_net, total_tax, total_gross) from the VAT breakdown."""
    total_net = money(sum((e.basis for e in breakdown), Decimal("0.00")))
    total_tax = money(sum((e.amount for e in breakdown), Decimal("0.00")))
    total_gross = money(total_net + total_tax)
    return total_net, total_tax, total_gross