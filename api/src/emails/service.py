"""Business logic for Emails and Email templates (tag: Emails & Email Templates).

Route-facing service functions only: CRUD and search for email senders, email
templates, email-template files and emails. The SMTP/delivery machinery
(rendering + queueing, transport, worker) lives in ``src.emails.deps``.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import uuid
from collections.abc import Sequence
from io import BytesIO
from typing import Any

from sqlalchemy import ColumnElement, Select, String, cast, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session
from src.core.errors import NotFoundError
from src.core.schemas import make_multilanguage_label, resolve_secret
from src.emails.models import (
    Email,
    EmailSender,
    EmailTemplate,
    EmailTemplateFile,
    EmailTemplateVersion,
)
from src.emails.schemas import (
    EmailSearchParams,
    EmailSenderRequest,
    EmailSenderSearchParams,
    EmailTemplateFileCreateRequest,
    EmailTemplateFileUpdateRequest,
    EmailTemplateRequest,
)
from src.files.models import File
from src.files.service import create_file, get_file, get_files_by_hash


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _resolve_email_template_file(
    db: Session, raw_bytes: bytes, *, created_by: str,
) -> File:
    """Return a canonical File for these bytes, reusing an existing row when the
    content hash already exists. New content goes through create_file so it is
    size-bounded, AV-scanned, sniffed and stored exactly like any upload."""
    digest = hashlib.sha256(raw_bytes).hexdigest()

    matches = get_files_by_hash(db, digest)
    if matches:
        file = matches[0]
    else:
        file = create_file(
            db,
            BytesIO(raw_bytes),
            label={},
            base_path="email-template-files",
            created_by=created_by,
            # filename omitted on purpose: extension is derived from the sniffed
            # mime, so we don't risk a spurious extension/mime mismatch.
        )
    return file


# --------------------------------------------------------------------------- #
# Email senders
# --------------------------------------------------------------------------- #
def list_email_senders(
    db: Session, *, limit: int, offset: int
) -> tuple[list[EmailSender], int]:
    total = db.execute(select(func.count()).select_from(
        EmailSender)).scalar_one()
    stmt = (
        select(EmailSender)
        .order_by(EmailSender.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_email_sender(db: Session, sender_id: uuid.UUID) -> EmailSender:
    sender = db.get(EmailSender, sender_id)
    if sender is None:
        raise NotFoundError("email sender not found")
    return sender


def resolve_email_sender(
    db: Session, purpose: str | None = None
) -> EmailSender | None:
    """Pick the sender to send through for ``purpose``.

    Highest-priority live (non-deleted) sender that serves ``purpose``; if no
    sender is configured for it (or ``purpose`` is None), the highest-priority
    live sender overall. ``created_at`` is a deterministic tie-break so equal
    priorities resolve to a stable choice. Raises when no sender exists at all.
    """
    order = (
        EmailSender.priority.desc(),
        EmailSender.created_at.desc(),
    )

    # 1. Highest priority among senders that serve this purpose.
    if purpose is not None:
        sender = db.execute(
            select(EmailSender)
            .where(
                EmailSender.deleted_at.is_(None),
                # `purpose = ANY(email_senders.purposes)`
                EmailSender.purposes.any_() == purpose,
            )
            .order_by(*order)
            .limit(1)
        ).scalars().first()
        if sender is not None:
            return sender

    # 2. Fallback: highest priority overall.
    sender = db.execute(
        select(EmailSender)
        .where(EmailSender.deleted_at.is_(None))
        .order_by(*order)
        .limit(1)
    ).scalars().first()
    if sender is not None:
        return sender

    return None


def search_email_senders(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_params: EmailSenderSearchParams,
) -> tuple[list[EmailSender], int]:
    conditions: list[ColumnElement[bool]] = []

    # filters
    if search_params.security:
        conditions.append(EmailSender.security.in_(search_params.security))

    # text filters
    if search_params.q and search_params.q.strip():
        term: str = search_params.q.strip()
        # escape LIKE wildcards so user input is matched literally
        escaped: str = (
            term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern: str = f"%{escaped}%"
        conditions.append(
            or_(
                EmailSender.from_email.ilike(pattern, escape="\\"),
                EmailSender.from_name.ilike(pattern, escape="\\"),
                EmailSender.reply_to.ilike(pattern, escape="\\"),
                EmailSender.host.ilike(pattern, escape="\\"),
                EmailSender.username.ilike(pattern, escape="\\"),
                cast(EmailSender.label, String).ilike(pattern, escape="\\"),
            )
        )

    # count total
    count_stmt: Select[tuple[int]] = (
        select(func.count()).select_from(EmailSender).where(*conditions)
    )
    total: int = db.execute(count_stmt).scalar_one()

    # build statement
    stmt = (
        select(EmailSender)
        .where(*conditions)
        .order_by(EmailSender.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def create_email_sender(
        db: Session,
        *,
        body: EmailSenderRequest,
        actor: str
) -> EmailSender:
    email_sender = EmailSender(
        label=make_multilanguage_label(body.label),
        from_email=body.from_email,
        from_name=body.from_name,
        reply_to=body.reply_to,
        host=body.host,
        port=body.port,
        security=body.security,
        username=body.username,
        password=resolve_secret(body.password, None),
        purposes=body.purposes,
        priority=body.priority,
        created_at=_now(),
        created_by=actor,
    )
    db.add(email_sender)
    db.flush()

    return email_sender


def update_email_sender(
        db: Session,
        sender_id: uuid.UUID,
        *,
        body: EmailSenderRequest,
        actor: str
) -> EmailSender:
    email_sender = get_email_sender(db, sender_id)

    email_sender.label = make_multilanguage_label(body.label)
    email_sender.from_email = body.from_email
    email_sender.from_name = body.from_name
    email_sender.reply_to = body.reply_to
    email_sender.host = body.host
    email_sender.port = body.port
    email_sender.security = body.security
    email_sender.username = body.username

    # sending back the masked placeholder keeps the stored value,
    # a real value replaces it, and null/empty clears it (see resolve_secret).
    email_sender.password = resolve_secret(
        body.password, email_sender.password)

    email_sender.purposes = body.purposes
    email_sender.priority = body.priority

    db.flush()

    return email_sender


def delete_email_sender(
        db: Session,
        sender_id: uuid.UUID,
        *,
        actor: str
) -> EmailSender:
    now = _now()
    email_sender = get_email_sender(db, sender_id)

    # soft delete
    email_sender.deleted_at = now
    email_sender.deleted_by = actor

    db.flush()

    return email_sender


# --------------------------------------------------------------------------- #
# Email templates
# --------------------------------------------------------------------------- #
def list_email_templates(
    db: Session, *, limit: int, offset: int
) -> tuple[list[EmailTemplate], int]:
    total = db.execute(select(func.count()).select_from(
        EmailTemplate)).scalar_one()
    stmt = (
        select(EmailTemplate)
        .order_by(EmailTemplate.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_email_template(db: Session, template_id: uuid.UUID) -> EmailTemplate:
    template = db.get(EmailTemplate, template_id)
    if template is None:
        raise NotFoundError("email template not found")
    return template


def resolve_email_template(
    db: Session, locale: str, purpose: str
) -> EmailTemplate | None:

    # 1. Highest priority among templates that serve this purpose.
    template = db.execute(
        select(EmailTemplate)
        .where(
            EmailTemplate.deleted_at.is_(None),
            # `purpose = ANY(email_senders.purposes)`
            EmailTemplate.purposes.any_() == purpose,
        )
        .order_by(EmailTemplate.priority.desc(),
                  EmailTemplate.created_at.desc(),)
        .limit(1)
    ).scalars().first()
    if template is not None:
        return template

    # 2. check if a fallback template exits
    # create the template on the fly and return it

    # 3. no template exists
    return None


def create_email_template(
        db: Session,
        *,
        body: EmailTemplateRequest,
        actor: str
) -> EmailTemplate:
    now = _now()

    email_template = EmailTemplate(
        locale=body.locale,
        label=make_multilanguage_label(body.label),
        subject=body.subject,
        preview_text=body.preview_text,
        html=body.html,
        purposes=body.purposes,
        priority=body.priority,
        created_at=now,
        created_by=actor
    )
    db.add(email_template)

    email_template_version = EmailTemplateVersion(
        email_template=email_template,
        locale=body.locale,
        label=make_multilanguage_label(body.label),
        subject=body.subject,
        preview_text=body.preview_text,
        html=body.html,
        purposes=body.purposes,
        priority=body.priority,
        created_at=now,
        created_by=actor
    )
    db.add(email_template_version)

    db.flush()

    return email_template


def update_email_template(
        db: Session,
        template_id: uuid.UUID,
        *,
        body: EmailTemplateRequest,
        actor: str
) -> EmailTemplate:
    now = _now()
    email_template = get_email_template(db, template_id)

    # create new version
    email_template_version = EmailTemplateVersion(
        email_template_id=email_template.id,
        locale=body.locale,
        label=make_multilanguage_label(body.label),
        subject=body.subject,
        preview_text=body.preview_text,
        html=body.html,
        purposes=body.purposes,
        priority=body.priority,
        created_at=now,
        created_by=actor
    )
    db.add(email_template_version)

    # update template
    email_template.locale = body.locale
    email_template.label = make_multilanguage_label(body.label)
    email_template.subject = body.subject
    email_template.preview_text = body.preview_text
    email_template.html = body.html
    email_template.purposes = body.purposes
    email_template.priority = body.priority
    email_template.updated_at = now

    # save changes
    db.flush()

    return email_template


def delete_email_template(
        db: Session,
        template_id: uuid.UUID,
        *,
        actor: str
) -> EmailTemplate:
    now = _now()
    email_template = get_email_template(db, template_id)

    # delete template
    email_template.updated_at = now
    email_template.deleted_at = now
    email_template.deleted_by = actor

    # save changes
    db.flush()

    return email_template


# --------------------------------------------------------------------------- #
# Email template files
# --------------------------------------------------------------------------- #
def get_email_template_file(db: Session, template_file_id: uuid.UUID) -> EmailTemplateFile:
    template_file = db.get(EmailTemplateFile, template_file_id)
    if template_file is None:
        raise NotFoundError("email template file not found")
    return template_file


def create_email_template_file(
        db: Session,
        template_id: uuid.UUID,
        *,
        body: EmailTemplateFileCreateRequest,
        actor: str
) -> EmailTemplateFile:
    email_template = get_email_template(db, template_id)

    # get/save file
    file: File
    if body.file:
        raw = base64.b64decode(body.file)
        file = _resolve_email_template_file(db, raw, created_by=actor)
    elif body.file_id:
        tmp = get_file(db, body.file_id)
        if tmp is None:
            raise NotFoundError(f"file not found: {body.file_id}")
        if tmp.type != "image":
            raise NotFoundError(
                f"file referenced as image is no image: {body.file_id}")
        file = tmp
    else:
        raise NotFoundError(
            "please supply a base64 encoded file or fileId to create the template file")

    # create template file
    email_template_file = EmailTemplateFile(
        email_template=email_template,
        file=file,
        type='image',
        key=body.key,
        created_by=actor
    )
    db.add(email_template_file)
    email_template.updated_at = _now()
    db.flush()

    return email_template_file


def update_email_template_file(
        db: Session,
        template_id: uuid.UUID,
        template_file_id: uuid.UUID,
        *,
        body: EmailTemplateFileUpdateRequest,
        actor: str
) -> EmailTemplateFile:
    email_template = get_email_template(db, template_id)
    email_template_file = get_email_template_file(db, template_file_id)
    if email_template_file.email_template_id != email_template.id:
        raise NotFoundError(
            "file referenced is not connected to the email template")

    email_template_file.key = body.key
    db.flush()

    return email_template_file


def delete_email_template_file(
        db: Session,
        template_id: uuid.UUID,
        template_file_id: uuid.UUID,
        *,
        actor: str
) -> EmailTemplateFile:
    email_template = get_email_template(db, template_id)
    email_template_file = get_email_template_file(db, template_file_id)
    if email_template_file.email_template_id != email_template.id:
        raise NotFoundError(
            "file referenced is not connected to the email template")

    email_template_file.deleted_at = _now()
    email_template_file.deleted_by = actor
    db.flush()

    return email_template_file


# --------------------------------------------------------------------------- #
# Emails
# --------------------------------------------------------------------------- #
def list_emails(
    db: Session, *, limit: int, offset: int
) -> tuple[list[Email], int]:
    total = db.execute(select(func.count()).select_from(
        Email)).scalar_one()
    stmt = (
        select(Email)
        .order_by(Email.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def search_emails(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_params: EmailSearchParams
) -> tuple[list[Email], int]:
    conditions: list[ColumnElement[bool]] = []

    # filters
    filters: list[tuple[InstrumentedAttribute[Any], Sequence[Any] | None]] = [
        (Email.email_sender_id, search_params.email_sender),
        (Email.status, search_params.status),
        (Email.locale, search_params.locale),
    ]
    for column, values in filters:
        if values:
            conditions.append(column.in_(values))

    # special values
    if search_params.email_template:
        conditions.append(
            Email.email_template_version.has(
                EmailTemplateVersion.email_template_id.in_(
                    search_params.email_template)
            )
        )
    if search_params.has_attachments:
        if search_params.has_attachments:
            conditions.append(Email.email_attachments.any())
        else:
            conditions.append(~Email.email_attachments.any())

    # text filters
    if search_params.q and search_params.q.strip():
        term: str = search_params.q.strip()
        # escape LIKE wildcards so user input is matched literally
        escaped: str = (
            term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern: str = f"%{escaped}%"
        conditions.append(
            or_(
                cast(Email.to, String).ilike(pattern, escape="\\"),
                cast(Email.cc, String).ilike(pattern, escape="\\"),
                cast(Email.bcc, String).ilike(pattern, escape="\\"),
                Email.sender.ilike(pattern, escape="\\"),
                Email.subject.ilike(pattern, escape="\\"),
                Email.body.ilike(pattern, escape="\\"),
            )
        )

    # count total
    count_stmt: Select[tuple[int]] = (
        select(func.count()).select_from(Email).where(*conditions)
    )
    total: int = db.execute(count_stmt).scalar_one()

    # build statement
    stmt = (
        select(Email)
        .where(*conditions)
        .order_by(Email.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_email(db: Session, template_id: uuid.UUID) -> Email:
    email = db.get(Email, template_id)
    if email is None:
        raise NotFoundError("email not found")
    return email
