"""Monetary and VAT computation for invoice generation.

All arithmetic uses :class:`~decimal.Decimal` with commercial ``ROUND_HALF_UP``
to two decimals, matching how invoice software and EN16931 validators expect
amounts to round.

EN16931 is a **net-based** standard at the line level, and the KoSIT / PEPPOL
validators enforce that. The chain the validators recompute is:

* BT-146 item net price          = round(gross_unit_price / (1 + rate/100))
* BT-131 invoice line net amount = round(BT-129 quantity * BT-146)   [PEPPOL-EN16931-R120]
* BT-116 category taxable amount = sum of the BT-131 in that category  [BR-S-08 / BR-E-08]
* BT-117 category VAT amount     = round(BT-116 * rate / 100)          [BR-CO-17]
* BT-109 total without VAT       = sum of BT-116
* BT-110 total VAT               = sum of BT-117
* BT-112 total with VAT          = BT-109 + BT-110                      [BR-CO-15]
* BT-115 amount due              = BT-112 (no prepaid / rounding here)  [BR-CO-16]

The incoming ``pricePerUnit`` is VAT-inclusive (per the API spec), so the net
unit price is derived from it. Everything downstream is then built from the net
side, exactly as the validator recomputes it.

Note on gross fidelity: because EN16931 carries no per-line gross amount, the
invoice's reconstructed gross total (BT-112 = net + VAT) can differ by up to a
couple of cents from a naive ``sum(quantity * gross_unit_price)`` when net-unit
rounding compounds across large quantities. That is inherent to the net-based
model — the validators reject the gross-anchored alternative (see R120) — and is
the standard, accepted behavior. If exact reconciliation with the charged gross
is ever required, express BT-146 at higher precision or add a BT-114 rounding
amount; do not re-anchor the line net to the gross.
"""

from __future__ import annotations

from collections import OrderedDict
from decimal import ROUND_HALF_UP, Decimal

from src.invoices.generation.model import DocumentLine, TaxBreakdownEntry
from src.invoices.models import Tax

CENTS = Decimal("0.01")

# Default human-readable exemption reason for the German "Verein" case when the
# caller supplies neither a reason text nor a code (EN16931 BR-E-10 needs one).
DEFAULT_EXEMPTION_REASON = "Steuerbefreite Leistung gemäß § 4 UStG"


def money(value: object) -> Decimal:
    """Coerce to a 2-decimal Decimal, robust against float inputs."""
    d = value if isinstance(value, Decimal) else Decimal(str(value))
    return d.quantize(CENTS, rounding=ROUND_HALF_UP)


def rate(value: object) -> Decimal:
    return Decimal(str(value)).quantize(CENTS, rounding=ROUND_HALF_UP)


def classify_tax(tax: Tax
                 ) -> tuple[str, Decimal, str | None, str | None]:
    """Resolve (category, effective_rate, reason, reason_code) for a tax rate.

    ``exempt-verein`` (or any zero rate) maps to EN16931 category ``E`` at 0 %
    with an exemption reason; everything else is standard-rated ``S``.
    """
    is_exempt = (tax.type == "exempt-verein") or tax.rate == Decimal("0.00")
    if is_exempt:
        reason = tax.tax_exemption_reason or DEFAULT_EXEMPTION_REASON
        return "E", tax.rate, reason, None
    return "S", tax.rate, None, None


