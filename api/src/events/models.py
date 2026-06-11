"""Event-domain models (tag: Events).

An *event* is the top-level grouping that orders, invoices and payments hang
off. Its id is a human-friendly slug (lower-case letters, digits, ``-`` and
``_``) supplied by the caller — not a UUID — so it can appear in per-event
scopes (e.g. ``invoices:read:tema-2026``) and in external references.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    DeletedAtMixin,
    DeletedByMixin,
    TZDateTime,
    UpdatedAtMixin,
)


class Event(Base, CreatedAtMixin, UpdatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    __tablename__ = "events"

    # Caller-supplied slug, e.g. "tema-2026".
    id: Mapped[str] = mapped_column(String(128), primary_key=True)

    # MultiLanguageLabel: {"de": ..., "en": ...}
    label: Mapped[dict[str, str]] = mapped_column(JSONB, nullable=False, default=dict)

    start_dt: Mapped[dt.datetime | None] = mapped_column(TZDateTime, nullable=True)
    end_dt: Mapped[dt.datetime | None] = mapped_column(TZDateTime, nullable=True)
