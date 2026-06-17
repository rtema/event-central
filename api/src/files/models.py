from __future__ import annotations

import uuid

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    DeletedAtMixin,
    DeletedByMixin,
    uuid_pk,
)


class File(Base, CreatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    """A File that can be referenced by other tables

    Files are stored at the following path
    /files/{base_path}/{file_id}/original.{extension}

    Images: Processed versions for web are stored like follows
    /files/{base_path}/{file_id}/processed-w{processed_width}.{processed_extension}
    
    """

    __tablename__ = "files"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Multi language label to show in the management area
    label: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)

    # File extension for retrieving the file
    extension: Mapped[str] = mapped_column(String(16), nullable=False)

    # Type of file saved
    type: Mapped[str] = mapped_column(String(256), nullable=False)

    # Mime type of file saved
    mime: Mapped[str] = mapped_column(String(256), nullable=False)

    # Should this file be publicly accessible?
    published: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False)

    # Part of the url, that will be matched when displaying the file
    access_key: Mapped[str] = mapped_column(
        String(2048), nullable=False, unique=True)
    
    # Base path of the storage location
    base_path: Mapped[str] = mapped_column(
        String(2048), nullable=False)

    # Size in bytes
    size: Mapped[int] = mapped_column(Integer, nullable=False)

    # Hash of the file contents
    hash: Mapped[str] = mapped_column(String(64), nullable=False)

    # Base64 encoded string of a preview image with a maximum of 128x128px
    preview: Mapped[str | None] = mapped_column(
        Text, nullable=True, default=None)

    # Height of the image (if applicable)
    height: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None)

    # Width of the image (if applicable)
    width: Mapped[int | None] = mapped_column(
        Integer, nullable=True, default=None)

    # Additional metadata
    meta: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)
