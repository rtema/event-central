"""Order-domain API schemas (camelCase JSON, tag: Orders)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field

from src.core.schemas import (
    CamelModel,
    CommaSeparatedListStr,
    InvoiceRecipient,
    Pagination,
    split_comma_separated_list,
)

OrderStatus = Literal["open", "paid", "cancelled"]


class OrderOut(CamelModel):
    id: uuid.UUID
    event_id: str
    external_id: str | None = None
    payment_link: str | None = None
    link: str | None = None
    status: OrderStatus
    recipient: InvoiceRecipient | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    deleted_at: dt.datetime | None = None


class OrderResponse(CamelModel):
    data: OrderOut


class OrdersListResponse(CamelModel):
    data: list[OrderOut]
    pagination: Pagination


class OrderSearchParams(CamelModel):
    q: str | None = Field(
        default=None, description="Generic free-text search term")

    status: Annotated[list[OrderStatus] | None,
                      BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated types, e.g. open,paid,cancelled"
    )
    event: CommaSeparatedListStr = Field(
        default=None,
        description="Comma-separated event ids",
    )


class OrdersSearchResponse(CamelModel):
    data: list[OrderOut]
    pagination: Pagination
    search: OrderSearchParams
