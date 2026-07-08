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

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import AppError, ConflictError, NotFoundError
from src.core.schemas import make_multilanguage_label
from src.document_templates.models import (
    DocumentTemplate,
    DocumentTemplateFile,
    PublicDocumentTemplate,
)
from src.document_templates.schemas import (
    PublicDocumentTemplateCreateRequest,
    PublicDocumentTemplateUpdateRequest,
)
from src.files.models import File
from src.files.service import create_file, get_file, get_files_by_hash
from src.invoices.schemas import InvoiceTemplate

# Public ids (slugs): lower-case letters, digits, '-' and '_'.
_SLUG_REGEX = re.compile(r"^[a-z0-9_-]{3,128}$")

ReferencedFile = tuple[str, str, str | None, int | None, File]


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _validate_slug(slug: str) -> None:
    if not _SLUG_REGEX.match(slug):
        raise AppError(
            "id must contain only lower-case letters, numbers, '-' and '_'",
            error="invalid_id",
        )


def _generate_font_key(name: str, weight: int) -> str:
    return f"{re.sub(r'[^a-z]', '', name.lower())}-{weight}"

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
    db: Session,
    *,
    public_document_template_id: str,
    body: PublicDocumentTemplateCreateRequest,
    actor: str
) -> PublicDocumentTemplate:
    _validate_slug(public_document_template_id)
    if db.get(PublicDocumentTemplate, public_document_template_id) is not None:
        raise ConflictError(
            f"public document template {public_document_template_id!r} already exists")

    public_document_template = PublicDocumentTemplate(
        id=public_document_template_id,
        locale=body.locale,
        label={},
    )
    db.add(public_document_template)
    db.flush()

    # create the file
    public_document_template = update_public_document_template(
        db,
        public_document_template_id,
        body=body,
        actor=actor
    )
    return public_document_template


def update_public_document_template(
    db: Session,
    public_document_template_id: str,
    *,
    body: PublicDocumentTemplateUpdateRequest | PublicDocumentTemplateCreateRequest,
    actor: str
) -> PublicDocumentTemplate:
    public_document_template = get_public_document_template(
        db, public_document_template_id)

    # get / deduplicate files
    seen_files: dict[str, File] = {}
    seen_keys: dict[tuple[str, str, int | None], uuid.UUID] = {}
    referenced_files: list[ReferencedFile] = []

    for image in body.images or []:
        file: File
        if image.file:
            raw = base64.b64decode(image.file)
            file = _resolve_file(
                db, raw, created_by=actor, seen=seen_files)
        elif image.file_id:
            tmp = get_file(db, image.file_id)
            if tmp is None:
                raise NotFoundError(f"file not found: {image.file_id}")
            if tmp.type != "image":
                raise NotFoundError(
                    f"file referenced as image is no image: {image.file_id}")
            file = tmp
        else:
            raise NotFoundError(f"file not found: {image.file_id}")

        # add to list of files
        _add_to_referenced_files(
            referenced_files, seen_keys, "image", image.key, None, None, file)

    for font in body.fonts or []:
        file: File
        if font.file:
            raw = base64.b64decode(font.file)
            file = _resolve_file(
                db, raw, created_by=actor, seen=seen_files)
        elif font.file_id:
            tmp = get_file(db, font.file_id)
            if tmp is None:
                raise NotFoundError(f"file not found: {font.file_id}")
            if tmp.type != "font":
                raise NotFoundError(
                    f"file referenced as font is no font: {font.file_id}")
            file = tmp
        else:
            raise NotFoundError(f"file not found: {font.file_id}")

        # add to list of files
        _add_to_referenced_files(
            referenced_files,
            seen_keys,
            "font",
            _generate_font_key(font.name, font.weight),
            font.name,
            font.weight,
            file
        )

    # create a new document_template
    document_template = DocumentTemplate(
        public_document_template_id=public_document_template_id,
        html=body.html,
        css=body.css,
        created_by=actor,
    )
    db.add(document_template)
    db.flush()  # need the id for the file rows

    # attach all files
    for type_, key, font_name, font_weight, file in referenced_files:
        db.add(
            DocumentTemplateFile(
                document_template_id=document_template.id,
                file_id=file.id,
                type=type_,
                key=key,
                font_name=font_name,
                font_weight=font_weight,
                created_by=actor,
            )
        )

    # point the new id to the public template
    public_document_template.document_template_id = document_template.id

    # set label + locale
    public_document_template.locale = body.locale
    public_document_template.label = make_multilanguage_label(body.label)

    # set updated at
    public_document_template.updated_at = _now()
    db.flush()

    # return updated template
    return public_document_template


def resolve_document_template(
    db: Session,
    invoice_template: InvoiceTemplate,
    locale: str,
    actor_sub: str | None,

) -> DocumentTemplate:

    # a public template should be used
    if invoice_template.template_name is not None:
        # get the template of the database
        public_template = get_public_document_template(
            db, invoice_template.template_name)
        return public_template.document_template

    # go over all files
    seen_files: dict[str, File] = {}
    seen_keys: dict[tuple[str, str, int | None], uuid.UUID] = {}
    referenced_files: list[ReferencedFile] = []

    for image in invoice_template.images or []:
        raw = base64.b64decode(image.file)
        file = _resolve_file(
            db, raw, created_by=actor_sub or "system", seen=seen_files)
        _add_to_referenced_files(
            referenced_files, seen_keys, "image", image.key, None, None, file)

    for font in invoice_template.fonts or []:
        raw = base64.b64decode(font.file)
        file = _resolve_file(
            db, raw, created_by=actor_sub or "system", seen=seen_files)
        _add_to_referenced_files(
            referenced_files,
            seen_keys,
            "font",
            _generate_font_key(font.name, font.weight),
            font.name,
            font.weight,
            file
        )

    # Template-level deduplication: same html+css and identical file set
    existing = _find_existing_document_template(
        db, invoice_template.html, invoice_template.css, referenced_files
    )
    if existing is not None:
        return existing

    # create new template
    document_template = DocumentTemplate(
        locale=locale,
        html=invoice_template.html,
        css=invoice_template.css,
        public_document_template_id=None,
        created_by=actor_sub,
    )
    db.add(document_template)
    db.flush()  # need the id for the file rows

    # attach all files
    for type_, key, font_name, font_weight, file in referenced_files:
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

    # return the created document template
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


def _add_to_referenced_files(
    referenced_files: list[ReferencedFile],
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
    images always pass weight=None, so they still deduplicate on (type, key)."""
    ns_key = (type_, key, font_weight)
    if ns_key in key_seen:
        if key_seen[ns_key] != file.id:
            raise ValueError(
                f"duplicate {type_} key {key!r} (weight {font_weight!r}) "
                "with conflicting content"
            )
        return
    key_seen[ns_key] = file.id
    referenced_files.append((type_, key, font_name, font_weight, file))


def _find_existing_document_template(
    db: Session, html: str | None, css: str | None, specs: list[ReferencedFile],
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
