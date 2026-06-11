"""Payment-domain models (tag: Payments).

Payments (and refunds) are recorded against an order. They are immutable
records — created once and never updated — so they carry only ``created_*``
audit columns.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import CreatedAtMixin, CreatedByMixin, UUIDType, uuid_pk

PAYMENT_TYPES = ("payment", "refund")


class Payment(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = uuid_pk()
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("orders.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Unique on a per-event basis; enforced in the service layer since the event
    # lives on the parent order rather than on the payment row.
    external_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)

    provider: Mapped[str | None] = mapped_column(String(128), nullable=True)
    method: Mapped[str | None] = mapped_column(String(128), nullable=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False, default="payment")
    status: Mapped[str | None] = mapped_column(String(64), nullable=True)

    amount: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
