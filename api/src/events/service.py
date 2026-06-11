"""Event-domain business logic (tag: Events), decoupled from HTTP."""

from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import NotFoundError
from src.events.models import Event


def list_events(
    db: Session, *, limit: int, offset: int, include_deleted: bool = False
) -> tuple[list[Event], int]:
    """Return a page of events (newest first) and the total count."""
    base = select(Event)
    count_stmt = select(func.count()).select_from(Event)
    if not include_deleted:
        base = base.where(Event.deleted_at.is_(None))
        count_stmt = count_stmt.where(Event.deleted_at.is_(None))

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(Event.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def get_event(db: Session, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFoundError("event not found")
    return event
