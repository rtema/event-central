"""Invoice endpoints (/api/v1/invoices, tag: Invoicing)."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.auth.deps import (
    AuthenticatedActor,
    get_authenticated_actor,
    require_all_scopes,
)
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import (
    SCOPE_INVOICES_READ_ALL,
)
from src.invoices import service
from src.invoices.deps import require_invoice_scope
from src.invoices.schemas import (
    InvoiceCreateRequest,
    InvoiceCreateResponse,
    InvoiceExportRequest,
    InvoiceLineItemOut,
    InvoiceLineItemsListResponse,
    InvoiceLinkRequest,
    InvoiceLinkResponse,
    InvoiceOut,
    InvoiceResponse,
    InvoicesExportResponse,
    InvoicesListResponse,
    InvoiceTaxesListResponse,
    TaxOut,
)

router = APIRouter(prefix="/api/v1/invoices", tags=["Invoicing"])


@router.get("", response_model=InvoicesListResponse, summary="List invoices")
def list_invoices(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_INVOICES_READ_ALL)),
) -> InvoicesListResponse:
    invoices, total = service.list_invoices(db, limit=page.limit, offset=page.offset)
    return InvoicesListResponse(
        data=[InvoiceOut.model_validate(i) for i in invoices],
        pagination=make_pagination(total, limit=page.limit, offset=page.offset),
    )


@router.post(
    "",
    response_model=InvoiceCreateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an invoice",
)
def create_invoice(
    body: InvoiceCreateRequest,
    db: Session = Depends(get_db),
    # Any authenticated actor may attempt creation; the precise per-event scope
    # (invoices:write:{all|own|<eventId>}) is enforced inside the service once
    # the request's event has been resolved.
    actor: AuthenticatedActor = Depends(get_authenticated_actor),
) -> InvoiceCreateResponse:
    return service.create_invoice(db, payload=body.model_dump(exclude_unset=True), actor=actor)


@router.post("/export", response_model=InvoicesExportResponse, summary="Export invoices")
def export_invoices(
    body: InvoiceExportRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(require_all_scopes(SCOPE_INVOICES_READ_ALL)),
) -> InvoicesExportResponse:
    return service.export_invoices(
        db,
        accounting_entity=body.accounting_entity,
        export_format=body.format,
        actor=actor.sub,
    )


@router.get("/{invoice_id}", response_model=InvoiceResponse, summary="Get an invoice")
def get_invoice(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_invoice_scope("read")),
) -> InvoiceResponse:
    return InvoiceResponse(data=InvoiceOut.model_validate(service.get_invoice(db, invoice_id)))


@router.get(
    "/{invoice_id}/line-items",
    response_model=InvoiceLineItemsListResponse,
    summary="Line items of an invoice",
)
def get_invoice_line_items(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_invoice_scope("read")),
) -> InvoiceLineItemsListResponse:
    items = service.get_invoice_line_items(db, invoice_id)
    return InvoiceLineItemsListResponse(
        data=[InvoiceLineItemOut.model_validate(i) for i in items]
    )


@router.get(
    "/{invoice_id}/taxes",
    response_model=InvoiceTaxesListResponse,
    summary="Taxes of an invoice",
)
def get_invoice_taxes(
    invoice_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_invoice_scope("read")),
) -> InvoiceTaxesListResponse:
    taxes = service.get_invoice_taxes(db, invoice_id)
    return InvoiceTaxesListResponse(data=[TaxOut.model_validate(t) for t in taxes])


@router.post(
    "/{invoice_id}/link",
    response_model=InvoiceLinkResponse,
    summary="Create a signed download link",
)
def create_invoice_link(
    invoice_id: uuid.UUID,
    body: InvoiceLinkRequest,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_invoice_scope("read")),
) -> InvoiceLinkResponse:
    return service.create_invoice_link(
        db, invoice_id, file_type=body.file_type, expires_in=body.expires_in
    )
