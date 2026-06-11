"""Cross-cutting FastAPI dependencies (infrastructure only)."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy.orm import Session

from src.core.db import get_session


def get_db() -> Iterator[Session]:  # pragma: no cover - thin wrapper
    yield from get_session()
