"""Invoicing-domain API schemas (camelCase JSON, tag: Invoicing)."""

from __future__ import annotations

import datetime as dt
import uuid
from decimal import Decimal
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, StringConstraints, field_validator, model_validator

from src.core.schemas import (
    Base64Str,
    CamelModel,
    CommaSeparatedListStr,
    Currency,
    InvoiceRecipient,
    InvoiceSupplier,
    Locale,
    MultiLanguageLabel,
    Pagination,
    split_comma_separated_list,
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
# Accounting entities
# --------------------------------------------------------------------------- #


class AccountingEntitiesListResponse(CamelModel):
    data: list[str]


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


class InvoiceSearchParams(CamelModel):
    q: str | None = Field(
        default=None, description="Generic free-text search term")

    accounting_entity: CommaSeparatedListStr = Field(
        default=None,
        description="Comma-separated list of accounting entities",
    )
    invoice_type: Annotated[list[InvoiceType] | None,
                            BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated types, e.g. invoice,cancellation"
    )
    locale: Annotated[list[Locale] | None, BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated locales, e.g. de,en"
    )


class InvoicesSearchResponse(CamelModel):
    data: list[InvoiceOut]
    pagination: Pagination
    search: InvoiceSearchParams


# --------------------------------------------------------------------------- #
# Template fragments (embedded in the create request)
# --------------------------------------------------------------------------- #
class TemplateFont(CamelModel):
    name: str
    weight: int
    file: Base64Str


class TemplateImage(CamelModel):
    key: str
    file: Base64Str


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
    external_id: str = Field(min_length=1)
    # Percentage. Decimal (not float) to avoid binary-float drift; bounded to
    # 0..100 and at most 2 decimals to match the `taxes.rate` Numeric(5, 2)
    # column and EN16931 rate handling.
    rate: Decimal = Field(ge=0, le=100, max_digits=5, decimal_places=2)
    label: Annotated[str, StringConstraints(
        strip_whitespace=True, min_length=1)]
    type: TaxType
    tax_exemption_reason: str | None = None


class InvoiceCreateLineItem(CamelModel):
    # Quantity: strictly positive, at most 3 decimals (matches the
    # `invoice_line_items.quantity` Numeric(14, 3) column). Decimal, not float,
    # so the value that reaches the money/CII layer is exactly what was sent.
    quantity: Decimal = Field(gt=0, max_digits=14, decimal_places=3)
    # VAT-inclusive gross unit price (per the API spec). Non-negative and at
    # most 2 decimals: sub-cent unit prices are rejected here rather than being
    # silently truncated on persistence (`price_per_unit` is Numeric(14, 2)) and
    # then diverging from the amount used during document generation.
    price_per_unit: Decimal = Field(ge=0, max_digits=14, decimal_places=2)
    external_tax_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    ticket: InvoiceLineItemTicketMetadata | None = None


class InvoiceCreateRequest(CamelModel):
    external_order_id: str = Field(min_length=1)
    external_order_short_id: str | None = None
    locale: Locale
    currency: Currency
    due_date: dt.datetime
    accounting_entity: InvoiceCreateAccountingEntity | None = None
    event: InvoiceCreateEvent
    links: InvoiceCreateLinks
    supplier: InvoiceSupplier
    recipient: InvoiceRecipient
    tax_rates: list[InvoiceCreateTaxRate]
    line_items: list[InvoiceCreateLineItem] = Field(min_length=1)
    invoice_template: InvoiceTemplate

    @model_validator(mode="after")
    def check_tax_rate_references(self):
        """Within-request tax integrity.

        Tax rates supplied inline must have unique ``externalId``s, and every
        line item must reference one of them. When ``tax_rates`` is omitted the
        service resolves ``externalTaxId`` against persisted tax rows, so that
        referential check (and the EN16931 BR-S-02 "seller VAT id required for
        standard-rated lines" rule, which depends on the resolved rate) is
        enforced in the service layer instead.
        """
        if not self.tax_rates:
            return self

        rate_ids: set[str] = set()
        for tr in self.tax_rates:
            if tr.external_id in rate_ids:
                raise ValueError(
                    f"duplicate tax rate externalId '{tr.external_id}'"
                )
            rate_ids.add(tr.external_id)

        for idx, line in enumerate(self.line_items):
            if line.external_tax_id not in rate_ids:
                raise ValueError(
                    f"lineItems[{idx}] references unknown externalTaxId "
                    f"'{line.external_tax_id}'"
                )
        return self


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
