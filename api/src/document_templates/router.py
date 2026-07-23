"""Document-template endpoints (/api/v1/document-templates, tag: Document Templates).

Note: the ``/public`` routes are declared before ``/{document_template_id}`` so
the literal segment is matched ahead of the UUID path parameter.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_BACKEND_READ_ALL, SCOPE_BACKEND_WRITE_ALL
from src.document_templates import service
from src.document_templates.renderer.dummy_data import (
    dummy_event,
    dummy_invoice,
    dummy_order,
    make_dummy_finisher,
)
from src.document_templates.renderer.main import render_document
from src.document_templates.schemas import (
    DocumentTemplateFileOut,
    DocumentTemplateFilesResponse,
    DocumentTemplateOut,
    DocumentTemplateResponse,
    DocumentTemplatesListResponse,
    PublicDocumentTemplateCreateRequest,
    PublicDocumentTemplateOut,
    PublicDocumentTemplateResponse,
    PublicDocumentTemplatesListResponse,
    PublicDocumentTemplateUpdateRequest,
)

router = APIRouter(prefix="/api/v1/document-templates",
                   tags=["Document Templates"])


# --------------------------------------------------------------------------- #
# Public templates (declared first; literal segment beats the UUID param)
# --------------------------------------------------------------------------- #
@router.get(
    "/public",
    response_model=PublicDocumentTemplatesListResponse,
    summary="List public document templates",
)
def list_public_document_templates(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> PublicDocumentTemplatesListResponse:
    public_document_templates, total = service.list_public_document_templates(
        db, limit=page.limit, offset=page.offset
    )
    return PublicDocumentTemplatesListResponse(
        data=[PublicDocumentTemplateOut.model_validate(
            t) for t in public_document_templates],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@router.post(
    "/public",
    response_model=PublicDocumentTemplateResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a public document template",
)
def create_public_document_template(
    body: PublicDocumentTemplateCreateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> PublicDocumentTemplateResponse:
    public_document_template = service.create_public_document_template(
        db,
        public_document_template_id=body.id,
        body=body,
        actor=actor.sub
    )
    return PublicDocumentTemplateResponse(
        data=PublicDocumentTemplateOut.model_validate(public_document_template)
    )


@router.get(
    "/public/{public_document_template_id}",
    response_model=PublicDocumentTemplateResponse,
    summary="Get a public document template",
)
def get_public_document_template(
    public_document_template_id: str,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> PublicDocumentTemplateResponse:
    public_document_template = service.get_public_document_template(
        db, public_document_template_id)
    return PublicDocumentTemplateResponse(
        data=PublicDocumentTemplateOut.model_validate(public_document_template)
    )


@router.post(
    "/public/{public_document_template_id}",
    response_model=PublicDocumentTemplateResponse,
    summary="Update a public document template",
)
def update_public_document_template(
    public_document_template_id: str,
    body: PublicDocumentTemplateUpdateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> PublicDocumentTemplateResponse:
    public_document_template = service.update_public_document_template(
        db, public_document_template_id, body=body, actor=actor.sub
    )
    return PublicDocumentTemplateResponse(
        data=PublicDocumentTemplateOut.model_validate(public_document_template)
    )


# --------------------------------------------------------------------------- #
# Private templates
# --------------------------------------------------------------------------- #
@router.get("", response_model=DocumentTemplatesListResponse, summary="List document templates")
def list_document_templates(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> DocumentTemplatesListResponse:
    document_templates, total = service.list_document_templates(
        db, limit=page.limit, offset=page.offset)
    return DocumentTemplatesListResponse(
        data=[DocumentTemplateOut.model_validate(
            t) for t in document_templates],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@router.get(
    "/{document_template_id}",
    response_model=DocumentTemplateResponse,
    summary="Get a document template",
)
def get_document_template(
    document_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> DocumentTemplateResponse:
    document_template = service.get_document_template(db, document_template_id)
    return DocumentTemplateResponse(data=DocumentTemplateOut.model_validate(document_template))


@router.get(
    "/{document_template_id}/files",
    response_model=DocumentTemplateFilesResponse,
    summary="Get all files referenced in a document template",
)
def get_document_template_files(
    document_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> DocumentTemplateFilesResponse:
    document_template = service.get_document_template(db, document_template_id)
    return DocumentTemplateFilesResponse(
        data=[DocumentTemplateFileOut.model_validate(
            f) for f in document_template.document_template_files],
    )


@router.get(
    "/{document_template_id}/preview",
    response_model=DocumentTemplateFilesResponse,
    summary="Generate a preview of the document template",
)
def get_document_template_preview(
    document_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> Response:
    document_template = service.get_document_template(db, document_template_id)

    # determine locale from query parameter
    locale = "de"

    #  generate the preview
    data = render_document(
        document_template,
        locale,
        event=dummy_event,
        order=dummy_order,
        invoice=dummy_invoice,
        attachments=[],
        pdf_variant="pdf/a-3b",
        finisher=make_dummy_finisher(),
    )

    # return the preview document
    return Response(
        content=data.getvalue(),
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'inline; filename="{document_template.id}.pdf"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=3",
        },
    )
