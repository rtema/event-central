"""Document-template business logic (tag: Document Templates).

Creating a public template provisions a concrete ``document_templates`` row and
a ``public_document_templates`` slug that points at it. Updating a public
template is versioned: it provisions a *new* concrete template and repoints the
slug, so older invoices keep referencing the exact template they were rendered
with.
"""

from __future__ import annotations

import datetime as dt
import re
import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import AppError, ConflictError, NotFoundError
from src.document_templates.models import DocumentTemplate, PublicDocumentTemplate

# Public ids (slugs): lower-case letters, digits, '-' and '_'.
_SLUG_REGEX = re.compile(r"^[a-z0-9_-]{3,128}$")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _validate_slug(slug: str) -> None:
    if not _SLUG_REGEX.match(slug):
        raise AppError(
            "id must contain only lower-case letters, numbers, '-' and '_'",
            error="invalid_id",
        )


# --------------------------------------------------------------------------- #
# Private templates (read-only via the API)
# --------------------------------------------------------------------------- #
def list_document_templates(
    db: Session, *, limit: int, offset: int
) -> tuple[list[DocumentTemplate], int]:
    total = db.execute(select(func.count()).select_from(
        DocumentTemplate)).scalar_one()
    stmt = (
        select(DocumentTemplate)
        .order_by(DocumentTemplate.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_document_template(db: Session, template_id: uuid.UUID) -> DocumentTemplate:
    template = db.get(DocumentTemplate, template_id)
    if template is None:
        raise NotFoundError("document template not found")
    return template


# --------------------------------------------------------------------------- #
# Public templates
# --------------------------------------------------------------------------- #
def list_public_document_templates(
    db: Session, *, limit: int, offset: int, include_deleted: bool = False
) -> tuple[list[PublicDocumentTemplate], int]:
    base = select(PublicDocumentTemplate)
    count_stmt = select(func.count()).select_from(PublicDocumentTemplate)
    if not include_deleted:
        base = base.where(PublicDocumentTemplate.deleted_at.is_(None))
        count_stmt = count_stmt.where(
            PublicDocumentTemplate.deleted_at.is_(None))

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(PublicDocumentTemplate.created_at.desc()).limit(
        limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def get_public_document_template(db: Session, public_id: str) -> PublicDocumentTemplate:
    template = db.get(PublicDocumentTemplate, public_id)
    if template is None:
        raise NotFoundError("public document template not found")
    return template


def create_public_document_template(
    db: Session, *, public_id: str, body: dict[str, Any], actor: str | None
) -> PublicDocumentTemplate:
    _validate_slug(public_id)
    if db.get(PublicDocumentTemplate, public_id) is not None:
        raise ConflictError(
            f"public document template {public_id!r} already exists")

    concrete = DocumentTemplate(
        public_document_template_id=public_id,
        html=body.get("html"),
        css=body.get("css"),
        fonts=body.get("fonts") or [],
        images=body.get("images") or [],
        created_by=actor,
    )
    db.add(concrete)
    db.flush()

    public = PublicDocumentTemplate(
        id=public_id,
        document_template_id=concrete.id,
        label={},
    )
    db.add(public)
    db.flush()
    return public


def update_public_document_template(
    db: Session, public_id: str, *, body: dict[str, Any], actor: str | None
) -> PublicDocumentTemplate:
    public = get_public_document_template(db, public_id)

    # Versioned update: provision a new concrete template and repoint the slug.
    concrete = DocumentTemplate(
        public_document_template_id=public_id,
        html=body.get("html"),
        css=body.get("css"),
        fonts=body.get("fonts") or [],
        images=body.get("images") or [],
        created_by=actor,
    )
    db.add(concrete)
    db.flush()

    public.document_template_id = concrete.id
    public.updated_at = _now()
    db.flush()
    return public
