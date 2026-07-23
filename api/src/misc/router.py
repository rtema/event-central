"""Misc endpoints (tag: Misc): liveness / readiness probes, taxes, scopes."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import MultiLanguageLabel, make_pagination
from src.core.scopes import SCOPE_BACKEND_READ_ALL, build_scope_catalogue
from src.invoices import service as invoicing_service
from src.invoices.schemas import AccountingEntitiesListResponse, TaxesListResponse, TaxOut
from src.misc.schemas import ScopeOut, ScopesListResponse
from src.storage.s3 import get_storage

router = APIRouter(tags=["Misc"])


@router.get("/health", summary="Liveness probe")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/db", summary="DB connection probe")
def health_db(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    return {"status": "ready"}


@router.get("/health/storage", summary="Storage connection probe")
def health_storage(db: Session = Depends(get_db)) -> JSONResponse:
    status, code = get_storage().test_connections()
    return JSONResponse(status, code)


@router.get(
    "/api/v1/taxes",
    response_model=TaxesListResponse,
    summary="List tax rates"
)
def list_taxes(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> TaxesListResponse:
    taxes, total = invoicing_service.list_all_taxes(
        db, limit=page.limit, offset=page.offset)
    return TaxesListResponse(
        data=[TaxOut.model_validate(t) for t in taxes],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@router.get(
    "/api/v1/accounting-entities",
    response_model=AccountingEntitiesListResponse,
    summary="List tax rates"
)
def list_accounting_entities(
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> AccountingEntitiesListResponse:
    return AccountingEntitiesListResponse(
        data=invoicing_service.list_all_accounting_entities(db),
    )


@router.get(
    "/api/v1/scopes",
    response_model=ScopesListResponse,
    summary="List scopes"
)
def list_scopes(
     db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> ScopesListResponse:
    scope_catalogue = build_scope_catalogue(db, include_dynamic=True)
    return ScopesListResponse(
        data=[
            ScopeOut(scope=s.scope, label=MultiLanguageLabel(de=s.de, en=s.en))
            for s in scope_catalogue
        ]
    )
