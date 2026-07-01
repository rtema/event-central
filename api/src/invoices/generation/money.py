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
    """Compute a single line's net/tax/gross from a VAT-inclusive unit price."""
    qty = Decimal(str(quantity))
    unit_gross = money(price_per_unit_gross)
    factor = Decimal("1") + (rate / Decimal("100"))

    net_unit = money(unit_gross / factor) if factor != 0 else unit_gross
    net = money(net_unit * qty)
    tax = money(net * rate / Decimal("100"))
    gross = money(net + tax)

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

    The per-category VAT amount is recomputed as ``basis × rate / 100`` (rounded)
    rather than summed from the lines, so it satisfies BR-S-08 / BR-E-08.
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

    for entry in groups.values():
        entry.amount = money(entry.basis * entry.rate / Decimal("100"))
    return list(groups.values())


def totals(breakdown: list[TaxBreakdownEntry]) -> tuple[Decimal, Decimal, Decimal]:
    """Return (total_net, total_tax, total_gross) from the VAT breakdown."""
    total_net = money(sum((e.basis for e in breakdown), Decimal("0.00")))
    total_tax = money(sum((e.amount for e in breakdown), Decimal("0.00")))
    total_gross = money(total_net + total_tax)
    return total_net, total_tax, total_gross
