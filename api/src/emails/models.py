from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    DeletedAtMixin,
    DeletedByMixin,
    TZDateTime,
    UpdatedAtMixin,
    UUIDType,
    uuid_pk,
)
from src.files.models import File


class EmailSender(Base, CreatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    __tablename__ = "email_senders"

    id: Mapped[uuid.UUID] = uuid_pk()

    # MultiLanguageLabel
    label: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)

    # from, names, etc
    from_email: Mapped[str] = mapped_column(String(255), nullable=False)
    from_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None)
    reply_to: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None)

    # Connection setting
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False, default=587)
    # One of SmtpSecurity: "starttls" | "ssl" | "plain".
    security: Mapped[str] = mapped_column(
        String(16), nullable=False, default="starttls")
    username: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default=None)
    # Stored encrypted at rest (Fernet);
    password: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None)

    # Routing / selection
    # A sender can serve several purposes at once, e.g. ["auth", "default"].
    # The resolver picks the highest-priority live sender that serves the
    # requested purpose, falling back to the highest-priority live sender
    # overall when no sender is configured for that purpose. Higher wins.
    purposes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    emails: Mapped[list[Email]] = relationship(
        back_populates="email_sender")


class Email(
    Base,
    CreatedAtMixin,
    CreatedByMixin
):
    __tablename__ = "emails"

    id: Mapped[uuid.UUID] = uuid_pk()

    email_template_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("email_template_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    email_sender_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("email_senders.id", ondelete="SET NULL"),
        nullable=True,
    )

    locale: Mapped[str] = mapped_column(
        String(2), nullable=False, default="de")

    to: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    cc: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    bcc: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    sender: Mapped[str] = mapped_column(Text)

    subject: Mapped[str] = mapped_column(Text)
    body: Mapped[str] = mapped_column(Text)

    # Status, etc.
    # status: ...
    # send_after: Email are sent asynchronously.
    #             If the send_after is in the past, async task will try to sent the email.
    # retry_after: Exponential backup, retry only after once this time has passed
    # retries: how many retries have happened
    # delivered_at: When was this email actually delivered
    # server_response: What response did the server send
    status: Mapped[str | None] = mapped_column(Text, nullable=True)
    send_after: Mapped[dt.datetime] = mapped_column(
        TZDateTime, nullable=False, server_default=func.now()
    )
    retry_after: Mapped[dt.datetime | None] = mapped_column(
        TZDateTime, nullable=True, default=None)
    retries: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    delivered_at: Mapped[dt.datetime | None] = mapped_column(
        TZDateTime, nullable=True, default=None)
    server_response = mapped_column(Text, nullable=True, default=None)

    # Relationships
    email_sender: Mapped[EmailSender | None] = relationship(
        back_populates="emails"
    )
    email_template_version: Mapped[EmailTemplateVersion | None] = relationship(
        back_populates="emails"
    )
    email_attachments: Mapped[list[EmailAttachment]] = relationship(
        back_populates="emails",
        order_by="EmailAttachment.file_name"
    )


class EmailAttachment(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "email_attachments"

    id: Mapped[uuid.UUID] = uuid_pk()

    email_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("emails.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_name: Mapped[str] = mapped_column(
        String(2048), nullable=False, default=None)

    # Relationships
    emails: Mapped[list[Email] | None] = relationship(
        back_populates="email_attachments")
    file: Mapped[File | None] = relationship()

class EmailTemplate(
    Base,
    CreatedAtMixin,
    CreatedByMixin,
    UpdatedAtMixin,
    DeletedAtMixin,
    DeletedByMixin
):
    __tablename__ = "email_templates"

    id: Mapped[uuid.UUID] = uuid_pk()

    locale: Mapped[str] = mapped_column(
        String(2), nullable=False, default="de")

    # MultiLanguageLabel
    label: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)

    # Content
    subject: Mapped[str] = mapped_column(Text)
    preview_text: Mapped[str] = mapped_column(Text)
    html: Mapped[str] = mapped_column(Text)

    # Routing / selection
    # A template can serve several purposes at once, e.g. ["reset-password", "confirm-email"].
    # The resolver picks the highest-priority live template that serves the
    # requested purpose
    purposes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    email_template_versions: Mapped[list[EmailTemplateVersion]] = relationship(
        back_populates="email_template"
    )
    email_template_files: Mapped[list[EmailTemplateFile]] = relationship(
        back_populates="email_template",
        order_by="EmailTemplateFile.key"
    )


class EmailTemplateVersion(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "email_template_versions"

    id: Mapped[uuid.UUID] = uuid_pk()

    email_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    locale: Mapped[str] = mapped_column(
        String(2), nullable=False, default="de")

    # MultiLanguageLabel
    label: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)

    subject: Mapped[str] = mapped_column(Text)
    preview_text: Mapped[str] = mapped_column(Text)
    html: Mapped[str] = mapped_column(Text)

    purposes: Mapped[list[str]] = mapped_column(ARRAY(Text), default=list)
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    # Relationships
    email_template: Mapped[EmailTemplate] = relationship(
        back_populates="email_template_versions"
    )
    emails: Mapped[list[Email]] = relationship(
        back_populates="email_template_version",
        lazy="selectin",
        order_by="Email.created_at"
    )


class EmailTemplateFile(Base, CreatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    __tablename__ = "email_template_files"

    id: Mapped[uuid.UUID] = uuid_pk()

    email_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("email_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    file_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("files.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Type of file ('image' or 'font')
    type: Mapped[str] = mapped_column(String(256), nullable=False)

    # Key
    # the templates are jinja templates. files can be referenced by {{ files.key }}
    # Therefore this key only needs to unique within a single template
    key: Mapped[str] = mapped_column(String(2048), nullable=True, default=None)

    # Relationships
    email_template: Mapped[EmailTemplate] = relationship(
        back_populates="email_template_files")
    file: Mapped[File] = relationship()