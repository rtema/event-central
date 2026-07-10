"""Invoice exports: an xlsx of invoicing data or a zip of the documents.

An export is modelled as a :class:`~src.jobs.models.Job` row so the work can be
claimed and run by the dedicated queue-handler container in production. No
worker runs in dev/CI, so :func:`run_export_job` is invoked inline immediately
after the job is created; the very same function is what a future worker would
call after claiming the row with ``SELECT ... FOR UPDATE SKIP LOCKED``.

The produced artefact is written to object storage under
``exports/{job_id}/{filename}`` and the job's ``result`` records the storage key
and filename so the download route can stream it.
"""

from __future__ import annotations

import datetime as dt
import io
import zipfile
from typing import TYPE_CHECKING

from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.invoices.models import Invoice, InvoiceLineItem
from src.storage.s3 import get_storage

if TYPE_CHECKING:
    from src.jobs.models import Job

EXPORT_JOB_TYPE = "invoice_export"

_XLSX_CONTENT_TYPE = (
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)
_ZIP_CONTENT_TYPE = "application/zip"


def export_filename(export_format: str, accounting_entity: str | None) -> str:
    stamp = dt.datetime.now(dt.UTC).strftime("%Y%m%d")
    scope = (accounting_entity or "all").replace("/", "-")
    ext = "xlsx" if export_format == "xlsx" else "zip"
    return f"invoices-{scope}-{stamp}.{ext}"


def content_type_for(filename: str) -> str:
    return _XLSX_CONTENT_TYPE if filename.endswith(".xlsx") else _ZIP_CONTENT_TYPE


def _select_invoices(db: Session, accounting_entity: str | None) -> list[Invoice]:
    stmt = select(Invoice).order_by(
        Invoice.accounting_entity, Invoice.accounting_number)
    if accounting_entity:
        stmt = stmt.where(Invoice.accounting_entity == accounting_entity)
    return list(db.execute(stmt).scalars().all())


def _as_float(value: object) -> float:
    return float(value) if value is not None else 0.0


def build_xlsx(db: Session, invoices: list[Invoice]) -> bytes:
    """Build a two-sheet workbook: one row per invoice, one per line item."""
    wb = Workbook()
    inv_sheet = wb.active
    inv_sheet.title = "Invoices"
    inv_sheet.append(
        [
            "Invoice number",
            "Accounting entity",
            "Accounting number",
            "Type",
            "Type code",
            "Event",
            "Issue date",
            "Due date",
            "Currency",
            "Net",
            "Tax",
            "Gross",
            "Recipient",
            "Created by",
        ]
    )
    for inv in invoices:
        recipient = inv.recipient or {}
        recipient_name = (
            recipient.get("contactName")
            or recipient.get("contact_name")
            or recipient.get("line1")
            or ""
        )
        inv_sheet.append(
            [
                inv.invoice_number,
                inv.accounting_entity,
                inv.accounting_number,
                inv.invoice_type,
                inv.invoice_type_code,
                inv.event_id,
                inv.issue_date.date().isoformat() if inv.issue_date else None,
                inv.due_date.date().isoformat() if inv.due_date else None,
                inv.currency,
                _as_float(inv.total_net),
                _as_float(inv.total_tax),
                _as_float(inv.total_gross),
                recipient_name,
                inv.created_by,
            ]
        )

    line_sheet = wb.create_sheet("Line items")
    line_sheet.append(
        [
            "Invoice number",
            "Position",
            "Name",
            "Quantity",
            "Price per unit",
            "Tax category",
            "Tax rate",
            "Net",
            "Tax",
            "Gross",
        ]
    )
    by_invoice = {inv.id: inv.invoice_number for inv in invoices}
    if invoices:
        items = db.execute(
            select(InvoiceLineItem)
            .where(InvoiceLineItem.invoice_id.in_(list(by_invoice)))
            .order_by(InvoiceLineItem.invoice_id, InvoiceLineItem.position)
        ).scalars().all()
        for item in items:
            line_sheet.append(
                [
                    by_invoice.get(item.invoice_id),
                    item.position,
                    item.name,
                    _as_float(item.quantity),
                    _as_float(item.price_per_unit),
                    item.tax_category,
                    _as_float(item.tax_rate),
                    _as_float(item.total_net),
                    _as_float(item.total_tax),
                    _as_float(item.total_gross),
                ]
            )

    buffer = io.BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


def build_zip(invoices: list[Invoice]) -> bytes:
    """Bundle every invoice's stored PDF and XML into a single zip archive."""
    storage = get_storage()
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for inv in invoices:
            number = inv.invoice_number or str(inv.id)
            for key, suffix in ((inv.pdf_key, "pdf"), (inv.xml_key, "xml")):
                if not key:
                    continue
                try:
                    data = storage.get(key)
                except Exception:  # noqa: BLE001 - skip artefacts missing from storage
                    continue
                archive.writestr(f"{number}.{suffix}", data)
    return buffer.getvalue()


def run_export_job(db: Session, job: Job) -> None:
    """Execute an export job: build the artefact and store it.

    Idempotent enough for at-least-once delivery: re-running simply rewrites the
    object at the deterministic ``exports/{job_id}/{filename}`` key. On success
    the job's ``result`` carries ``storage_key``, ``file_name`` and ``content_type``.
    """
    payload = job.payload or {}
    export_format = payload.get("format", "xlsx")
    accounting_entity = payload.get("accounting_entity")
    file_name = payload.get("file_name") or export_filename(
        export_format, accounting_entity)

    job.status = "running"
    job.attempts = (job.attempts or 0) + 1
    db.flush()

    try:
        invoices = _select_invoices(db, accounting_entity)
        data = build_zip(
            invoices) if export_format == "zip" else build_xlsx(db, invoices)

        key = f"exports/{job.id}/{file_name}"
        get_storage().put(key, data, content_type=content_type_for(file_name))

        job.result = {
            "storage_key": key,
            "file_name": file_name,
            "content_type": content_type_for(file_name),
            "invoice_count": len(invoices),
        }
        job.status = "succeeded"
        job.error = None
    except Exception as exc:  # noqa: BLE001 - persist failure for the API/worker
        job.status = "failed"
        job.error = str(exc)
        db.flush()
        raise
    finally:
        db.flush()
