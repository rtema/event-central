"""Document-template API schemas (camelCase JSON, tag: Document Templates)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field, field_validator
from src.core.schemas import (
    MASKED_SECRET,
    Base64Str,
    CamelModel,
    CommaSeparatedListStr,
    Locale,
    MultiLanguageLabel,
    Pagination,
    split_comma_separated_list,
)

EMAIL_STATUS_SCHEDULED = 'scheduled'  # Email is scheduled to be sent out
EMAIL_STATUS_IN_PROGRESS = 'in-progress'  # Email is currently being sent
EMAIL_STATUS_DELIVERED = 'delivered'  # Email was successfully delivered
EMAIL_STATUS_RETRY = 'retry'  # Email delivery failed, but will be retried
EMAIL_STATUS_FAILED = 'failed'  # Email delivery failed
EMAIL_STATUS_CANCELLED = 'cancelled'  # Email delivery cancelled by user

EmailStatus = Literal["scheduled", "in-progress",
                      "delivered", "retry", "failed", "cancelled"]

# One of: "starttls" | "ssl" | "plain" (mirrors EmailSender.security).
SmtpSecurity = Literal["starttls", "ssl", "plain"]

# --------------------------------------------------------------------------- #
# Email senders
# --------------------------------------------------------------------------- #


class EmailSenderRequest(CamelModel):
    label: dict[str, str]
    from_email: str
    from_name: str | None = None
    reply_to: str | None = None
    host: str
    port: int = 587
    security: SmtpSecurity = "starttls"
    username: str | None = None
    # Sent verbatim to update the stored SMTP password. On update this is a full
    # replace like every other field: omitting it (null) clears the stored
    # password rather than leaving it untouched.
    password: str | None = None
    # Purposes this sender may be selected for, e.g. ["auth", "default"]. Among
    # senders that serve a purpose, the one with the highest priority wins.
    purposes: list[str] = Field(default_factory=list)
    priority: int = 0


class EmailSenderOut(CamelModel):
    id: uuid.UUID
    label: MultiLanguageLabel | None = None
    from_email: str
    from_name: str | None = None
    reply_to: str | None = None
    host: str
    port: int
    security: str
    username: str | None = None
    password: str | None = None
    purposes: list[str] = Field(default_factory=list)
    priority: int
    created_by: str | None = None
    created_at: dt.datetime
    deleted_by: str | None = None
    deleted_at: dt.datetime | None = None

    @field_validator("password", mode="before")
    @classmethod
    def _mask_password(cls, value: object) -> str | None:
        # Never expose the stored value (it is ciphertext anyway). Return a
        # fixed placeholder when a password is set, and null when it is not.
        return MASKED_SECRET if value else None


class EmailSenderResponse(CamelModel):
    data: EmailSenderOut


class EmailSendersListResponse(CamelModel):
    data: list[EmailSenderOut]
    pagination: Pagination


class EmailSenderSearchParams(CamelModel):
    q: str | None = Field(
        default=None, description="Generic free-text search term")

    security: Annotated[list[SmtpSecurity] | None,
                        BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated security modes, e.g. starttls,ssl",
    )


class EmailSenderSearchResponse(CamelModel):
    data: list[EmailSenderOut]
    pagination: Pagination
    search: EmailSenderSearchParams


# --------------------------------------------------------------------------- #
# Email templates
# --------------------------------------------------------------------------- #
class EmailTemplateFileCreateRequest(CamelModel):
    key: str
    file_id: uuid.UUID | None = None
    file: Base64Str | None = None


class EmailTemplateFileUpdateRequest(CamelModel):
    key: str


class EmailTemplateFileOut(CamelModel):
    id: uuid.UUID
    email_template_id: uuid.UUID
    file_id: uuid.UUID
    type: str
    key: str | None = None
    font_name: str | None = None
    font_weight: int | None = None


class EmailTemplateFileResponse(CamelModel):
    data: EmailTemplateFileOut


class EmailTemplateVersionOut(CamelModel):
    id: uuid.UUID
    email_template_id: uuid.UUID
    locale: str
    label: MultiLanguageLabel
    subject: str
    preview_text: str
    html: str
    purposes: list[str] = Field(default_factory=list)
    priority: int
    created_by: str | None = None
    created_at: dt.datetime


class EmailTemplateVersionResponse(CamelModel):
    data: EmailTemplateVersionOut


class EmailTemplateRequest(CamelModel):
    locale: str
    label: dict[str, str]
    subject: str
    preview_text: str
    html: str
    purposes: list[str] = Field(default_factory=list)
    priority: int = 0


class EmailTemplateOut(CamelModel):
    id: uuid.UUID
    locale: str
    label: MultiLanguageLabel | None = None
    subject: str
    preview_text: str
    html: str
    purposes: list[str] = Field(default_factory=list)
    priority: int
    created_by: str | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    deleted_by: str | None = None
    deleted_at: dt.datetime | None = None


class EmailTemplateResponse(CamelModel):
    data: EmailTemplateOut


class EmailTemplateFilesResponse(CamelModel):
    data: list[EmailTemplateFileOut]


class EmailTemplateVersionsResponse(CamelModel):
    data: list[EmailTemplateVersionOut]


class EmailTemplatePreviewResponse(CamelModel):
    subject: str
    body: str
    version_id: str


class EmailTemplatesListResponse(CamelModel):
    data: list[EmailTemplateOut]
    pagination: Pagination

# --------------------------------------------------------------------------- #
# Emails
# --------------------------------------------------------------------------- #


class EmailAttachmentOut(CamelModel):
    id: uuid.UUID
    email_id: uuid.UUID
    file_id: uuid.UUID
    file_name: str


class EmailOut(CamelModel):
    id: uuid.UUID
    email_template_version_id: uuid.UUID
    email_sender_id: uuid.UUID
    locale: str

    to: list[str]
    cc: list[str]
    bcc: list[str]
    sender: str
    subject: str
    body: str

    status: str
    send_after: dt.datetime
    retry_after: dt.datetime | None
    retries: int
    delivered_at: dt.datetime |None
    server_response: str | None

    created_by: str | None = None
    created_at: dt.datetime


class EmailResponse(CamelModel):
    data: EmailOut


class EmailAttachmentsResponse(CamelModel):
    data: list[EmailAttachmentOut]


class EmailsListResponse(CamelModel):
    data: list[EmailOut]
    pagination: Pagination


class EmailSearchParams(CamelModel):
    q: str | None = Field(
        default=None, description="Generic free-text search term")

    email_template: CommaSeparatedListStr = Field(
        default=None,
        description="Comma-separated list of email templates",
    )
    has_attachments: Annotated[list[bool] | None,
                               BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated booleans, e.g. true,false"
    )
    email_sender: CommaSeparatedListStr = Field(
        default=None,
        description="Comma-separated list of email senders",
    )
    status: Annotated[list[EmailStatus] | None,
                      BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated types, e.g. invoice,cancellation"
    )
    locale: Annotated[list[Locale] | None, BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated locales, e.g. de,en"
    )


class EmailSearchResponse(CamelModel):
    data: list[EmailOut]
    pagination: Pagination
    search: EmailSearchParams
