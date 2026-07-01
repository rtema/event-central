"""Document-template API schemas (camelCase JSON, tag: Document Templates)."""

from __future__ import annotations

import datetime as dt
import uuid

from src.core.schemas import Base64Str, CamelModel, MultiLanguageLabel, Pagination


class DocumentFont(CamelModel):
    name: str | None = None
    file: Base64Str | None = None  # base64


class DocumentImage(CamelModel):
    name: str | None = None
    file: Base64Str | None = None  # base64
    link: str | None = None  # https only


# --------------------------------------------------------------------------- #
# Private templates
# --------------------------------------------------------------------------- #
class DocumentTemplateOut(CamelModel):
    id: uuid.UUID
    public_document_template_id: str | None = None
    html: str | None = None
    css: str | None = None
    fonts: list[DocumentFont] = []
    images: list[DocumentImage] = []
    created_by: str | None = None
    created_at: dt.datetime


class DocumentTemplateResponse(CamelModel):
    data: DocumentTemplateOut


class DocumentTemplatesListResponse(CamelModel):
    data: list[DocumentTemplateOut]
    pagination: Pagination


# --------------------------------------------------------------------------- #
# Public templates
# --------------------------------------------------------------------------- #
class PublicDocumentTemplateOut(CamelModel):
    id: str
    document_template_id: uuid.UUID | None = None
    label: MultiLanguageLabel | None = None
    created_at: dt.datetime
    updated_at: dt.datetime
    deleted_at: dt.datetime | None = None


class PublicDocumentTemplateResponse(CamelModel):
    data: PublicDocumentTemplateOut


class PublicDocumentTemplatesListResponse(CamelModel):
    data: list[PublicDocumentTemplateOut]
    pagination: Pagination


class PublicDocumentTemplateCreateRequest(CamelModel):
    id: str
    html: str | None = None
    css: str | None = None
    fonts: list[DocumentFont] | None = None
    images: list[DocumentImage] | None = None


class PublicDocumentTemplateUpdateRequest(CamelModel):
    html: str | None = None
    css: str | None = None
    fonts: list[DocumentFont] | None = None
    images: list[DocumentImage] | None = None
