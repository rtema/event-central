"""File download endpoints (/api/v1/files, tags: Files, Invoicing).

The invoice/export routes are authorized by a signed token in the query string
(not the OAuth bearer), so they carry no scope dependency. The token binds the
exact ``<resource>`` (``invoices/{id}/{file}`` or ``exports/{job}/{file}``) and
an expiry; an absent/forged/expired token yields a friendly 401 HTML page rather
than leaking object bytes.

The ``/public`` and ``/private`` routes serve managed ``File`` rows by their
``access_key``:

* ``/public/{access_key}``  — only ``published`` files, no token required.
* ``/private/{access_key}`` — requires a signed token bound to the access key.

To avoid leaking which keys exist, every authorization/lookup failure returns
the same 401 page regardless of the underlying reason.
"""

from __future__ import annotations

import re
import uuid
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from src.core.deps import get_db
from src.core.security import verify_download_token
from src.files.models import File
from src.files.service import get_file_by_access_key, storage_key_for_file
from src.invoices.exports import content_type_for
from src.invoices.service import get_invoice
from src.jobs.models import Job

router = APIRouter(prefix="/api/v1/files", tags=["Files"])

# --------------------------------------------------------------------------- #
# Localized error/status pages, read from disk relative to this module:        #
#   <this dir>/error_pages/<kind>-<locale>.html   (kind: "loading"|"expired")  #
#                                                                              #
# There is NO built-in fallback: the relevant file must be deployed, otherwise #
# the request raises (a missing page is treated as a deployment error).        #
# --------------------------------------------------------------------------- #

_ERROR_PAGES_DIR = (Path(__file__).resolve().parent / "error_pages").resolve()
_DEFAULT_LOCALE = "en"
# Whitelist of language tags ("en", "en-US", "pt_BR"). No slashes or dots, so a
# crafted value can never traverse out of the error_pages directory.
_LOCALE_RE = re.compile(r"^[a-z]{2}(?:[-_][a-z0-9]{2,8})?$", re.IGNORECASE)


def _normalize_locale(locale: str | None) -> str:
    locale = (locale or "").strip()
    return locale if _LOCALE_RE.match(locale) else _DEFAULT_LOCALE


def _resolve_locale(locale: str | None, accept_language: str | None) -> str:
    """Pick a locale from an explicit value or the Accept-Language header."""
    if locale:
        return _normalize_locale(locale)
    if accept_language:
        primary = accept_language.split(",", 1)[0].split(";", 1)[0]
        return _normalize_locale(primary)
    return _DEFAULT_LOCALE


@lru_cache(maxsize=64)
def _render_page(kind: str, locale: str) -> str:
    """Read ``error_pages/<kind>-<locale>.html`` from disk (no fallback).

    ``locale`` must already be normalized. Negotiates the best available file:
    the full tag, then the base language, then the default locale. If none of
    those exist a FileNotFoundError is raised, surfacing the missing deployment
    artifact. Cached for the process lifetime (restart to pick up edits).
    """
    candidates = [locale]
    base = re.split(r"[-_]", locale, 1)[0]
    if base != locale:
        candidates.append(base)
    if _DEFAULT_LOCALE not in candidates:
        candidates.append(_DEFAULT_LOCALE)

    for cand in candidates:
        path = (_ERROR_PAGES_DIR / f"{kind}-{cand}.html").resolve()
        # Defence in depth: the resolved path must stay directly inside the dir.
        if path.parent == _ERROR_PAGES_DIR and path.is_file():
            return path.read_text(encoding="utf-8")

    raise FileNotFoundError(
        f"No {kind} page for locale {locale!r} in {_ERROR_PAGES_DIR}"
    )


# Content types we are happy to let the browser render inline. Everything else
# is forced to download, and we always send X-Content-Type-Options: nosniff so
# the browser cannot re-interpret the bytes as something executable.
_INLINE_MIMES = {"application/pdf"}


def _expired_page(locale: str = _DEFAULT_LOCALE) -> HTMLResponse:
    return HTMLResponse(
        content=_render_page("expired", _normalize_locale(locale)),
        status_code=401,
    )


