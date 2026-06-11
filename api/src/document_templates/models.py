"""Document-template models (tag: Document Templates).

Two tables:

* ``document_templates``        — a concrete WeasyPrint/Jinja template
                                  (html/css + embedded fonts and images).
* ``public_document_templates`` — a stable public slug that points at the
                                  ``document_templates`` row currently in use,
                                  so invoices can reference a template by a
                                  human-friendly id rather than a UUID.

The two reference each other (a private template knows its public slug; a
public slug knows its current private template). To avoid a circular foreign
key, only the public→private direction is a real FK; the private→public link is
stored as a plain slug column and validated in the service layer.
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    DeletedAtMixin,
    DeletedByMixin,
    UpdatedAtMixin,
    UUIDType,
    uuid_pk,
)


class DocumentTemplate(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "document_templates"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Logical reference to public_document_templates.id (a slug). Not a DB-level
    # foreign key, to avoid a cycle with public_document_templates; integrity is
    # maintained by the service layer.
    public_document_template_id: Mapped[str | None] = mapped_column(
        String(128), nullable=True, index=True
    )

    html: Mapped[str | None] = mapped_column(Text, nullable=True)
    css: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Arrays of {"name", "file"} (fonts) / {"name", "file"|"link"} (images).
    fonts: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, nullable=False, default=list)
    images: Mapped[list[dict[str, str]]] = mapped_column(
        JSONB, nullable=False, default=list)


class PublicDocumentTemplate(
    Base, CreatedAtMixin, UpdatedAtMixin, DeletedAtMixin, DeletedByMixin
):
    __tablename__ = "public_document_templates"

    # Caller-supplied slug, e.g. "invoice-default".
    id: Mapped[str] = mapped_column(String(128), primary_key=True)

    document_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("document_templates.id", ondelete="SET NULL"),
        nullable=True,
    )

    # MultiLanguageLabel
    label: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)
