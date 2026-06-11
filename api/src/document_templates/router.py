"""Document-template endpoints (/api/v1/document-templates, tag: Document Templates).

Note: the ``/public`` routes are declared before ``/{document_template_id}`` so
the literal segment is matched ahead of the UUID path parameter.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_BACKEND_READ, SCOPE_BACKEND_WRITE
from src.document_templates import service
from src.document_templates.schemas import (
    DocumentTemplateOut,
    DocumentTemplateResponse,
    DocumentTemplatesListResponse,
    PublicDocumentTemplateCreateRequest,
    PublicDocumentTemplateOut,
    PublicDocumentTemplateResponse,
    PublicDocumentTemplatesListResponse,
    PublicDocumentTemplateUpdateRequest,
)

router = APIRouter(prefix="/api/v1/document-templates", tags=["Document Templates"])


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
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ)),
) -> PublicDocumentTemplatesListResponse:
    templates, total = service.list_public_document_templates(
        db, limit=page.limit, offset=page.offset
    )
    return PublicDocumentTemplatesListResponse(
        data=[PublicDocumentTemplateOut.model_validate(t) for t in templates],
        pagination=make_pagination(total, limit=page.limit, offset=page.offset),
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
    actor: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_WRITE)),
) -> PublicDocumentTemplateResponse:
    template = service.create_public_document_template(
        db,
        public_id=body.id,
        body=body.model_dump(exclude_unset=True, exclude={"id"}),
        actor=actor.sub,
    )
    return PublicDocumentTemplateResponse(data=PublicDocumentTemplateOut.model_validate(template))


@router.get(
    "/public/{public_id}",
    response_model=PublicDocumentTemplateResponse,
    summary="Get a public document template",
)
def get_public_document_template(
    public_id: str,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ)),
) -> PublicDocumentTemplateResponse:
    template = service.get_public_document_template(db, public_id)
    return PublicDocumentTemplateResponse(data=PublicDocumentTemplateOut.model_validate(template))


@router.post(
    "/public/{public_id}",
    response_model=PublicDocumentTemplateResponse,
    summary="Update a public document template",
)
def update_public_document_template(
    public_id: str,
    body: PublicDocumentTemplateUpdateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_WRITE)),
) -> PublicDocumentTemplateResponse:
    template = service.update_public_document_template(
        db, public_id, body=body.model_dump(exclude_unset=True), actor=actor.sub
    )
    return PublicDocumentTemplateResponse(data=PublicDocumentTemplateOut.model_validate(template))


# --------------------------------------------------------------------------- #
# Private templates
# --------------------------------------------------------------------------- #
@router.get("", response_model=DocumentTemplatesListResponse, summary="List document templates")
def list_document_templates(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ)),
) -> DocumentTemplatesListResponse:
    templates, total = service.list_document_templates(db, limit=page.limit, offset=page.offset)
    return DocumentTemplatesListResponse(
        data=[DocumentTemplateOut.model_validate(t) for t in templates],
        pagination=make_pagination(total, limit=page.limit, offset=page.offset),
    )


@router.get(
    "/{document_template_id}",
    response_model=DocumentTemplateResponse,
    summary="Get a document template",
)
def get_document_template(
    document_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_BACKEND_READ)),
) -> DocumentTemplateResponse:
    template = service.get_document_template(db, document_template_id)
    return DocumentTemplateResponse(data=DocumentTemplateOut.model_validate(template))
