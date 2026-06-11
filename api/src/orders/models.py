"""Order-domain models (tag: Orders).

An *order* belongs to exactly one event and is uniquely identified within that
event by its caller-supplied ``external_id``. Invoices and payments reference
the order; cancelling an order is a soft operation that flips its status and
(in step 3) issues a cancellation invoice.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    DeletedAtMixin,
    DeletedByMixin,
    UpdatedAtMixin,
    uuid_pk,
)

ORDER_STATUSES = ("open", "paid", "cancelled")


class Order(Base, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    __tablename__ = "orders"
    __table_args__ = (
        # external_id is unique on a per-event basis (see spec).
        UniqueConstraint("event_id", "external_id", name="uq_orders_event_external"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    event_id: Mapped[str] = mapped_column(
        String(128), ForeignKey("events.id", ondelete="RESTRICT"), index=True, nullable=False
    )

    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    payment_link: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    link: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    status: Mapped[str] = mapped_column(String(16), nullable=False, default="open")

    # InvoiceRecipient snapshot for this order.
    recipient: Mapped[dict[str, str] | None] = mapped_column(JSONB, nullable=True, default=None)