def _safe_download_name(file: File) -> str:
    """Build a header-safe download filename from the (untrusted) label."""
    label = ""
    if isinstance(file.label, dict) and file.label:
        label = file.label.get("en") or next(iter(file.label.values()), "")
    base = re.sub(r"[^A-Za-z0-9._-]", "_", str(label)
                  ).strip("._") or "download"
    return f"{base}.{file.extension}"


def _serve_file(file: File, locale: str = _DEFAULT_LOCALE) -> Response:
    """Stream a stored File's bytes with conservative, sniff-proof headers."""
    from src.storage.s3 import get_storage

    try:
        data = get_storage().get(storage_key_for_file(file, "original"))
    except Exception:
        data = None
    if not data:
        return _expired_page(locale)

    inline = file.mime.startswith("image/") or file.mime in _INLINE_MIMES
    disposition = "inline" if inline else "attachment"
    return Response(
        content=data,
        media_type=file.mime,
        headers={
            "Content-Disposition": f'{disposition}; filename="{_safe_download_name(file)}"',
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "private, max-age=300",
        },
    )


@router.get(
    "/public/{access_key}",
    tags=["Files"],
    summary="Access a public file",
)
def get_public_file(
    access_key: str,
    locale: str | None = Query(None),
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_db),
) -> Response:
    loc = _resolve_locale(locale, accept_language)
    file = get_file_by_access_key(db, access_key)
    if file is None or not file.published:
        # Same response whether the key is missing or simply not published.
        return _expired_page(loc)
    return _serve_file(file, loc)


@router.get(
    "/private/{access_key}",
    tags=["Files"],
    summary="Access a private file",
)
def get_private_file(
    access_key: str,
    signed_token: str = Query(..., alias="signedToken"),
    locale: str | None = Query(None),
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_db),
) -> Response:
    resource = f"files/{access_key}"
    if not verify_download_token(signed_token, resource=resource):
        return _expired_page(loc)

    file = get_file_by_access_key(db, access_key)
    if file is None:
        return _expired_page(loc)
    return _serve_file(file, loc)


@router.get(
    "/invoices/{invoice_id}/{file_name}",
    tags=["Invoicing"],
    summary="Download an invoice document",
)
def download_invoice_document(
    invoice_id: uuid.UUID,
    file_name: str,
    signed_token: str = Query(..., alias="signedToken"),
    locale: str | None = Query(None),
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_db),
) -> Response:
    loc = _resolve_locale(locale, accept_language)
    resource = f"invoices/{invoice_id}/{file_name}"
    if not verify_download_token(signed_token, resource=resource):
        return _expired_page(loc)

    invoice = get_invoice(db, invoice_id)
    if file_name.endswith(".xml"):
        key, media_type = invoice.xml_key, "application/xml"
    else:
        key, media_type = invoice.pdf_key, "application/pdf"
    if not key:
        return _expired_page(loc)

    from src.storage.s3 import get_storage

    data = get_storage().get(key)
    return Response(
        content=data,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )


@router.get(
    "/exports/{job_id}/{file_name}",
    tags=["Invoicing"],
    summary="Download an export file",
)
def download_export_file(
    job_id: uuid.UUID,
    file_name: str,
    signed_token: str = Query(..., alias="signedToken"),
    locale: str | None = Query(None),
    accept_language: str | None = Header(None, alias="Accept-Language"),
    db: Session = Depends(get_db),
) -> Response:
    loc = _resolve_locale(locale, accept_language)
    resource = f"exports/{job_id}/{file_name}"
    if not verify_download_token(signed_token, resource=resource):
        return _expired_page(loc)

    job = db.get(Job, job_id)
    if job is None or job.status != "succeeded" or not (job.result or {}).get("storage_key"):
        # Still running (or failed and being retried) — show the loading page.
        return HTMLResponse(content=_render_page("loading", loc), status_code=202)

    from src.storage.s3 import get_storage

    key: str = job.result["storage_key"]  # type: ignore
    data = get_storage().get(key)  # type: ignore
    return Response(
        content=data,
        media_type=content_type_for(file_name),
        headers={"Content-Disposition": f'attachment; filename="{file_name}"'},
    )
