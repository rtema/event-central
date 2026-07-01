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

from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

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
from src.files.models import File


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

    # Relationships
    document_template_files: Mapped[list[DocumentTemplateFile]] = relationship(
        back_populates="document_template"
    )
    invoices: Mapped[list["Invoice"]] = relationship(  # noqa: F821, UP037 # type: ignore
        back_populates="document_template", lazy="selectin", order_by="Invoice.invoice_number"
    )
    public_document_templates: Mapped[list[PublicDocumentTemplate]] = relationship(
        back_populates="document_template", lazy="selectin", order_by="PublicDocumentTemplate.id"
    )


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

    # Relationships
    document_template: Mapped[DocumentTemplate] = relationship(
        back_populates="public_document_templates", order_by="PublicDocumentTemplate.id")


class DocumentTemplateFile(Base, CreatedAtMixin, CreatedByMixin):
    __tablename__ = "document_template_files"

    id: Mapped[uuid.UUID] = uuid_pk()

    document_template_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType,
        ForeignKey("document_templates.id", ondelete="SET NULL"),
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
    # the templates are jinja templates that will be rendered using weasyprint
    # files can be referenced by {{ image.key }} and fonts by {{ font.key }}
    # Therefore this key only needs to unique within a single template
    key: Mapped[str] = mapped_column(String(2048), nullable=True, default=None)

    # Name of the font
    font_name: Mapped[str] = mapped_column(
        String(256), nullable=True, default=None)

    # Name of the font
    font_weight: Mapped[int] = mapped_column(
        Integer, nullable=True, default=None)

    # Relationships
    document_template: Mapped[DocumentTemplate] = relationship(
        back_populates="document_template_files")
    file: Mapped[File] = relationship()
