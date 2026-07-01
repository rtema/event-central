"""Document-template business logic (tag: Document Templates).

Creating a public template provisions a concrete ``document_templates`` row and
a ``public_document_templates`` slug that points at it. Updating a public
template is versioned: it provisions a *new* concrete template and repoints the
slug, so older invoices keep referencing the exact template they were rendered
with.
"""

from __future__ import annotations

import base64
import datetime as dt
import hashlib
import re
import uuid
from io import BytesIO
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import AppError, ConflictError, NotFoundError
from src.document_templates.models import (
    DocumentTemplate,
    DocumentTemplateFile,
    PublicDocumentTemplate,
)
from src.files.models import File
from src.files.service import create_file, get_files_by_hash
from src.invoices.schemas import InvoiceTemplate

# Public ids (slugs): lower-case letters, digits, '-' and '_'.
_SLUG_REGEX = re.compile(r"^[a-z0-9_-]{3,128}$")

Spec = tuple[str, str, str | None, int | None, File]


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
        created_by=actor,
    )
    db.add(concrete)
    db.flush()

    public.document_template_id = concrete.id
    public.updated_at = _now()
    db.flush()
    return public


def resolve_document_template(
    db: Session, invoice_template: InvoiceTemplate, actor_sub: str | None
) -> DocumentTemplate:

    # a public template should be used
    if invoice_template.template_name is not None:
        # get the template of the database
        public_template = get_public_document_template(
            db, invoice_template.template_name)
        return public_template.document_template

    # check if the template already exists

    # Template does not exist

    # create all necessary files

    # create document template

    seen: dict[str, File] = {}
    key_seen: dict[tuple[str, str, int | None], uuid.UUID] = {}
    specs: list[Spec] = []

    for image in invoice_template.images or []:
        raw = base64.b64decode(image.file) if image.file is not None\
            else _fetch_link(image.link)  # type: ignore validator guarantees exactly one of file/link is set

        file = _resolve_file(
            db, raw, created_by=actor_sub or "system", seen=seen)
        _add_spec(specs, key_seen, "image", image.key, None, None, file)

    for font in invoice_template.fonts or []:
        raw = base64.b64decode(font.file)
        file = _resolve_file(
            db, raw, created_by=actor_sub or "system", seen=seen)
        # fonts are referenced in the template by their name
        _add_spec(specs, key_seen, "font", font.name,
                  font.name, font.weight, file)

    # ---- Template-level dedup: same html+css and identical file set ------- #
    existing = _find_existing_document_template(
        db, invoice_template.html, invoice_template.css, specs
    )
    if existing is not None:
        return existing

    document_template = DocumentTemplate(
        html=invoice_template.html,
        css=invoice_template.css,
        public_document_template_id=None,
        created_by=actor_sub,
    )
    db.add(document_template)
    db.flush()  # need the id for the file rows

    for type_, key, font_name, font_weight, file in specs:
        db.add(
            DocumentTemplateFile(
                document_template_id=document_template.id,
                file_id=file.id,
                type=type_,
                key=key,
                font_name=font_name,
                font_weight=font_weight,
                created_by=actor_sub or "system",
            )
        )
    db.flush()
    return document_template


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _resolve_file(
    db: Session, raw_bytes: bytes, *, created_by: str, seen: dict[str, File],
) -> File:
    """Return a canonical File for these bytes, reusing an existing row when the
    content hash already exists. New content goes through create_file so it is
    size-bounded, AV-scanned, sniffed and stored exactly like any upload."""
    digest = hashlib.sha256(raw_bytes).hexdigest()
    if digest in seen:
        return seen[digest]

    matches = get_files_by_hash(db, digest)
    if matches:
        file = matches[0]
    else:
        file = create_file(
            db,
            BytesIO(raw_bytes),
            label={},
            base_path="document-template-files",
            created_by=created_by,
            # filename omitted on purpose: extension is derived from the sniffed
            # mime, so we don't risk a spurious extension/mime mismatch.
        )
    seen[digest] = file
    return file


def _add_spec(
    specs: list[Spec],
    key_seen: dict[tuple[str, str, int | None], uuid.UUID],
    type_: str,
    key: str,
    font_name: str | None,
    font_weight: int | None,
    file: File,
) -> None:
    """Collect a (type, key, weight) -> file mapping, collapsing exact
    duplicates and rejecting the same (key, weight) pointing at conflicting
    content within one request. Fonts may reuse a key across different weights;
    images always pass weight=None, so they still dedup on (type, key)."""
    ns_key = (type_, key, font_weight)
    if ns_key in key_seen:
        if key_seen[ns_key] != file.id:
            raise ValueError(
                f"duplicate {type_} key {key!r} (weight {font_weight!r}) "
                "with conflicting content"
            )
        return
    key_seen[ns_key] = file.id
    specs.append((type_, key, font_name, font_weight, file))


def _find_existing_document_template(
    db: Session, html: str | None, css: str | None, specs: list[Spec],
) -> DocumentTemplate | None:
    desired = {
        (type_, key, font_name, font_weight, file.id)
        for type_, key, font_name, font_weight, file in specs
    }
    stmt = select(DocumentTemplate).where(
        DocumentTemplate.html == html,
        DocumentTemplate.css == css,
        DocumentTemplate.public_document_template_id.is_(None),
    )
    for candidate in db.scalars(stmt):
        actual = {
            (f.type, f.key, f.font_name, f.font_weight, f.file_id)
            for f in candidate.document_template_files
        }
        if actual == desired:
            return candidate
    return None


def _fetch_link(url: str) -> bytes:
    raise ValueError("link is currently not supported for images")
    # # SEE NOTE BELOW — this is server-side fetching of a caller-supplied URL.
    # if not url.lower().startswith("https://"):
    #     raise ValueError("image link must be https")
    # resp = httpx.get(url, timeout=10.0, follow_redirects=False)
    # resp.raise_for_status()
    # return resp.content
