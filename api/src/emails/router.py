"""Email endpoints (/api/v1/emails, tag: Emails) & 
                   (/api/v1/email-templates, tag: Email Templates)
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_BACKEND_READ_ALL, SCOPE_BACKEND_WRITE_ALL
from src.emails import service
from src.emails.renderer import render_email
from src.emails.schemas import (
    EmailAttachmentOut,
    EmailAttachmentsResponse,
    EmailOut,
    EmailResponse,
    EmailSearchParams,
    EmailSearchResponse,
    EmailSenderOut,
    EmailSenderRequest,
    EmailSenderResponse,
    EmailSenderSearchParams,
    EmailSenderSearchResponse,
    EmailSendersListResponse,
    EmailsListResponse,
    EmailTemplateFileCreateRequest,
    EmailTemplateFileOut,
    EmailTemplateFileResponse,
    EmailTemplateFilesResponse,
    EmailTemplateFileUpdateRequest,
    EmailTemplateOut,
    EmailTemplatePreviewResponse,
    EmailTemplateRequest,
    EmailTemplateResponse,
    EmailTemplatesListResponse,
    EmailTemplateVersionOut,
    EmailTemplateVersionsResponse,
)
from src.template_placeholders.dummy_data import (
    dummy_event,
    dummy_invoice,
    dummy_order,
    dummy_user,
)

email_templates_router = APIRouter(prefix="/api/v1/email-templates",
                                   tags=["Email Templates"])

email_router = APIRouter(prefix="/api/v1/emails",
                         tags=["Emails"])

email_senders_router = APIRouter(prefix="/api/v1/email-senders",
                                 tags=["Email Senders"])

# --------------------------------------------------------------------------- #
# Email templates
# --------------------------------------------------------------------------- #


@email_templates_router.get(
    "",
    response_model=EmailTemplatesListResponse,
    summary="List email templates")
def list_email_templates(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailTemplatesListResponse:
    email_templates, total = service.list_email_templates(
        db, limit=page.limit, offset=page.offset)
    return EmailTemplatesListResponse(
        data=[EmailTemplateOut.model_validate(
            t) for t in email_templates],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@email_templates_router.post(
    "",
    response_model=EmailTemplateResponse,
    summary="Create an email template")
def create_email_template(
    body: EmailTemplateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailTemplateResponse:
    email_template = service.create_email_template(
        db, body=body, actor=actor.sub)
    return EmailTemplateResponse(data=EmailTemplateOut.model_validate(email_template))


@email_templates_router.get(
    "/{email_template_id}",
    response_model=EmailTemplateResponse,
    summary="Get an email template",
)
def get_email_template(
    email_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailTemplateResponse:
    email_template = service.get_email_template(db, email_template_id)
    return EmailTemplateResponse(data=EmailTemplateOut.model_validate(email_template))


@email_templates_router.patch(
    "/{email_template_id}",
    response_model=EmailTemplateResponse,
    summary="Get an email template",
)
def update_email_template(
    email_template_id: uuid.UUID,
    body: EmailTemplateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailTemplateResponse:
    email_template = service.update_email_template(
        db, email_template_id, body=body, actor=actor.sub)
    return EmailTemplateResponse(data=EmailTemplateOut.model_validate(email_template))


@email_templates_router.delete(
    "/{email_template_id}",
    response_model=EmailTemplateResponse,
    summary="Delete an email template",
)
def delete_email_template(
    email_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailTemplateResponse:
    email_template = service.delete_email_template(
        db, email_template_id, actor=actor.sub)
    return EmailTemplateResponse(data=EmailTemplateOut.model_validate(email_template))


@email_templates_router.get(
    "/{email_template_id}/files",
    response_model=EmailTemplateFilesResponse,
    summary="Get all files referenced in an email template",
)
def get_email_template_files(
    email_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailTemplateFilesResponse:
    email_template = service.get_email_template(db, email_template_id)
    return EmailTemplateFilesResponse(
        data=[EmailTemplateFileOut.model_validate(
            f) for f in email_template.email_template_files],
    )


@email_templates_router.post(
    "/{email_template_id}/files",
    response_model=EmailTemplateFileResponse,
    summary="Create a new email template file",
)
def create_email_template_file(
    email_template_id: uuid.UUID,
    body: EmailTemplateFileCreateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailTemplateFileResponse:
    email_template_file = service.create_email_template_file(
        db, email_template_id, body=body, actor=actor.sub)
    return EmailTemplateFileResponse(
        data=EmailTemplateFileOut.model_validate(email_template_file)
    )


@email_templates_router.get(
    "/{email_template_id}/files/{email_template_file_id}",
    response_model=EmailTemplateFileResponse,
    summary="Get an email template file",
)
def get_email_template_file(
    email_template_id: uuid.UUID,
    email_template_file_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailTemplateFileResponse:
    _email_template = service.get_email_template(db, email_template_id)
    email_template_file = service.get_email_template_file(
        db, email_template_file_id)
    return EmailTemplateFileResponse(
        data=EmailTemplateFileOut.model_validate(email_template_file)
    )


@email_templates_router.patch(
    "/{email_template_id}/files/{email_template_file_id}",
    response_model=EmailTemplateFileResponse,
    summary="Update an email template file",
)
def update_email_template_file(
    email_template_id: uuid.UUID,
    email_template_file_id: uuid.UUID,
    body: EmailTemplateFileUpdateRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailTemplateFileResponse:
    email_template_file = service.update_email_template_file(
        db, email_template_id, email_template_file_id, body=body, actor=actor.sub)
    return EmailTemplateFileResponse(
        data=EmailTemplateFileOut.model_validate(email_template_file)
    )


@email_templates_router.delete(
    "/{email_template_id}/files/{email_template_file_id}",
    response_model=EmailTemplateFileResponse,
    summary="Remove an email template file",
)
def delete_email_template_file(
    email_template_id: uuid.UUID,
    email_template_file_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailTemplateFileResponse:
    email_template_file = service.delete_email_template_file(
        db, email_template_id, email_template_file_id, actor=actor.sub)
    return EmailTemplateFileResponse(
        data=EmailTemplateFileOut.model_validate(email_template_file)
    )


@email_templates_router.get(
    "/{email_template_id}/versions",
    response_model=EmailTemplateVersionsResponse,
    summary="Get all versions (history) of the email template",
)
def get_email_template_versions(
    email_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailTemplateVersionsResponse:
    email_template = service.get_email_template(db, email_template_id)
    return EmailTemplateVersionsResponse(
        data=[EmailTemplateVersionOut.model_validate(
            f) for f in email_template.email_template_versions],
    )


@email_templates_router.get(
    "/{email_template_id}/preview",
    response_model=EmailTemplatePreviewResponse,
    summary="Generate a preview of the email template",
)
def get_email_template_preview(
    email_template_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailTemplatePreviewResponse:
    email_template = service.get_email_template(db, email_template_id)

    #  generate the preview
    body, subject, version_id = render_email(
        db,
        email_template,
        user=dummy_user,
        event=dummy_event,
        order=dummy_order,
        invoice=dummy_invoice,
        extra={
            'code': '123456',
            'link': 'https://www.tema.de/cores/event-marketing'
        }
    )

    # return the preview email
    return EmailTemplatePreviewResponse(
        subject=subject,
        body=body,
        version_id=str(version_id)
    )


# --------------------------------------------------------------------------- #
# Email senders
# --------------------------------------------------------------------------- #
@email_senders_router.get(
    "",
    response_model=EmailSendersListResponse,
    summary="List email senders")
def list_email_senders(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailSendersListResponse:
    email_senders, total = service.list_email_senders(
        db, limit=page.limit, offset=page.offset)
    return EmailSendersListResponse(
        data=[EmailSenderOut.model_validate(s) for s in email_senders],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@email_senders_router.get(
    "/search",
    response_model=EmailSenderSearchResponse,
    summary="Search email senders")
def search_email_senders(
    page: Annotated[PageParams, Depends(page_params)],
    search_params: Annotated[EmailSenderSearchParams, Query()],
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailSenderSearchResponse:
    email_senders, total = service.search_email_senders(
        db, limit=page.limit, offset=page.offset, search_params=search_params)
    return EmailSenderSearchResponse(
        data=[EmailSenderOut.model_validate(s) for s in email_senders],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
        search=search_params,
    )


@email_senders_router.post(
    "",
    response_model=EmailSenderResponse,
    summary="Create an email sender")
def create_email_sender(
    body: EmailSenderRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailSenderResponse:
    email_sender = service.create_email_sender(
        db, body=body, actor=actor.sub)
    return EmailSenderResponse(data=EmailSenderOut.model_validate(email_sender))


@email_senders_router.get(
    "/{email_sender_id}",
    response_model=EmailSenderResponse,
    summary="Get an email sender",
)
def get_email_sender(
    email_sender_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailSenderResponse:
    email_sender = service.get_email_sender(db, email_sender_id)
    return EmailSenderResponse(data=EmailSenderOut.model_validate(email_sender))


@email_senders_router.patch(
    "/{email_sender_id}",
    response_model=EmailSenderResponse,
    summary="Update an email sender",
)
def update_email_sender(
    email_sender_id: uuid.UUID,
    body: EmailSenderRequest,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailSenderResponse:
    email_sender = service.update_email_sender(
        db, email_sender_id, body=body, actor=actor.sub)
    return EmailSenderResponse(data=EmailSenderOut.model_validate(email_sender))


@email_senders_router.delete(
    "/{email_sender_id}",
    response_model=EmailSenderResponse,
    summary="Delete an email sender",
)
def delete_email_sender(
    email_sender_id: uuid.UUID,
    db: Session = Depends(get_db),
    actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_WRITE_ALL)),
) -> EmailSenderResponse:
    email_sender = service.delete_email_sender(
        db, email_sender_id, actor=actor.sub)
    return EmailSenderResponse(data=EmailSenderOut.model_validate(email_sender))


# --------------------------------------------------------------------------- #
# Emails
# --------------------------------------------------------------------------- #
@email_router.get("", response_model=EmailsListResponse, summary="List emails")
def list_emails(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailsListResponse:
    emails, total = service.list_emails(
        db, limit=page.limit, offset=page.offset)
    return EmailsListResponse(
        data=[EmailOut.model_validate(e) for e in emails],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@email_router.get("/search", response_model=EmailSearchResponse, summary="Search emails")
def search_emails(
    page: Annotated[PageParams, Depends(page_params)],
    search_params: Annotated[EmailSearchParams, Query()],
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailSearchResponse:
    emails, total = service.search_emails(
        db, limit=page.limit, offset=page.offset, search_params=search_params)
    return EmailSearchResponse(
        data=[EmailOut.model_validate(e) for e in emails],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
        search=search_params,
    )


@email_router.get(
    "/{email_id}",
    response_model=EmailResponse,
    summary="Get an email",
)
def get_email(
    email_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailResponse:
    email = service.get_email(db, email_id)
    return EmailResponse(data=EmailOut.model_validate(email))


@email_router.get(
    "/{email_id}/attachments",
    response_model=EmailAttachmentsResponse,
    summary="Get all attachments of an email",
)
def get_email_attachments(
    email_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_BACKEND_READ_ALL)),
) -> EmailAttachmentsResponse:
    email = service.get_email(db, email_id)
    return EmailAttachmentsResponse(
        data=[EmailAttachmentOut.model_validate(
            f) for f in email.email_attachments],
    )
