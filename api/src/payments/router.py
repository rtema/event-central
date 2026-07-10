"""Payment endpoints (/api/v1/payments, tag: Payments)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_PAYMENTS_READ_ALL
from src.payments import service
from src.payments.schemas import PaymentOut, PaymentsListResponse

router = APIRouter(prefix="/api/v1/payments", tags=["Payments"])


@router.get("", response_model=PaymentsListResponse, summary="List payments")
def list_payments(
    page: PageParams = Depends(page_params),
    event_id: str | None = Query(
        default=None, description="Restrict to one event"),
    db: Session = Depends(get_db),
    # Listing across events requires the resource-wide read scope. Per-event
    # tokens read payments through the order-scoped routes instead.
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_PAYMENTS_READ_ALL)),
) -> PaymentsListResponse:
    payments, total = service.list_payments(
        db, limit=page.limit, offset=page.offset, event_id=event_id
    )
    return PaymentsListResponse(
        data=[PaymentOut.model_validate(p) for p in payments],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )
