"""Cross-cutting FastAPI dependencies (infrastructure only)."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass

from fastapi import Query
from sqlalchemy.orm import Session

from src.core.db import get_session


def get_db() -> Iterator[Session]:  # pragma: no cover - thin wrapper
    yield from get_session()


@dataclass(slots=True)
class PageParams:
    """Resolved ``limit``/``offset`` for list endpoints (spec: Limit, Offset)."""

    limit: int
    offset: int


def page_params(
    limit: int = Query(default=100, ge=1, le=1000,
                       description="Max items to return"),
    # The spec types Offset as a string, but the Pagination.currentOffset it
    # pairs with is an integer; a non-negative integer offset is used here.
    offset: int = Query(default=0, ge=0, description="Items to skip"),
) -> PageParams:
    return PageParams(limit=limit, offset=offset)
