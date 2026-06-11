"""Invoicing-domain business logic (tag: Invoicing).

The read paths (list/get/line-items/taxes) are fully implemented against the
step-2 schema. The behaviours that produce or move bytes — generating the
ZUGFeRD PDF and XRechnung XML, issuing signed download links, and building
exports — are scaffolded here and raise :class:`NotImplementedYetError`; they
are delivered in step 3 (generation) and step 4 (validation).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from src.core.errors import NotFoundError, NotImplementedYetError
from src.invoices.models import Invoice, InvoiceLineItem, Tax
from src.invoices.schemas import InvoiceCreateResponse, InvoiceLinkResponse, InvoicesExportResponse
from src.orders.service import get_order


def list_invoices(
    db: Session,
    *,
    limit: int,
    offset: int,
    event_id: str | None = None,
    order_id: uuid.UUID | None = None,
) -> tuple[list[Invoice], int]:
    base = select(Invoice)
    count_stmt = select(func.count()).select_from(Invoice)
    if event_id is not None:
        base = base.where(Invoice.event_id == event_id)
        count_stmt = count_stmt.where(Invoice.event_id == event_id)
    if order_id is not None:
        base = base.where(Invoice.order_id == order_id)
        count_stmt = count_stmt.where(Invoice.order_id == order_id)

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def get_invoice(db: Session, invoice_id: uuid.UUID) -> Invoice:
    invoice = db.get(Invoice, invoice_id)
    if invoice is None:
        raise NotFoundError("invoice not found")
    return invoice


def get_invoice_line_items(db: Session, invoice_id: uuid.UUID) -> list[InvoiceLineItem]:
    get_invoice(db, invoice_id)  # 404 if missing
    stmt = (
        select(InvoiceLineItem)
        .where(InvoiceLineItem.invoice_id == invoice_id)
        .order_by(InvoiceLineItem.position.asc())
    )
    return list(db.execute(stmt).scalars().all())


def get_invoice_taxes(db: Session, invoice_id: uuid.UUID) -> list[Tax]:
    get_invoice(db, invoice_id)  # 404 if missing
    stmt = select(Tax).where(Tax.invoice_id ==
                             invoice_id).order_by(Tax.created_at.asc())
    return list(db.execute(stmt).scalars().all())


def list_order_invoices(db: Session, order_id: uuid.UUID) -> list[Invoice]:
    get_order(db, order_id)  # 404 if missing
    invoices, _ = list_invoices(db, limit=1000, offset=0, order_id=order_id)
    return invoices


def list_all_taxes(db: Session, *, limit: int, offset: int) -> tuple[list[Tax], int]:
    """All tax rates across all invoices (newest first) — used by Misc /taxes."""
    total = db.execute(select(func.count()).select_from(Tax)).scalar_one()
    stmt = select(Tax).order_by(
        Tax.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


# --------------------------------------------------------------------------- #
# Step-3 seams: document generation, signed links and exports.
# --------------------------------------------------------------------------- #
def create_invoice(
        db: Session,
        *,
        payload: dict[str, Any],
        actor: str | None
) -> InvoiceCreateResponse:
    """Create an order (if needed), persist the invoice and its lines, assign a
    number within the accounting entity, and render the ZUGFeRD PDF + XRechnung
    XML. Implemented in step 3."""
    raise NotImplementedYetError(
        "invoice generation (PDF/XML) is implemented in step 3",
    )


def create_invoice_link(
    db: Session,
    invoice_id: uuid.UUID,
    *,
    file_type: str,
    expires_in: int | None
) -> InvoiceLinkResponse:
    """Issue a signed, time-limited download link for a generated document.
    Implemented in step 3 (requires the generated artefacts in object storage)."""
    get_invoice(db, invoice_id)  # 404 now; link issuance lands in step 3
    raise NotImplementedYetError(
        "signed download links are implemented in step 3",
    )


def export_invoices(
    db: Session, *, accounting_entity: str | None, export_format: str, actor: str | None
) -> InvoicesExportResponse:
    """Enqueue an export job (xlsx of invoicing data, or a zip of documents) and
    return a signed link to the result. Implemented in step 3."""
    raise NotImplementedYetError(
        "invoice exports are implemented in step 3",
    )


def cancel_order(db: Session, order_id: uuid.UUID, *, actor: str | None) -> InvoiceCreateResponse:
    """Cancel an order and issue the corresponding cancellation invoice
    (invoiceType ``cancellation``, code 381). Implemented in step 3."""
    get_order(db, order_id)  # 404 now; cancellation invoice lands in step 3
    raise NotImplementedYetError(
        "order cancellation issues a cancellation invoice, implemented in step 3",
    )
