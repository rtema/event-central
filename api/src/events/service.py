"""Event-domain business logic (tag: Events), decoupled from HTTP."""

from __future__ import annotations

from sqlalchemy import ColumnElement, Select, String, cast, func, or_, select
from sqlalchemy.orm import Session

from src.core.errors import NotFoundError
from src.events.models import Event
from src.events.schemas import EventSearchParams


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

def get_event_ids(
    db: Session
) -> list[str]:
    events = list(db.execute(select(Event).order_by(Event.id.desc())).scalars().all())
    return [e.id for e in events]

def search_events(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_params: EventSearchParams,
    include_deleted: bool = False
) -> tuple[list[Event], int]:
    """Return a page of events (newest first) and the total count."""
    conditions: list[ColumnElement[bool]] = []

    if not include_deleted:
        conditions.append(Event.deleted_at.is_(None))

    # filters
    # Currently not implemented

    # special values
    # Currently not implemented

    # text filters
    if search_params.q and search_params.q.strip():
        term: str = search_params.q.strip()
        # escape LIKE wildcards so user input is matched literally
        escaped: str = (
            term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern: str = f"%{escaped}%"
        conditions.append(
            or_(
                cast(Event.label, String).ilike(pattern, escape="\\"),
            )
        )

    # count total
    count_stmt: Select[tuple[int]] = (
        select(func.count()).select_from(Event).where(*conditions)
    )
    total: int = db.execute(count_stmt).scalar_one()

    # build statement
    stmt = (
        select(Event)
        .where(*conditions)
        .order_by(Event.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_event(db: Session, event_id: str) -> Event:
    event = db.get(Event, event_id)
    if event is None:
        raise NotFoundError("event not found")
    return event
