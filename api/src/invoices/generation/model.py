"""Normalized, ORM-free description of an invoice ready for rendering.

The service layer maps persisted ORM rows (Invoice, InvoiceLineItem, Tax,
Order, Event) into these dataclasses; the CII and PDF generators consume only
these, so they carry no database or HTTP coupling and are trivially testable.

All monetary values are :class:`~decimal.Decimal` quantised to two decimals.
"""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field
from decimal import Decimal

# EN16931 / UN/EDIFACT code lists used by the generators.
INVOICE_TYPE_CODE = "380"        # commercial invoice (Rechnung)
CANCELLATION_TYPE_CODE = "381"   # credit note (Storno / Gutschrift)
UNIT_CODE_PIECE = "C62"          # "one" / piece (BT-130 default)
VAT_SCHEME = "VAT"

# XRechnung 3.0 specification identifier (EN16931 BT-24). The same CII profile
# is valid as the ZUGFeRD "XRECHNUNG" profile, so one document serves both the
# standalone XRechnung XML and the PDF-embedded XML.
XRECHNUNG_SPEC_ID = (
    "urn:cen.eu:en16931:2017#compliant#urn:xoev-de:kosit:standard:xrechnung_3.0"
)


@dataclass(slots=True)
class Party:
    """A seller (supplier) or buyer (recipient)."""

    name: str | None = None
    legal_registration: str | None = None
    vat_id: str | None = None
    iban: str | None = None
    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
    city: str | None = None
    zip_code: str | None = None
    country: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None

    @property
    def street(self) -> str | None:
        parts = [p for p in (self.line1, self.line2, self.line3) if p]
        return ", ".join(parts) if parts else None


@dataclass(slots=True)
class DocumentLine:
    """A priced invoice line with its computed net/tax/gross amounts."""

    position: int
    name: str
    quantity: Decimal
    price_per_unit_gross: Decimal  # incoming unit price *includes* VAT (per spec)
    net_unit_price: Decimal        # derived net unit price (BT-146)
    net: Decimal                   # line net amount (BT-131)
    tax: Decimal
    gross: Decimal
    tax_category: str              # "S" (standard) or "E" (exempt)
    tax_rate: Decimal              # percent, e.g. Decimal("19.00")
    tax_scheme: str = VAT_SCHEME
    exemption_reason: str | None = None
    exemption_reason_code: str | None = None
    ticket_label: str | None = None


@dataclass(slots=True)
class TaxBreakdownEntry:
    """One VAT category/rate subtotal (EN16931 BG-23)."""

    category: str
    rate: Decimal
    basis: Decimal      # taxable amount (BT-116)
    amount: Decimal     # VAT amount (BT-117)
    exemption_reason: str | None = None
    exemption_reason_code: str | None = None


@dataclass(slots=True)
class InvoiceDocument:
    """Everything required to render the XML + PDF for a single invoice."""

    invoice_number: str
    invoice_type: str            # "invoice" | "cancellation"
    invoice_type_code: str       # "380" | "381"
    issue_date: dt.date
    currency: str
    locale: str
    supplier: Party
    recipient: Party
    lines: list[DocumentLine]
    tax_breakdown: list[TaxBreakdownEntry]
    total_net: Decimal
    total_tax: Decimal
    total_gross: Decimal
    due_date: dt.date | None = None
    buyer_reference: str | None = None
    order_external_id: str | None = None
    payment_link: str | None = None
    order_link: str | None = None
    event_id: str | None = None
    event_label: str | None = None
    notes: list[str] = field(default_factory=list[str])

    @property
    def is_cancellation(self) -> bool:
        return self.invoice_type == "cancellation"
