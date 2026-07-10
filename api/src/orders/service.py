"""Order-domain business logic (tag: Orders), decoupled from HTTP."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, String, cast, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from src.core.errors import NotFoundError
from src.orders.models import Order
from src.orders.schemas import OrderSearchParams


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


def search_orders(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_params: OrderSearchParams,
    include_deleted: bool = False,
) -> tuple[list[Order], int]:
    """Return a page of orders (newest first) and the total count.

    Optionally restricted to a single event (used by the per-event route).
    """
    conditions: list[ColumnElement[bool]] = []

    if not include_deleted:
        conditions.append(Order.deleted_at.is_(None))

    # filters
    filters: list[tuple[InstrumentedAttribute[Any], Sequence[Any] | None]] = [
        (Order.status, search_params.status),
        (Order.event_id, search_params.event),
    ]
    for column, values in filters:
        if values:
            conditions.append(column.in_(values))

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
                Order.external_id.ilike(pattern, escape="\\"),
                Order.external_short_id.ilike(pattern, escape="\\"),
                cast(Order.recipient, String).ilike(pattern, escape="\\"),
            )
        )

    # count total
    count_stmt: Select[tuple[int]] = (
        select(func.count()).select_from(Order).where(*conditions)
    )
    total: int = db.execute(count_stmt).scalar_one()

    # build statement
    stmt = (
        select(Order)
        .where(*conditions)
        .order_by(Order.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_order(db: Session, order_id: uuid.UUID) -> Order:
    order = db.get(Order, order_id)
    if order is None:
        raise NotFoundError("order not found")
    return order
