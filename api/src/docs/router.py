"""Misc endpoints (tag: Misc): liveness / readiness probes, taxes, scopes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.scopes import SCOPE_BACKEND_READ_ALL

router = APIRouter(prefix="/api/v1/docs", tags=["Docs"])


BASE_DIR = Path(__file__).resolve().parent
SPEC_PATH = BASE_DIR / "spec.yaml"


@router.get("/api-spec.yaml", summary="Open API spec")
def get_api_spec(
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> FileResponse:
    return FileResponse(
        path=SPEC_PATH,
        media_type="application/yaml",
        # filename="api-spec.yaml",
    )
