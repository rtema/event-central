"""Event endpoints (/api/v1/events, tags: Events, Orders)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth.deps import (
    AuthenticatedActor,
    require_all_scopes,
    require_event_path_scope,
)
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_EVENTS_READ_ALL
from src.events import service
from src.events.schemas import EventOut, EventResponse, EventsListResponse
from src.orders import service as orders_service
from src.orders.schemas import OrderOut, OrdersListResponse

router = APIRouter(prefix="/api/v1/events", tags=["Events"])


@router.get("", response_model=EventsListResponse, summary="List events")
def list_events(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_EVENTS_READ_ALL)),
) -> EventsListResponse:
    events, total = service.list_events(db, limit=page.limit, offset=page.offset)
    return EventsListResponse(
        data=[EventOut.model_validate(e) for e in events],
        pagination=make_pagination(total, limit=page.limit, offset=page.offset),
    )


@router.get("/{event_id}", response_model=EventResponse, summary="Get an event")
def get_event(
    event_id: str,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_event_path_scope("events", "read")),
) -> EventResponse:
    return EventResponse(data=EventOut.model_validate(service.get_event(db, event_id)))


@router.get(
    "/{event_id}/orders",
    response_model=OrdersListResponse,
    tags=["Orders"],
    summary="Orders of an event",
)
def get_event_orders(
    event_id: str,
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_event_path_scope("orders", "read")),
) -> OrdersListResponse:
    service.get_event(db, event_id)  # 404 if the event is unknown
    orders, total = orders_service.list_orders(
        db, limit=page.limit, offset=page.offset, event_id=event_id
    )
    return OrdersListResponse(
        data=[OrderOut.model_validate(o) for o in orders],
        pagination=make_pagination(total, limit=page.limit, offset=page.offset),
    )
