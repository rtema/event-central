from __future__ import annotations

import hashlib
import logging
import os
import re
import uuid
from dataclasses import dataclass
from io import BytesIO

import magic
from PIL import Image, ImageFile
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.config import settings
from src.core.errors import AppError
from src.files.clamav_client import clamav_validate_bytes
from src.files.images import generate_image_preview, open_image_safely
from src.files.models import File
from src.storage.s3 import get_storage

logger = logging.getLogger(__name__)

# We never trust client-declared content types. The bytes are sniffed and only
# an explicit allow-list is accepted; the declared extension must agree with the
# sniffed mime. Tune this table for your product.
_ALLOWED: dict[str, set[str]] = {
    # Images
    "image/jpeg": {"jpg", "jpeg"},
    "image/png": {"png"},
    "image/gif": {"gif"},
    "image/webp": {"webp"},

    # Documents
    "application/pdf": {"pdf"},
    "text/plain": {"txt", "csv"},
    "text/csv": {"csv", "txt"},

    # OOXML files are zip containers; libmagic usually reports application/zip.
    "application/zip": {"zip", "docx", "xlsx", "pptx"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {"docx"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {"xlsx"},

    # Fonts
    # TODO
    "font/sfnt": {"ttf"}
}
_IMAGE_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp"}

# Be strict: Pillow must not silently accept truncated payloads, and we bound
# the pixel count to defend against decompression bombs.
ImageFile.LOAD_TRUNCATED_IMAGES = False
Image.MAX_IMAGE_PIXELS = settings.api_files_max_image_pixels

# Hashing


def generate_file_data_hash(data: BytesIO) -> str:
    """SHA-256 hex digest of the file contents (streamed, position restored)."""
    pos = data.tell()
    data.seek(0)
    h = hashlib.sha256()
    for chunk in iter(lambda: data.read(1024 * 1024), b""):
        h.update(chunk)
    data.seek(pos)
    return h.hexdigest()


# Content sniffing / validation
_EXT_RE = re.compile(r"^[a-z0-9]{1,16}$")
_BASE_PATH_RE = re.compile(r"^[A-Za-z0-9._/\-]{1,512}$")


def _safe_extension(filename: str | None) -> str | None:
    """Extract a lowercase, alnum-only extension from an untrusted filename."""
    if not filename:
        return None
    name = os.path.basename(filename.replace("\\", "/")).replace("\x00", "")
    _, dot, ext = name.rpartition(".")
    if not dot:
        return None
    ext = ext.lower()
    return ext if _EXT_RE.match(ext) else None


def _sniff_mime(raw: bytes, *, image: Image.Image | None) -> str | None:
    try:
        sniffed = magic.from_buffer(raw, mime=True)
    except Exception:
        logger.warning("libmagic sniff failed", exc_info=True)
        sniffed = None
    if sniffed:
        return sniffed
    # Fallback: trust the Pillow-decoded format only.
    if image is not None:
        return {
            "JPEG": "image/jpeg",
            "PNG": "image/png",
            "GIF": "image/gif",
            "WEBP": "image/webp",
        }.get((image.format or "").upper())
    return None


@dataclass
class _Inspection:
    mime: str
    extension: str
    type: str
    width: int | None = None
    height: int | None = None
    image: Image.Image | None = None


def inspect_and_validate_file(
        raw_bytes: bytes,
        *,
        filename: str | None = None,
        max_file_size: int = settings.api_files_max_size
) -> _Inspection:
    """Validate an untrusted payload and return what we are willing to store.

    Order matters: bound the size, scan for malware, then decode/sniff. Anything
    suspicious raises ``FileRejected`` and nothing is persisted by the caller.
    """
    # Size bounds.
    if not raw_bytes:
        raise AppError(
            "Empty file",
            http_status=400
        )

    if len(raw_bytes) > max_file_size:
        raise AppError(
            "File exceeds the maximum allowed size",
            http_status=400
        )

    # Malware scan, throws AppError, when malware is found
    # Fails open, if clamav is not configured/reachable
    clamav_validate_bytes(raw_bytes)

    # Attempt to read an image, if not an image ignore
    image = open_image_safely(raw_bytes)

    # Determine the real content type from the bytes
    mime = _sniff_mime(raw_bytes, image=image)
    if mime is None or mime not in _ALLOWED:
        raise AppError(
            f"Unsupported or undetectable content type: {mime!r}",
            http_status=400
        )

    # Reconcile the declared extension with the sniffed type.
    allowed_extensions = _ALLOWED[mime]
    declared_ext = _safe_extension(filename)
    if declared_ext and declared_ext not in allowed_extensions:
        raise AppError(
            f"Extension '.{declared_ext}' does not match detected type {mime}",
            http_status=400
        )
    extension = declared_ext or sorted(allowed_extensions)[0]

    # Image / polyglot consistency checks.
    width = height = None
    if mime in _IMAGE_MIMES:
        if image is None:
            raise AppError(
                "Declared image type but no valid image data",
                http_status=400
            )
        width, height = image.size
        if width <= 0 or height <= 0:
            raise AppError(
                "Image has invalid dimensions",
                http_status=400
            )
    elif image is not None:
        # Decodes as an image yet sniffs as something else => polyglot. Reject.
        raise AppError(
            "Ambiguous file: decodes as image but typed otherwise",
            http_status=400
        )

    return _Inspection(
        mime=mime,
        extension=extension,
        type=mime.split("/", 1)[0],  # image / application / text ...
        width=width,
        height=height,
        image=image,
    )


# Storage key helpers
def storage_key_for_file(file: File) -> str:
    """Deterministic object key for a stored variant of ``file``."""
    return f"files/{file.base_path}/{file.id}/original.{file.extension}"


def create_file(
    db: Session,
    data: BytesIO,
    label: dict[str, str],
    base_path: str,
    created_by: str,
        *,
    filename: str | None = None,
    published: bool = False,
    meta: dict[str, str] | None = None,
) -> File:
    """Validate, scan and persist an uploaded file.

    Treats the payload as hostile: size-bounded, AV-scanned, content-sniffed and
    cross-checked against an allow-list before anything is written to storage.
    For images a 128px preview is generated.

    Raises ``AppError`` for a bad/forbidden file, or ``AppError`` if
    the scanner is unreachable while failing closed (nothing is persisted).
    """

    # Validate base path
    if not re.match("^[a-z0-9_-]{2,256}$", base_path):
        raise AppError(
            "Invalid base path",
            http_status=500
        )

    # Read raw bytes
    raw_bytes: bytes
    if isinstance(data, (bytes, bytearray, memoryview)):
        raw_bytes = bytes(data)
    else:
        # data is now narrowed to BytesIO -> tell/seek/read are fully typed
        pos = data.tell()
        data.seek(0)
        raw_bytes = data.read()
        data.seek(pos)

    #
    inspection = inspect_and_validate_file(raw_bytes, filename=filename)

    preview = None
    if inspection.image is not None:
        preview = generate_image_preview(inspection.image)

    # generate ID
    id = uuid.uuid4()
    file = File(
        id=id,
        label=label or {},
        extension=inspection.extension,
        type=inspection.type,
        mime=inspection.mime,
        published=published,
        access_key=f'{id}.{inspection.extension}',
        base_path=base_path,
        size=len(raw_bytes),
        hash=hashlib.sha256(raw_bytes).hexdigest(),
        preview=preview,
        width=inspection.width,
        height=inspection.height,
        meta=dict(meta or {}),
        created_by=created_by
    )

    db.add(file)

    # surface unique-constraint violations before we touch storage
    db.flush()

    storage = get_storage()
    storage.put(
        storage_key_for_file(file),
        BytesIO(raw_bytes).read(),
        content_type=inspection.mime,
    )

    return file


def list_files(
    db: Session,
    *,
    limit: int,
    offset: int,
    include_deleted: bool = False,
) -> tuple[list[File], int]:
    """Return a page of files (newest first) and the total count."""
    base = select(File)
    count_stmt = select(func.count()).select_from(File)
    if not include_deleted:
        base = base.where(File.deleted_at.is_(None))
        count_stmt = count_stmt.where(File.deleted_at.is_(None))

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(File.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def get_files_by_hash(
    db: Session,
    hash: str,
    *,
    include_deleted: bool = False,
) -> list[File]:
    """All files matching a content hash (useful for deduplicate before storing)."""
    stmt = select(File).where(File.hash == hash)
    if not include_deleted:
        stmt = stmt.where(File.deleted_at.is_(None))
    return list(db.execute(stmt).scalars().all())


def get_file(db: Session, file_id: uuid.UUID) -> File | None:
    """Fetch a non-deleted file by id."""
    stmt = select(File).where(File.id == file_id, File.deleted_at.is_(None))
    return db.execute(stmt).scalar_one_or_none()


def get_file_by_access_key(
    db: Session,
    access_key: str,
    *,
    include_deleted: bool = False,
) -> File | None:
    """Fetch a file by its URL access key."""
    stmt = select(File).where(File.access_key == access_key)
    if not include_deleted:
        stmt = stmt.where(File.deleted_at.is_(None))
    return db.execute(stmt).scalar_one_or_none()


def get_file_data(
    db: Session,
    file_id: uuid.UUID,
) -> bytes | None:
    """Return the stored bytes for an original file variant"""
    file = get_file(db, file_id)
    if file is None:
        return None
    try:
        return get_storage().get(storage_key_for_file(file))
    except Exception:
        logger.warning("storage fetch failed for %s", file_id, exc_info=True)
        return None
