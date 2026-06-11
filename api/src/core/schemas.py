"""Shared Pydantic schema building blocks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Locale = Literal["de", "en"]
Currency = Literal["EUR"]


class CamelModel(BaseModel):
    """Base for API models that serialise/accept camelCase JSON keys.

    Fields are declared in snake_case but read and written as camelCase (e.g.
    ``first_name`` <-> ``firstName``). ``populate_by_name`` also allows the
    snake_case name on input.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        from_attributes=True,
    )


class MultiLanguageLabel(BaseModel):
    de: str | None = None
    en: str | None = None


# An actor is identified as ``user:<uuid>`` or ``app:<key>`` (see core.models
# CreatedByMixin). In the API it is exposed as a plain string.
ActorIdentifier = str


class Pagination(CamelModel):
    """Pagination metadata returned alongside list responses."""

    total: int
    limit: int
    current_offset: int


def make_pagination(total: int, *, limit: int, offset: int) -> Pagination:
    return Pagination(total=total, limit=limit, current_offset=offset)


class InvoiceSupplier(CamelModel):
    """Supplier (issuer) of the goods/services. Shared value object."""

    legal_name: str | None = None
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


class InvoiceRecipient(CamelModel):
    """Recipient (buyer) of the goods/services. Shared value object."""

    line1: str | None = None
    line2: str | None = None
    line3: str | None = None
    city: str | None = None
    zip_code: str | None = None
    country: str | None = None
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None
    contact_cc_email: list[str] | None = None
    purchase_order_reference: str | None = None
    vat_id: str | None = None
