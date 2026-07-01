"""Invoicing-domain API schemas (camelCase JSON, tag: Invoicing)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from pydantic import Field, field_validator, model_validator

from src.core.schemas import (
    Base64Str,
    CamelModel,
    Currency,
    InvoiceRecipient,
    InvoiceSupplier,
    Locale,
    MultiLanguageLabel,
    Pagination,
)
from src.core.scopes import RESERVED_LABELS
from src.events.schemas import EventOut
from src.orders.schemas import OrderOut

InvoiceType = Literal["invoice", "cancellation"]
TaxType = Literal["standard", "exempt-verein"]


# --------------------------------------------------------------------------- #
# Tax (also reused by the Misc /taxes route)
# --------------------------------------------------------------------------- #
class TaxOut(CamelModel):
    id: uuid.UUID
    external_id: str | None = None
    rate: float
    label: MultiLanguageLabel
    type: TaxType
    tax_exemption_reason: str | None = None
    created_by: str | None = None
    created_at: dt.datetime


class InvoiceTaxesListResponse(CamelModel):
    data: list[TaxOut]


class TaxesListResponse(CamelModel):
    """Paginated tax list for the Misc /taxes route."""

    data: list[TaxOut]
    pagination: Pagination


# --------------------------------------------------------------------------- #
# Line items
# --------------------------------------------------------------------------- #
class InvoiceLineItemTicketMetadata(CamelModel):
    external_ticket_id: str | None = None
    external_ticket_option_id: str | None = None
    external_ticket_option_label: str | None = None
    external_ticket_price_id: str | None = None
    external_ticket_price_line_id: str | None = None
    external_ticket_price_line_label: str | None = None
    external_sales_stage_id: str | None = None
    external_sales_stage_label: str | None = None


class InvoiceLineItemOut(CamelModel):
    id: uuid.UUID
    invoice_id: uuid.UUID
    tax_id: uuid.UUID | None = None
    position: int
    quantity: float
    price_per_unit: float
    name: str
    ticket: InvoiceLineItemTicketMetadata | None = None
    tax_category: str | None = None
    tax_rate: float | None = None
    tax_scheme: str | None = None
    tax_exemption_reason: str | None = None
    tax_exemption_reason_code: str | None = None
    total_net: float
    total_tax: float
    total_gross: float


class InvoiceLineItemsListResponse(CamelModel):
    data: list[InvoiceLineItemOut]


# --------------------------------------------------------------------------- #
# Invoice header
# --------------------------------------------------------------------------- #
class InvoiceOut(CamelModel):
    id: uuid.UUID
    order_id: uuid.UUID
    document_template_id: uuid.UUID | None = None
    locale: Locale | None = None
    accounting_entity: str | None = None
    accounting_number: int | None = None
    invoice_number: str | None = None
    invoice_type: InvoiceType
    invoice_type_code: str
    issue_date: dt.datetime | None = None
    due_date: dt.datetime | None = None
    currency: Currency
    supplier: InvoiceSupplier | None = None
    recipient: InvoiceRecipient | None = None
    total_net: float
    total_tax: float
    total_gross: float
    created_by: str | None = None
    created_at: dt.datetime


class InvoiceResponse(CamelModel):
    data: InvoiceOut


class InvoicesListResponse(CamelModel):
    data: list[InvoiceOut]
    pagination: Pagination


# --------------------------------------------------------------------------- #
# Template fragments (embedded in the create request)
# --------------------------------------------------------------------------- #
class TemplateFont(CamelModel):
    name: str
    weight: int
    file: Base64Str  # base64


class TemplateImage(CamelModel):
    key: str
    file: Base64Str | None = None  # base64
    link: str | None = None  # https only

    @model_validator(mode="after")
    def check_file_xor_link(self):
        # True when both are None or both are set — both are error cases
        if (self.file is None) == (self.link is None):
            raise ValueError("exactly one of 'file' or 'link' must be set")
        return self


class InvoiceTemplate(CamelModel):
    template_name: str | None = None
    html: str | None = None
    css: str | None = None
    fonts: list[TemplateFont] | None = None
    images: list[TemplateImage] | None = None

    @model_validator(mode="after")
    def check_template_source(self):
        has_name = self.template_name is not None
        has_html = self.html is not None
        has_css = self.css is not None

        if has_name and (has_html or has_css):
            raise ValueError(
                "set either 'template_name' or 'html'+'css', not both"
            )
        if not has_name and not (has_html and has_css):
            raise ValueError(
                "'html' and 'css' must both be set when 'template_name' is not"
            )
        return self


# --------------------------------------------------------------------------- #
# Create request (single-request invoice generation payload)
# --------------------------------------------------------------------------- #
class InvoiceCreateAccountingEntity(CamelModel):
    prefix: str
    first_invoice_number: int
    pad_number: int | None = None


class InvoiceCreateEvent(CamelModel):
    id: str
    label: str | None = None
    start_dt: dt.datetime | None = None
    end_dt: dt.datetime | None = None

    #
    # IMPORTANT:
    # Prevent any event name that is reserved and may lead to the expansion of access rights:
    # There fore the scope qualifiers are reserved labels that can NEVER be uses as event ids
    #

    @field_validator("id")
    @classmethod
    def validate_id(cls, v: str) -> str | None:
        if v is None:  # pyright: ignore[reportUnnecessaryComparison]
            return v
        if len(v) < 2:
            raise ValueError("id must be at least 2 characters")
        if v.lower() in RESERVED_LABELS:
            raise ValueError(f"'{v}' is a reserved id")
        return v


class InvoiceCreateLinks(CamelModel):
    payment_link: str | None = None
    order_link: str | None = None


class InvoiceCreateTaxRate(CamelModel):
    external_id: str
    rate: float = Field(ge=0, le=100)
    label: str
    type: TaxType | None = None
    tax_exemption_reason: str | None = None


class InvoiceCreateLineItem(CamelModel):
    quantity: float
    price_per_unit: float
    external_tax_id: str
    name: str
    ticket: InvoiceLineItemTicketMetadata | None = None


class InvoiceCreateRequest(CamelModel):
    external_order_id: str
    external_order_short_id: str | None = None
    locale: Locale | None = None
    currency: Currency
    due_date: dt.datetime
    accounting_entity: InvoiceCreateAccountingEntity | None = None
    event: InvoiceCreateEvent
    links: InvoiceCreateLinks
    supplier: InvoiceSupplier
    recipient: InvoiceRecipient
    tax_rates: list[InvoiceCreateTaxRate] | None = None
    line_items: list[InvoiceCreateLineItem] = Field(min_length=1)
    invoice_template: InvoiceTemplate


class InvoiceCreateResponse(CamelModel):
    invoice: InvoiceOut
    invoice_lines: list[InvoiceLineItemOut]
    order: OrderOut
    event: EventOut
    invoice_pdf: str | None = None  # base64 ZUGFeRD PDF
    invoice_xml: str | None = None  # base64 XRechnung XML


# --------------------------------------------------------------------------- #
# Signed link + export
# --------------------------------------------------------------------------- #
class InvoiceLinkRequest(CamelModel):
    file_type: Literal["pdf", "xrechnung"] = "pdf"
    expires_in: int | None = Field(default=None, le=31_536_000)


class InvoiceLinkResponse(CamelModel):
    url: str
    expires_at: dt.datetime


class InvoiceExportRequest(CamelModel):
    accounting_entity: str | None = None
    format: Literal["xlsx", "zip"] = "xlsx"


class InvoicesExportResponse(CamelModel):
    url: str
    expires_at: dt.datetime
