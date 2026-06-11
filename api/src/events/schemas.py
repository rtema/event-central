"""Event-domain API schemas (camelCase JSON, tag: Events)."""

from __future__ import annotations

import datetime as dt

from src.core.schemas import CamelModel, MultiLanguageLabel, Pagination


class EventOut(CamelModel):
    id: str
    label: MultiLanguageLabel
    start_dt: dt.datetime | None = None
    end_dt: dt.datetime | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    deleted_at: dt.datetime | None = None


class EventResponse(CamelModel):
    data: EventOut


class EventsListResponse(CamelModel):
    data: list[EventOut]
    pagination: Pagination
