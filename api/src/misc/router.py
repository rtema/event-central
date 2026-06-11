"""Misc endpoints (tag: Misc): liveness / readiness probes.

Other Misc endpoints from the spec (e.g. /api/v1/taxes) will be added here in
later steps.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.core.deps import get_db

router = APIRouter(tags=["Misc"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db", summary="Readiness probe")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}
