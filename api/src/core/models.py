"""Reusable column types and mixins.

The project targets PostgreSQL exclusively (in development and production), so
models use native Postgres types directly: ``UUID``, ``JSONB`` and
timezone-aware ``TIMESTAMPTZ``.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

# UUIDs as UUID, defined her to prevent issues
UUIDType = UUID(as_uuid=True)

# Timezone-aware timestamps everywhere (maps to TIMESTAMPTZ).
TZDateTime = DateTime(timezone=True)


def uuid_pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUIDType, primary_key=True, default=uuid.uuid4)


class CreatedAtMixin:
    """Adds an automatic ``created_at`` column."""

    created_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime, nullable=False, server_default=func.now()
    )


class UpdatedAtMixin:
    """Adds an automatic ``updated_at`` column (set on insert and update)."""

    updated_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )


class CreatedByMixin:
    """Adds a ``created_by`` column to track the actor.
    Format is as follows: User ID or APP: user:userId or app:appKey
    """

    created_by: Mapped[str] = mapped_column(String(128))


class DeletedAtMixin:
    """Adds a nullable ``deleted_at`` column for soft deletes."""

    deleted_at: Mapped[dt.datetime | None] = mapped_column(
        TZDateTime, nullable=True, default=None)

    @property
    def is_deleted(self) -> bool:
        return self.deleted_at is not None


class DeletedByMixin:
    """Adds a ``deleted_by`` column to track the actor.
    Format is as follows: User ID or APP: user:userId or app:appKey
    """

    deleted_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
