"""Postgres-backed job queue.

An external broker is intentionally avoided; workers may not share one, so
durable async work is persisted in PostgreSQL and claimed with
``SELECT ... FOR UPDATE SKIP LOCKED`` by the queue-handler containers.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import CreatedAtMixin, TZDateTime, uuid_pk

JOB_STATES = ("queued", "running", "succeeded", "failed")


class Job(Base, CreatedAtMixin):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = uuid_pk()
    type: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="queued", index=True)
    payload: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB, nullable=True, default=None)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_attempts: Mapped[int] = mapped_column(
        Integer, nullable=False, default=5)
    available_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime, nullable=False, default=lambda: dt.datetime.now(dt.UTC)
    )
    locked_at: Mapped[dt.datetime | None] = mapped_column(
        TZDateTime, nullable=True, default=None)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    updated_at: Mapped[dt.datetime] = mapped_column(
        TZDateTime,
        nullable=False,
        default=lambda: dt.datetime.now(dt.UTC),
        onupdate=lambda: dt.datetime.now(dt.UTC),
    )
