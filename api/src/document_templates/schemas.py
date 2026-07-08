"""Document-template API schemas (camelCase JSON, tag: Document Templates)."""

from __future__ import annotations

import datetime as dt
import uuid

from src.core.schemas import Base64Str, CamelModel, MultiLanguageLabel, Pagination


class DocumentTemplateFont(CamelModel):
    name: str
    weight: int
    file: Base64Str


class DocumentTemplateFontCreateRequest(CamelModel):
    name: str
    weight: int
    file_id: uuid.UUID | None = None
    file: Base64Str | None = None


class DocumentTemplateImage(CamelModel):
    key: str
    file: Base64Str


class DocumentTemplateImageCreateRequest(CamelModel):
    key: str
    file_id: uuid.UUID | None = None
    file: Base64Str | None = None


class DocumentTemplateFileOut(CamelModel):
    id: uuid.UUID
    document_template_id: uuid.UUID
    file_id: uuid.UUID
    type: str
    key: str | None = None
    font_name: str | None = None
    font_weight: int | None = None

# --------------------------------------------------------------------------- #
# Private templates
# --------------------------------------------------------------------------- #


class DocumentTemplateOut(CamelModel):
    id: uuid.UUID
    public_document_template_id: str | None = None
    html: str | None = None
    css: str | None = None
    fonts: list[DocumentTemplateFont] = []
    images: list[DocumentTemplateImage] = []
    created_by: str | None = None
    created_at: dt.datetime


class DocumentTemplateResponse(CamelModel):
    data: DocumentTemplateOut


class DocumentTemplateFilesResponse(CamelModel):
    data: list[DocumentTemplateFileOut]


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


class PublicDocumentTemplateUpdateRequest(CamelModel):
    locale: str
    label: dict[str, str]
    html: str
    css: str
    fonts: list[DocumentTemplateFontCreateRequest]
    images: list[DocumentTemplateImageCreateRequest]


class PublicDocumentTemplateCreateRequest(CamelModel):
    id: str
    locale: str
    label: dict[str, str]
    html: str
    css: str
    fonts: list[DocumentTemplateFontCreateRequest]
    images: list[DocumentTemplateImageCreateRequest]
