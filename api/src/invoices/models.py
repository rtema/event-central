"""Invoicing-domain models (tag: Invoicing).

Tables
------
* ``taxes``               — tax rates referenced by an invoice's line items.
                            ``external_id`` is the id the caller supplied and is
                            unique within an order/invoice.
* ``invoices``            — the invoice header (supplier/recipient snapshots,
                            numbering, totals). ``event_id`` is denormalised
                            from the order for per-event scoping and reporting.
* ``invoice_line_items``  — the priced lines, each pointing at a tax row.

Generated documents (ZUGFeRD PDF + XRechnung XML) are produced in step 3; the
header carries nullable object-storage keys so the file-download routes have a
place to read from once that lands.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    TZDateTime,
    UUIDType,
    uuid_pk,
)

INVOICE_TYPES = ("invoice", "cancellation")
TAX_TYPES = ("standard", "exempt-verein")


class Tax(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "taxes"

    id: Mapped[uuid.UUID] = uuid_pk()
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Id supplied to the API when this tax rate was created (unique per invoice).
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True)

    rate: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0)

    # MultiLanguageLabel
    label: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)

    type: Mapped[str] = mapped_column(String(32), nullable=False, default="standard")
    tax_exemption_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    invoice: Mapped[Invoice] = relationship(back_populates="taxes")


class Invoice(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "invoices"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("orders.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    # Denormalized from the order for per-event scoping / reporting.
    event_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("events.id", ondelete="RESTRICT"), index=True, nullable=False
    )
    
    document_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("document_templates.id", ondelete="SET NULL"), nullable=True
    )

    locale: Mapped[str] = mapped_column(String(2), nullable=False, default="de")

    # Numbering (Rechnungskreis).
    accounting_entity: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    accounting_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    invoice_number: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)

    invoice_type: Mapped[str] = mapped_column(String(16), nullable=False, default="invoice")
    invoice_type_code: Mapped[str] = mapped_column(String(8), nullable=False, default="380")

    issue_date: Mapped[dt.datetime | None] = mapped_column(TZDateTime, nullable=True)
    due_date: Mapped[dt.datetime | None] = mapped_column(TZDateTime, nullable=True)

    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")

    # InvoiceSupplier / InvoiceRecipient snapshots.
    supplier: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True, default=None)
    recipient: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True, default=None)

    total_net: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_tax: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_gross: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    # Object-storage keys for the generated documents (populated in step 3).
    pdf_key: Mapped[str | None] = mapped_column(String(512), nullable=True)
    xml_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    line_items: Mapped[list[InvoiceLineItem]] = relationship(
        back_populates="invoice", lazy="selectin", order_by="InvoiceLineItem.position"
    )
    taxes: Mapped[list[Tax]] = relationship(back_populates="invoice", lazy="selectin")


class InvoiceLineItem(Base):
    __tablename__ = "invoice_line_items"

    id: Mapped[uuid.UUID] = uuid_pk()
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("invoices.id", ondelete="CASCADE"), index=True, nullable=False
    )
    tax_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("taxes.id", ondelete="SET NULL"), nullable=True
    )

    position: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    quantity: Mapped[float] = mapped_column(Numeric(14, 3), nullable=False, default=0)
    price_per_unit: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    name: Mapped[str] = mapped_column(String(512), nullable=False, default="")

    # InvoiceLineItemTicketMetadata snapshot.
    ticket: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True, default=None)

    # Tax breakdown captured on the line (mirrors the spec's read model).
    tax_category: Mapped[str | None] = mapped_column(String(8), nullable=True)
    tax_rate: Mapped[float | None] = mapped_column(Numeric(5, 2), nullable=True)
    tax_scheme: Mapped[str | None] = mapped_column(String(16), nullable=True)
    tax_exemption_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    tax_exemption_reason_code: Mapped[str | None] = mapped_column(String(64), nullable=True)

    total_net: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_tax: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    total_gross: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)

    invoice: Mapped[Invoice] = relationship(back_populates="line_items")
