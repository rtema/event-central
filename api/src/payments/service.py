"""Payment-domain business logic (tag: Payments), decoupled from HTTP."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import ConflictError
from src.orders.models import Order
from src.orders.service import get_order
from src.payments.models import Payment


def list_payments(
    db: Session,
    *,
    limit: int,
    offset: int,
    order_id: uuid.UUID | None = None,
    event_id: str | None = None,
) -> tuple[list[Payment], int]:
    """Return a page of payments (newest first) and the total count.

    Can be narrowed to a single order or (via the parent order) to one event.
    """
    base = select(Payment)
    count_stmt = select(func.count()).select_from(Payment)
    if order_id is not None:
        base = base.where(Payment.order_id == order_id)
        count_stmt = count_stmt.where(Payment.order_id == order_id)
    if event_id is not None:
        base = base.join(Order, Order.id == Payment.order_id).where(Order.event_id == event_id)
        count_stmt = (
            count_stmt.join(Order, Order.id == Payment.order_id)
            .where(Order.event_id == event_id)
        )

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(Payment.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def list_order_payments(db: Session, order_id: uuid.UUID) -> list[Payment]:
    get_order(db, order_id)  # 404 if missing
    stmt = (
        select(Payment).where(Payment.order_id == order_id).order_by(Payment.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def create_order_payment(
    db: Session, order_id: uuid.UUID, *, data: dict[str, Any], actor: str | None
) -> Payment:
    order = get_order(db, order_id)

    external_id = data.get("external_id")
    if external_id is not None:
        # external_id must be unique on a per-event basis (across the event's
        # orders), so check against every payment of every order in this event.
        clash = db.execute(
            select(Payment.id)
            .join(Order, Order.id == Payment.order_id)
            .where(Order.event_id == order.event_id, Payment.external_id == external_id)
            .limit(1)
        ).first()
        if clash is not None:
            raise ConflictError(
                f"a payment with externalId {external_id!r} already exists for this event"
            )

    payment = Payment(
        order_id=order_id,
        external_id=external_id,
        provider=data.get("provider"),
        method=data.get("method"),
        type=data.get("type", "payment"),
        status=data.get("status"),
        amount=data.get("amount", 0),
        currency=data.get("currency", "EUR"),
        created_by=actor,
    )
    db.add(payment)
    db.flush()
    return payment
