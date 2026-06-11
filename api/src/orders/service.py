"""Order-domain business logic (tag: Orders), decoupled from HTTP."""

from __future__ import annotations

import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import NotFoundError
from src.orders.models import Order


def list_orders(
    db: Session,
    *,
    limit: int,
    offset: int,
    event_id: str | None = None,
    include_deleted: bool = False,
) -> tuple[list[Order], int]:
    """Return a page of orders (newest first) and the total count.

    Optionally restricted to a single event (used by the per-event route).
    """
    base = select(Order)
    count_stmt = select(func.count()).select_from(Order)
    if event_id is not None:
        base = base.where(Order.event_id == event_id)
        count_stmt = count_stmt.where(Order.event_id == event_id)
    if not include_deleted:
        base = base.where(Order.deleted_at.is_(None))
        count_stmt = count_stmt.where(Order.deleted_at.is_(None))

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(Order.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("order not found")
    return order
