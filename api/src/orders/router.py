"""Order endpoints (/api/v1/orders, tags: Orders, Payments, Invoicing)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_ORDERS_READ_ALL
from src.invoices import service as invoicing_service
from src.invoices.schemas import InvoiceCreateResponse, InvoiceOut, InvoicesListResponse
from src.orders import service
from src.orders.deps import require_order_scope
from src.orders.schemas import OrderOut, OrderResponse, OrdersListResponse
from src.payments import service as payments_service
from src.payments.schemas import (
    PaymentCreateRequest,
    PaymentOut,
    PaymentResponse,
    PaymentsListResponse,
)

router = APIRouter(prefix="/api/v1/orders", tags=["Orders"])


@router.get("", response_model=OrdersListResponse, summary="List orders")
def list_orders(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_ORDERS_READ_ALL)),
) -> OrdersListResponse:
    orders, total = service.list_orders(db, limit=page.limit, offset=page.offset)
    return OrdersListResponse(
        data=[OrderOut.model_validate(o) for o in orders],
        pagination=make_pagination(total, limit=page.limit, offset=page.offset),
    )


@router.get("/{order_id}", response_model=OrderResponse, summary="Get an order")
def get_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_order_scope("orders", "read")),
) -> OrderResponse:
    return OrderResponse(data=OrderOut.model_validate(service.get_order(db, order_id)))


@router.delete("/{order_id}", response_model=InvoiceCreateResponse, summary="Cancel an order")
def cancel_order(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(require_order_scope("orders", "write")),
) -> InvoiceCreateResponse:
    # Cancelling issues a cancellation invoice (invoiceType=cancellation, code
    # 381). Document generation is delivered in step 3, so this raises 501.
    return invoicing_service.cancel_order(db, order_id, actor=actor.sub)


@router.get(
    "/{order_id}/payments",
    response_model=PaymentsListResponse,
    tags=["Payments"],
    summary="Payments of an order",
)
def list_order_payments(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_order_scope("payments", "read")),
) -> PaymentsListResponse:
    payments = payments_service.list_order_payments(db, order_id)
    return PaymentsListResponse(
        data=[PaymentOut.model_validate(p) for p in payments],
        pagination=make_pagination(len(payments), limit=len(payments) or 1, offset=0),
    )


@router.post(
    "/{order_id}/payments",
    response_model=PaymentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Payments"],
    summary="Record a payment for an order",
)
def create_order_payment(
    order_id: uuid.UUID,
    body: PaymentCreateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(require_order_scope("payments", "write")),
) -> PaymentResponse:
    payment = payments_service.create_order_payment(
        db, order_id, data=body.model_dump(exclude_unset=True), actor=actor.sub
    )
    return PaymentResponse(data=PaymentOut.model_validate(payment))


@router.get(
    "/{order_id}/invoices",
    response_model=InvoicesListResponse,
    tags=["Invoicing"],
    summary="Invoices of an order",
)
def list_order_invoices(
    order_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_order_scope("invoices", "read")),
) -> InvoicesListResponse:
    invoices = invoicing_service.list_order_invoices(db, order_id)
    return InvoicesListResponse(
        data=[InvoiceOut.model_validate(i) for i in invoices],
        pagination=make_pagination(len(invoices), limit=len(invoices) or 1, offset=0),
    )
