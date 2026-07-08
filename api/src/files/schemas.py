"""Order-domain API schemas (camelCase JSON, tag: Orders)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Literal

from pydantic import BeforeValidator, Field

from src.core.schemas import (
    CamelModel,
    CommaSeparatedListStr,
    MultiLanguageLabel,
    Pagination,
    split_comma_separated_list,
)

FileExtension = Literal["png", "jpg", "ttf"]
FileType = Literal["image", "font"]


class FileOut(CamelModel):
    id: uuid.UUID
    label: MultiLanguageLabel
    extension: str
    # extension: FileExtension
    type: FileType
    mime: str
    published: bool
    access_key: str
    base_path: str
    size: int
    hash: str
    preview: str | None = None
    height: int | None = None
    width: int | None = None
    meta: dict[str, str]
    created_at: dt.datetime
    created_by: str
    deleted_at: dt.datetime | None = None
    deleted_by: str | None = None


class FileResponse(CamelModel):
    data: FileOut


class FilesListResponse(CamelModel):
    data: list[FileOut]
    pagination: Pagination


class FileSearchParams(CamelModel):
    # model_config = {"populate_by_name": True}

    q: str | None = Field(
        default=None, description="Generic free-text search term")

    extension: Annotated[list[FileExtension] | None,
                         BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated extensions, e.g. png,jpg,ttf"
    )
    type: Annotated[list[FileType] | None, BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated types, e.g. image,font"
    )
    published: Annotated[list[bool] | None, BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated booleans, e.g. true,false"
    )
    base_path: CommaSeparatedListStr = Field(
        default=None,
        description="Comma-separated base paths",
    )


class FilesSearchResponse(CamelModel):
    data: list[FileOut]
    pagination: Pagination
    search: FileSearchParams


class FileLinkRequest(CamelModel):
    expires_in: int | None = Field(default=None, le=31_536_000)


class FileLinkResponse(CamelModel):
    url: str
    expires_at: dt.datetime