def build_line(
    *,
    position: int,
    name: str,
    quantity: object,
    price_per_unit_gross: object,
    tax_category: str,
    tax_rate: Decimal,
    tax_exemption_reason: str | None = None,
    tax_exemption_reason_code: str | None = None,
    ticket_label: str | None = None,
) -> DocumentLine:
    """Compute a single line's net/tax/gross from a VAT-inclusive unit price.

    The computation follows EN16931's net-based line model so that the emitted
    XML passes PEPPOL-EN16931-R120 and the KoSIT Schematron total checks:

    1. ``net_unit_price`` (BT-146) = round(gross_unit_price / (1 + rate/100)).
    2. ``net`` (BT-131) = round(quantity * net_unit_price).

    R120 requires ``BT-131 == round(BT-129 * BT-146)`` exactly, so the line net
    MUST be derived from the *same* rounded net unit price that is written to
    the XML — not from a rounded gross total. Deriving the net from a rounded
    gross (``round(round(qty*gross_unit)/factor)``) is what produced the earlier
    ``R120`` failures and the payable-total drift, because that value does not
    equal ``round(qty * net_unit_price)``.

    ``tax`` and ``gross`` are retained per line for persistence / human-readable
    display only. They are NEVER summed into the document totals: VAT is a
    strictly category-level quantity in EN16931 (see :func:`build_tax_breakdown`
    and :func:`totals`).
    """
    qty = Decimal(str(quantity))
    raw_unit_gross = Decimal(str(price_per_unit_gross))
    factor = Decimal("1") + (tax_rate / Decimal("100"))

    # BT-146 item net price: single rounding of the VAT-inclusive unit price.
    net_unit = money(raw_unit_gross /
                     factor) if factor != 0 else money(raw_unit_gross)

    # BT-131 line net amount = round(quantity * BT-146). Exact match with what
    # the validator recomputes from the emitted quantity and net unit price.
    net = money(net_unit * qty)

    # Per-line VAT / gross — informational only (not part of the totals chain).
    tax = money(net * tax_rate / Decimal("100"))
    gross = money(net + tax)

    return DocumentLine(
        position=position,
        name=name,
        quantity=qty,
        price_per_unit_gross=money(raw_unit_gross),
        net_unit_price=net_unit,
        net=net,
        tax=tax,
        gross=gross,
        tax_category=tax_category,
        tax_rate=tax_rate,
        exemption_reason=tax_exemption_reason,
        exemption_reason_code=tax_exemption_reason_code,
        ticket_label=ticket_label,
    )


def build_tax_breakdown(lines: list[DocumentLine]) -> list[TaxBreakdownEntry]:
    """Group lines into EN16931 VAT subtotals (BG-23), one per category+rate.

    Each subtotal's taxable ``basis`` (BT-116) is the sum of the constituent
    lines' already-rounded ``net`` amounts (BT-131). The VAT ``amount`` (BT-117)
    is then derived from that finished basis as a *single* rounding of
    ``basis * rate / 100`` — it is NOT the running sum of the per-line ``tax``
    values.

    This is mandated by EN16931 rule BR-CO-17: "VAT category tax amount (BT-117)
    = VAT category taxable amount (BT-116) * (VAT category rate (BT-119) / 100),
    rounded to two decimals." The KoSIT / XRechnung validator recomputes BT-117
    exactly this way and rejects the document if it differs.

    Summing per-line ``tax`` instead can drift from ``round(basis * rate)`` by a
    cent or more once a category holds several lines, because each per-line
    ``tax`` was independently rounded; that drift both violates BR-CO-17 and
    propagates via :func:`totals` into the header totals.
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

    # BR-CO-17: derive each category's VAT amount from its finished basis with a
    # single rounding of basis * rate. (Exempt categories carry rate 0 -> 0.00.)
    for entry in groups.values():
        entry.amount = money(entry.basis * entry.rate / Decimal("100"))

    return list(groups.values())


def totals(breakdown: list[TaxBreakdownEntry]) -> tuple[Decimal, Decimal, Decimal]:
    """Return (total_net, total_tax, total_gross) from the VAT breakdown.

    BT-109 = sum of BT-116, BT-110 = sum of BT-117, BT-112 = BT-109 + BT-110
    (BR-CO-15). With no document-level allowances/charges, BT-109 also equals
    the sum of line net amounts (BT-106), satisfying BR-CO-13.
    """
    total_net = money(sum((e.basis for e in breakdown), Decimal("0.00")))
    total_tax = money(sum((e.amount for e in breakdown), Decimal("0.00")))
    total_gross = money(total_net + total_tax)
    return total_net, total_tax, total_gross
