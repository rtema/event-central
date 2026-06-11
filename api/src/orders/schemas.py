"""Order-domain API schemas (camelCase JSON, tag: Orders)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from src.core.schemas import CamelModel, InvoiceRecipient, Pagination

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
