"""Payment-domain API schemas (camelCase JSON, tag: Payments)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Literal

from src.core.schemas import CamelModel, Currency, Pagination

PaymentType = Literal["payment", "refund"]


class PaymentOut(CamelModel):
    id: uuid.UUID
    order_id: uuid.UUID
    external_id: str | None = None
    provider: str | None = None
    method: str | None = None
    type: PaymentType
    status: str | None = None
    amount: float
    currency: Currency
    created_by: str | None = None
    created_at: dt.datetime


class PaymentResponse(CamelModel):
    data: PaymentOut


class PaymentsListResponse(CamelModel):
    data: list[PaymentOut]
    pagination: Pagination


class PaymentCreateRequest(CamelModel):
    external_id: str | None = None
    provider: str | None = None
    method: str | None = None
    type: PaymentType = "payment"
    status: str | None = None
    amount: float
    currency: Currency = "EUR"
