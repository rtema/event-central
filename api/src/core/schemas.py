"""Shared Pydantic schema building blocks."""

from __future__ import annotations

import base64
import binascii
from typing import Annotated, Literal
from uuid import UUID

from alembic.environment import Any
from pydantic import AfterValidator, BaseModel, BeforeValidator, ConfigDict
from pydantic.alias_generators import to_camel

Locale = Literal["de", "en"]
Currency = Literal["EUR"]


# Base64 encoded data
def _validate_base64(value: str) -> str:
    try:
        # validate=True rejects any character outside the base64 alphabet
        # instead of silently discarding it
        base64.b64decode(value, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("must be valid base64-encoded data") from exc
    return value


Base64Str = Annotated[str, AfterValidator(_validate_base64)]


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


def split_comma_separated_list(value: Any) -> list[str] | None:
    """Normalize a comma-separated query value into a clean list.

    Handles both wire formats:
      "png,jpg"            -> ["png", "jpg"]   (comma-separated, one param)
      ["png", "jpg"]       -> ["png", "jpg"]   (repeated ?ext=png&ext=jpg)
      "a, b ,, c"          -> ["a", "b", "c"]  (trims, drops empties)
      None / "" / ","      -> None
    """
    if value is None:
        return None
    if isinstance(value, str):
        value = [value]
    items = [part.strip()
             for chunk in value for part in chunk.split(",")]  # type: ignore
    items: list[str] = [item for item in items if item]
    return items or None


CommaSeparatedListStr = Annotated[list[str] | None,
                                  BeforeValidator(split_comma_separated_list)]

CommaSeparatedListUuid = Annotated[list[UUID] |
                                   None, BeforeValidator(split_comma_separated_list)]


def make_multilanguage_label(value: str | dict[str, Any] | None) -> dict[str, str]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return {k: v for k, v in value.items() if v is not None}
    return {"de": value, "en": value}


class InvoiceSupplier(CamelModel):
    """Supplier (issuer) of the goods/services. Shared value object."""

    legal_name: str
    legal_registration: str
    vat_id: str
    iban: str
    bank_name: str | None = None
    line1: str
    line2: str | None = None
    line3: str | None = None
    city: str
    zip_code: str | None = None
    country: str
    contact_name: str | None = None
    contact_phone: str | None = None
    contact_email: str | None = None


class InvoiceRecipient(CamelModel):
    """Recipient (buyer) of the goods/services. Shared value object."""

    line1: str
    line2: str | None = None
    line3: str | None = None
    city: str
    zip_code: str | None = None
    country: str
    contact_salutation: str | None = None
    contact_title: str | None = None
    contact_firstname: str
    contact_lastname: str | None = None
    contact_phone: str | None = None
    contact_email: str
    contact_cc_email: list[str] | None = None
    purchase_order_reference: str | None = None
    vat_id: str | None = None
