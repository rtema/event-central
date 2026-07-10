"""Invoicing-domain business logic (tag: Invoicing).

The read paths (list/get/line-items/taxes) are fully implemented against the
step-2 schema. The behaviours that produce or move bytes — generating the
ZUGFeRD PDF and XRechnung XML, issuing signed download links, and building
exports — are scaffolded here and raise :class:`NotImplementedYetError`; they
are delivered in step 3 (generation): the ZUGFeRD PDF + XRechnung XML, signed
download links, exports and order cancellation are all implemented below.
"""

from __future__ import annotations

import base64
import datetime as dt
import uuid
from collections.abc import Sequence
from decimal import ROUND_HALF_UP, Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import ColumnElement, Select, String, cast, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from src.config import settings
from src.core.errors import ForbiddenError, NotFoundError
from src.core.schemas import make_multilanguage_label
from src.core.scopes import (
    SCOPE_INVOICES_WRITE_ALL,
    SCOPE_INVOICES_WRITE_OWN,
    build_scope,
    has_any,
)
from src.core.security import sign_download_token
from src.document_templates.models import DocumentTemplate
from src.document_templates.service import resolve_document_template
from src.events.models import Event
from src.events.schemas import EventOut
from src.invoices.exports import EXPORT_JOB_TYPE, run_export_job
from src.invoices.generation import (
    DocumentLine,
    InvoiceDocument,
    Party,
    build_documents,
)
from src.invoices.generation.model import (
    CANCELLATION_TYPE_CODE,
    INVOICE_TYPE_CODE,
    VAT_SCHEME,
)
from src.invoices.generation.money import (
    CENTS,
    build_line,
    build_tax_breakdown,
    classify_tax,
    money,
    totals,
)
from src.invoices.models import Invoice, InvoiceLineItem, Tax
from src.invoices.numbering import assign_invoice_number
from src.invoices.schemas import (
    InvoiceCreateRequest,
    InvoiceCreateResponse,
    InvoiceLineItemOut,
    InvoiceLinkResponse,
    InvoiceOut,
    InvoiceSearchParams,
    InvoicesExportResponse,
)
from src.jobs.models import Job
from src.orders.models import Order
from src.orders.schemas import OrderOut
from src.orders.service import get_order
from src.storage.s3 import get_storage

if TYPE_CHECKING:
    from src.auth.deps import AuthenticatedActor


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
        base = base.where(Invoice.order.event.id == event_id)
        count_stmt = count_stmt.where(Invoice.order.event.id == event_id)
    if order_id is not None:
        base = base.where(Invoice.order_id == order_id)
        count_stmt = count_stmt.where(Invoice.order_id == order_id)

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(Invoice.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def search_invoices(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_params: InvoiceSearchParams,
) -> tuple[list[Invoice], int]:
    conditions: list[ColumnElement[bool]] = []

    # filters
    filters: list[tuple[InstrumentedAttribute[Any], Sequence[Any] | None]] = [
        (Invoice.accounting_entity, search_params.accounting_entity),
        (Invoice.invoice_type, search_params.invoice_type),
        (Invoice.locale, search_params.locale),
    ]
    for column, values in filters:
        if values:
            conditions.append(column.in_(values))

    # special values
    # Currently not implemented

    # text filters
    if search_params.q and search_params.q.strip():
        term: str = search_params.q.strip()
        # escape LIKE wildcards so user input is matched literally
        escaped: str = (
            term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern: str = f"%{escaped}%"
        conditions.append(
            or_(
                Invoice.invoice_number.ilike(pattern, escape="\\"),
                cast(Invoice.supplier, String).ilike(pattern, escape="\\"),
                cast(Invoice.recipient, String).ilike(pattern, escape="\\"),
            )
        )

    # count total
    count_stmt: Select[tuple[int]] = (
        select(func.count()).select_from(Invoice).where(*conditions)
    )
    total: int = db.execute(count_stmt).scalar_one()

    # build statement
    stmt = (
        select(Invoice)
        .where(*conditions)
        .order_by(Invoice.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
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
    stmt = select(Tax).join(InvoiceLineItem, InvoiceLineItem.tax_id == Tax.id).where(
        InvoiceLineItem.invoice_id == invoice_id).distinct().order_by(Tax.rate.asc())
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


def list_all_accounting_entities(db: Session) -> list[str]:
    """All accounting entities used across all invoices (newest first) — used by Misc /accounting-entities."""  # noqa: E501
    stmt = select(Invoice.accounting_entity)\
        .where(Invoice.accounting_entity.is_not(None))\
        .distinct()\
        .order_by(Invoice.accounting_entity)

    # type: ignore see stmt, none is not allowed
    accounting_entities: list[str] = list(db.execute(stmt).scalars().all())

    return accounting_entities


# --------------------------------------------------------------------------- #
# Step-3: document generation, signed links, exports and cancellation.
# --------------------------------------------------------------------------- #
_PDF_CONTENT_TYPE = "application/pdf"
_XML_CONTENT_TYPE = "application/xml"


def _to_decimal(value: Any) -> Decimal:
    """Safely coerce any numeric-ish input (float, int, str, Decimal, None) into
    a Decimal without going through binary float noise.

    Money-relevant values (prices, quantities, rates) coming off pydantic
    request models are typically plain Python ``float``. Converting a float
    straight into a ``Decimal`` (``Decimal(0.1)``) preserves the float's binary
    imprecision (``Decimal('0.1000000000000000055511151231257827021181583404541015625')``).
    Routing it through ``str()`` first (``Decimal(str(0.1))`` -> ``Decimal('0.1')``)
    uses the value's shortest decimal repr instead, which is what every other
    money-sensitive spot in this module already does (see ``cancel_order``).
    This is the single conversion point for line/tax construction so that
    everything downstream (build_line, classify_tax, tax breakdowns, totals)
    operates on Decimals from the start instead of inheriting float rounding
    error.
    """
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def _actor_identity(actor: AuthenticatedActor | str | None) -> tuple[str | None, set[str]]:
    """Accept either a full actor (with scopes) or a bare ``sub`` string."""
    if actor is None or isinstance(actor, str):
        return actor, set()
    return actor.sub, set(getattr(actor, "scopes", set()))


def _supplier_snapshot(req: InvoiceCreateRequest) -> dict[str, Any]:
    """Resolve the supplier from the request, falling back to configured defaults."""
    supplied = req.supplier.model_dump(
        by_alias=True, exclude_none=True) if req.supplier else {}
    defaults = {
        # "legalName": settings.supplier_legal_name,
        # "legalRegistration": settings.supplier_legal_registration,
        # "vatId": settings.supplier_vat_id,
        # "iban": settings.supplier_iban,
        # "line1": settings.supplier_line1,
        "line2": None,
        "line3": None,
        # "city": settings.supplier_city,
        "zipCode": None,
        # "country": settings.supplier_country,
        "contactName":  None,
        "contactPhone": None,
        "contactEmail": None,
    }
    defaults = {k: v for k, v in defaults.items() if v is not None}
    defaults.update(supplied)
    return defaults


def _party_from_supplier(snapshot: dict[str, Any]) -> Party:
    g = snapshot.get
    return Party(
        name=g("legalName") or g("legal_name"),
        legal_registration=g("legalRegistration") or g("legal_registration"),
        vat_id=g("vatId") or g("vat_id"),
        iban=g("iban"),
        line1=g("line1"),
        line2=g("line2"),
        line3=g("line3"),
        city=g("city"),
        zip_code=g("zipCode") or g("zip_code"),
        country=g("country"),
        contact_name=g("contactName") or g("contact_name"),
        contact_phone=g("contactPhone") or g("contact_phone"),
        contact_email=g("contactEmail") or g("contact_email"),
    )


def _party_from_recipient(snapshot: dict[str, Any]) -> Party:
    g = snapshot.get
    contact_name = g("contactName") or g("contact_name")
    return Party(
        name=contact_name or g("line1"),
        vat_id=g("vatId") or g("vat_id"),
        line1=g("line1"),
        line2=g("line2"),
        line3=g("line3"),
        city=g("city"),
        zip_code=g("zipCode") or g("zip_code"),
        country=g("country"),
        contact_name=contact_name,
        contact_phone=g("contactPhone") or g("contact_phone"),
        contact_email=g("contactEmail") or g("contact_email"),
    )


def _resolve_event(
    db: Session, event_id: str, event_in: Any, actor_sub: str | None
) -> Event:
    """Find the event or create it on the fly from the embedded event object."""
    event = db.get(Event, event_id)
    if event is not None:
        # Enrich an existing event with any newly-supplied label/dates.
        if event_in is not None:
            if getattr(event_in, "label", None) and not event.label:
                event.label = make_multilanguage_label(event_in.label)
            if getattr(event_in, "start_dt", None) and event.start_dt is None:
                event.start_dt = event_in.start_dt
            if getattr(event_in, "end_dt", None) and event.end_dt is None:
                event.end_dt = event_in.end_dt
        return event

    event = Event(
        id=event_id,
        label=make_multilanguage_label(getattr(event_in, "label", None)) or {
            "de": event_id},
        start_dt=getattr(event_in, "start_dt", None),
        end_dt=getattr(event_in, "end_dt", None),
        created_by=actor_sub or "system",
    )
    db.add(event)
    db.flush()
    return event


def _resolve_order(
    db: Session, event_id: str, req: InvoiceCreateRequest, actor_sub: str | None
) -> Order:
    """Reuse an existing order (by external id within the event) or create one."""
    external_id = req.external_order_id
    links = req.links
    recipient_snapshot = req.recipient.model_dump(
        by_alias=True, exclude_none=True)

    if external_id:
        existing = db.execute(
            select(Order).where(
                Order.event_id == event_id,
                Order.external_id == external_id,
                Order.deleted_at.is_(None),
            )
        ).scalar_one_or_none()
        if existing is not None:

            # update recipient snapshot to keep everything in sync
            existing.recipient = recipient_snapshot

            return existing

    order = Order(
        event_id=event_id,
        external_id=external_id,
        payment_link=links.payment_link if links else None,
        link=links.order_link if links else None,
        status="open",
        recipient=recipient_snapshot,
        created_by=actor_sub or "system",
    )
    db.add(order)
    db.flush()
    return order


def _resolve_tax_rates(
    db: Session, req: InvoiceCreateRequest, actor_sub: str | None
) -> dict[str, Tax]:
    """Reuse existing tax_rates or create if necessary."""

    # hold the resolved tax rates
    resolved_tax_rates: dict[str, Tax] = {}

    # get the locale
    locale = req.locale

    # get list of all referenced tax rates
    used_tax_rates: set[str] = set()
    for line_item in req.line_items:
        used_tax_rates.add(line_item.external_tax_id)

    # validate no tax rate is specified more than once
    specified_tax_rates: set[str] = set()
    for tax_rate in req.tax_rates:
        if tax_rate.external_id in specified_tax_rates:
            raise ValueError(
                f"Tax rate '{tax_rate.external_id}' is specified more than once")
        specified_tax_rates.add(tax_rate.external_id)

    # validate all tax rates are specified
    if not used_tax_rates.issubset(specified_tax_rates):
        unspecified_tax_rates: list[str] = list(
            used_tax_rates - specified_tax_rates)
        unspecified_tax_rates.sort()
        raise ValueError(f"The following tax rates are not specified: \
                        {', '.join(unspecified_tax_rates)}")

    # get or create all the tax rates
    commit_changes = False
    for tax_rate in req.tax_rates:
        # skip over all unused tax rates to not pollute the database
        if tax_rate.external_id not in used_tax_rates:
            continue

        # determine the rate
        rate = Decimal(str(tax_rate.rate)).quantize(
            CENTS, rounding=ROUND_HALF_UP)

        # try to get the existing tax rate
        existing = db.execute(
            select(Tax).where(
                Tax.external_id == tax_rate.external_id,
                Tax.rate == rate,
                Tax.label[locale].astext == tax_rate.label,
                Tax.type == tax_rate.type,
                Tax.tax_exemption_reason == tax_rate.tax_exemption_reason
            )
        ).scalar()  # do not use scalar_one_or_none():
        # if deduplication had an issue: do not throw an error here, it does not do any harm
        if existing:
            # everything matches
            resolved_tax_rates[tax_rate.external_id] = existing

        # create a new tax rate
        created = Tax(
            external_id=tax_rate.external_id,
            rate=rate,
            label=make_multilanguage_label(tax_rate.label),
            type=tax_rate.type,
            tax_exemption_reason=tax_rate.tax_exemption_reason,
            created_by=actor_sub or "system",
        )
        db.add(created)
        commit_changes = True
        resolved_tax_rates[tax_rate.external_id] = created

    # commit changes to db
    if commit_changes:
        db.flush()

    # return the dict
    return resolved_tax_rates


def _build_lines_and_taxes(
    db: Session,
    req: InvoiceCreateRequest,
    invoice: Invoice,
    tax_rates: dict[str, Tax],
    actor_sub: str | None,
) -> tuple[list[InvoiceLineItem], list[DocumentLine]]:
    """Persist Tax rows and InvoiceLineItem rows; build the generator's lines.

    All money-relevant inputs (quantity, unit price, tax rate) are coerced to
    Decimal via ``_to_decimal`` *before* they touch ``classify_tax``/``build_line``.
    Previously ``rate`` and ``item.quantity``/``item.price_per_unit`` were passed
    through as whatever type the request schema produced (typically ``float``,
    since pydantic deserializes JSON numbers that way). That float noise then
    fed into every downstream Decimal computation — line net/tax/gross, the tax
    breakdown, and the invoice totals — producing cent-level rounding
    discrepancies. It also got written verbatim into
    ``InvoiceLineItem.quantity/price_per_unit/tax_rate``, so a later
    cancellation would faithfully reproduce the same float-tainted values.
    """
    line_items: list[InvoiceLineItem] = []
    doc_lines: list[DocumentLine] = []

    for position, item in enumerate(req.line_items, start=1):
        quantity = _to_decimal(item.quantity)
        price_per_unit = _to_decimal(item.price_per_unit)

        (
            tax_category,
            tax_rate,
            tax_exemption_reason,
            tax_exemption_reason_code
        ) = classify_tax(tax_rates[item.external_tax_id])

        line = build_line(
            position=position,
            name=item.name,
            quantity=quantity,
            price_per_unit_gross=price_per_unit,
            tax_category=tax_category,
            tax_rate=tax_rate,
            tax_exemption_reason=tax_exemption_reason,
            tax_exemption_reason_code=tax_exemption_reason_code,
            ticket_label=(
                item.ticket.external_ticket_option_label if item.ticket else None),
        )
        doc_lines.append(line)

        line_items.append(
            InvoiceLineItem(
                invoice=invoice,
                tax=tax_rates[item.external_tax_id],
                position=position,
                quantity=quantity,
                price_per_unit=price_per_unit,
                name=item.name,
                ticket=item.ticket.model_dump(by_alias=True, exclude_none=True)
                if item.ticket
                else None,
                tax_category=tax_category,
                tax_rate=tax_rate,
                tax_scheme=VAT_SCHEME,
                tax_exemption_reason=tax_exemption_reason if tax_category == "E" else None,
                tax_exemption_reason_code=tax_exemption_reason_code,
                total_net=line.net,
                total_tax=line.tax,
                total_gross=line.gross,
            )
        )

    return line_items, doc_lines


def _generate_and_store_documents(
    invoice: Invoice,
    doc: InvoiceDocument,
    document_template: DocumentTemplate,
) -> tuple[bytes, bytes]:
    """Render the artifacts, write them to storage and set the key columns."""
    pdf_bytes, xml_bytes = build_documents(
        doc,
        document_template,
        locale=invoice.locale,
        event=invoice.order.event,
        order=invoice.order,
        invoice=invoice
    )
    base = f"invoices/{invoice.order.event_id}/{invoice.id}"
    pdf_key = f"{base}/{invoice.invoice_number}.pdf"
    xml_key = f"{base}/{invoice.invoice_number}.xml"

    storage = get_storage()
    storage.put(pdf_key, pdf_bytes, content_type=_PDF_CONTENT_TYPE)
    storage.put(xml_key, xml_bytes, content_type=_XML_CONTENT_TYPE)

    invoice.pdf_key = pdf_key
    invoice.xml_key = xml_key
    return pdf_bytes, xml_bytes


def _stored_docs_b64(invoice: Invoice) -> tuple[str | None, str | None]:
    """Re-fetch the stored PDF/XML for an invoice as base64 (for replays)."""
    storage = get_storage()
    pdf_b64 = xml_b64 = None
    if invoice.pdf_key:
        try:
            pdf_b64 = base64.b64encode(
                storage.get(invoice.pdf_key)).decode("ascii")
        except Exception:  # noqa: BLE001
            pdf_b64 = None
    if invoice.xml_key:
        try:
            xml_b64 = base64.b64encode(
                storage.get(invoice.xml_key)).decode("ascii")
        except Exception:  # noqa: BLE001
            xml_b64 = None
    return pdf_b64, xml_b64


def _build_response(
    invoice: Invoice,
    order: Order,
    event: Event,
    *,
    pdf_b64: str | None,
    xml_b64: str | None,
) -> InvoiceCreateResponse:
    return InvoiceCreateResponse(
        invoice=InvoiceOut.model_validate(invoice),
        invoice_lines=[InvoiceLineItemOut.model_validate(
            li) for li in invoice.line_items],
        order=OrderOut.model_validate(order),
        event=EventOut.model_validate(event),
        invoice_pdf=pdf_b64,
        invoice_xml=xml_b64,
    )


def create_invoice(
    db: Session,
    *,
    payload: dict[str, Any],
    actor: AuthenticatedActor | str | None,
) -> InvoiceCreateResponse:
    """Create the order (if needed), 
    persist the invoice + lines + taxes, 
    assign a gap-free number within the accounting entity, 
    render the ZUGFeRD PDF and XRechnung XML, 
    store them, 
    and return everything in one response."""

    req = InvoiceCreateRequest.model_validate(payload)
    actor_sub, actor_scopes = _actor_identity(actor)

    # Resolve the event_id from the nested object
    event_id = req.event.id

    # TODO: Assign the necessary scopes if the event does not exist

    # Per-event authorization: invoices:write:{all|own|<eventId>}.
    required = [
        SCOPE_INVOICES_WRITE_ALL,
        SCOPE_INVOICES_WRITE_OWN,
        build_scope("invoices", "write", event_id),
    ]
    if not has_any(actor_scopes, required):
        raise ForbiddenError(
            f"missing required scope: {build_scope('invoices', 'write', event_id)}",
            error="insufficient_scope",
        )

    # resolve/create event
    event = _resolve_event(db, event_id, req.event, actor_sub)

    # resolve/create order.
    order = _resolve_order(db, event_id, req, actor_sub)

    # resolve/create tax rates
    tax_rates = _resolve_tax_rates(db, req, actor_sub)

    # resolve/create document template
    document_template = resolve_document_template(
        db, req.invoice_template, req.locale, actor_sub)

    # Numbering within the accounting entity (serialised by advisory lock).
    ae = req.accounting_entity
    prefix = ae.prefix if ae and ae.prefix else event_id
    first_number = ae.first_invoice_number if ae else 1
    pad = (ae.pad_number or 0) if ae else 0
    assigned = assign_invoice_number(
        db, prefix=prefix, first_invoice_number=first_number, pad=pad
    )

    # Set dates / snapshots.
    now = dt.datetime.now(dt.UTC)
    supplier_snapshot = _supplier_snapshot(req)
    recipient_snapshot = req.recipient.model_dump(
        by_alias=True, exclude_none=True)

    # generate the invoice
    invoice = Invoice(
        order_id=order.id,
        locale=req.locale,
        accounting_entity=prefix,
        accounting_number=assigned.accounting_number,
        invoice_number=assigned.invoice_number,
        invoice_type="invoice",
        invoice_type_code=INVOICE_TYPE_CODE,
        issue_date=now,
        due_date=req.due_date,
        currency=(req.currency or "EUR"),
        supplier=supplier_snapshot,
        recipient=recipient_snapshot,
        total_net=Decimal("0.00"),
        total_tax=Decimal("0.00"),
        total_gross=Decimal("0.00"),
        created_by=actor_sub or "system",
        document_template=document_template
    )
    db.add(invoice)

    # assign invoice.id
    # save/block invoice number
    # release the lock
    db.flush()

    # Lines + taxes.
    line_items, doc_lines = _build_lines_and_taxes(
        db, req, invoice, tax_rates, actor_sub)
    for li in line_items:
        db.add(li)
    db.flush()

    tax_breakdown = build_tax_breakdown(doc_lines)
    total_net, total_tax, total_gross = totals(tax_breakdown)
    invoice.total_net = total_net
    invoice.total_tax = total_tax
    invoice.total_gross = total_gross

    # 7. Build the generation model and render artifacts.
    doc = InvoiceDocument(
        # pyright: ignore[reportArgumentType]
        invoice_number=invoice.invoice_number or "",
        invoice_type="invoice",
        invoice_type_code=INVOICE_TYPE_CODE,
        issue_date=now.date(),
        currency=invoice.currency,
        locale=invoice.locale,
        supplier=_party_from_supplier(supplier_snapshot),
        recipient=_party_from_recipient(recipient_snapshot),
        lines=doc_lines,
        tax_breakdown=tax_breakdown,
        total_net=total_net,
        total_tax=total_tax,
        total_gross=total_gross,
        due_date=req.due_date.date(),
        buyer_reference=req.recipient.purchase_order_reference,
        order_external_id=order.external_id,
        payment_link=order.payment_link,
        order_link=order.link,
        event_id=event_id,
        event_label=(event.label or {}).get(
            "de") or (event.label or {}).get("en"),
    )

    pdf_bytes, xml_bytes = _generate_and_store_documents(
        invoice,
        doc,
        document_template
    )
    db.flush()

    return _build_response(
        invoice,
        order,
        event,
        pdf_b64=base64.b64encode(pdf_bytes).decode("ascii"),
        xml_b64=base64.b64encode(xml_bytes).decode("ascii"),
    )


def create_invoice_link(
    db: Session,
    invoice_id: uuid.UUID,
    *,
    file_type: str,
    expires_in: int | None,
) -> InvoiceLinkResponse:
    """Issue a signed, time-limited download link for a generated document."""
    invoice = get_invoice(db, invoice_id)

    if file_type == "xrechnung":
        key, suffix = invoice.xml_key, "xml"
    else:
        key, suffix = invoice.pdf_key, "pdf"
    if not key:
        raise NotFoundError(
            f"no {file_type} document available for this invoice")

    file_name = f"{invoice.invoice_number}.{suffix}"
    ttl = expires_in if expires_in is not None else 3600
    expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(seconds=ttl)
    resource = f"invoices/{invoice_id}/{file_name}"
    token = sign_download_token(
        resource=resource, expires_at=int(expires_at.timestamp()))
    url = (
        f"{settings.api_base_url}/api/v1/files/invoices/"
        f"{invoice_id}/{file_name}?signedToken={token}"
    )
    return InvoiceLinkResponse(url=url, expires_at=expires_at)


def export_invoices(
    db: Session, *, accounting_entity: str | None, export_format: str, actor: str | None
) -> InvoicesExportResponse:
    """Create an export job, run it (inline in dev; via the worker in prod) and
    return a signed link to the produced xlsx/zip."""
    from src.invoices.exports import content_type_for, export_filename

    file_name = export_filename(export_format, accounting_entity)
    job = Job(
        type=EXPORT_JOB_TYPE,
        status="queued",
        payload={
            "format": export_format,
            "accounting_entity": accounting_entity,
            "file_name": file_name,
            "requested_by": actor,
        },
    )
    db.add(job)
    db.flush()

    # No queue worker runs in dev/CI, so produce the artefact synchronously. The
    # very same entry point is what the worker container calls in production.
    run_export_job(db, job)

    result = job.result or {}
    file_name = result.get("file_name", file_name)
    expires_at = dt.datetime.now(dt.UTC) + dt.timedelta(hours=24)
    resource = f"exports/{job.id}/{file_name}"
    token = sign_download_token(
        resource=resource, expires_at=int(expires_at.timestamp()))
    url = (
        f"{settings.api_base_url}/api/v1/files/exports/"
        f"{job.id}/{file_name}?signedToken={token}"
    )
    _ = content_type_for(file_name)
    return InvoicesExportResponse(url=url, expires_at=expires_at)


def cancel_order(
    db: Session, order_id: uuid.UUID, *, actor: str | None
) -> InvoiceCreateResponse:
    """Cancel an order: bring the balance of all its invoices to 0.00.

    If the outstanding balance is already zero, the last issued invoice is
    returned unchanged. Otherwise a cancellation invoice (``invoiceType``
    ``cancellation``, code 381) is issued that reverses the most recent original
    invoice, the order is flipped to ``cancelled`` and the new document set is
    returned.
    """
    order = get_order(db, order_id)
    invoices = list_order_invoices(db, order_id)
    if not invoices:
        raise NotFoundError("order has no invoices to cancel")

    event = db.get(Event, order.event_id)
    if event is None:
        raise NotFoundError("event does not exist")

    balance = money(sum((_to_decimal(inv.total_gross)
                    for inv in invoices), Decimal("0.00")))

    # Newest-first ordering for "last issued".
    ordered = sorted(
        invoices,
        key=lambda i: (i.accounting_number or 0,
                       i.created_at or dt.datetime.min),
        reverse=True,
    )

    if balance == Decimal("0.00"):
        last = ordered[0]
        pdf_b64, xml_b64 = _stored_docs_b64(last)
        return _build_response(last, order, event, pdf_b64=pdf_b64, xml_b64=xml_b64)

    # Reverse the most recent non-cancellation invoice.
    source = next((i for i in ordered if i.invoice_type !=
                  "cancellation"), ordered[0])

    now = dt.datetime.now(dt.UTC)
    prefix = source.accounting_entity or order.event_id
    assigned = assign_invoice_number(
        db, prefix=prefix, first_invoice_number=1, pad=0)

    cancellation = Invoice(
        order_id=order.id,
        locale=source.locale,
        accounting_entity=prefix,
        accounting_number=assigned.accounting_number,
        invoice_number=assigned.invoice_number,
        invoice_type="cancellation",
        invoice_type_code=CANCELLATION_TYPE_CODE,
        issue_date=now,
        due_date=now,
        currency=source.currency,
        supplier=source.supplier,
        recipient=source.recipient,
        total_net=Decimal("0.00"),
        total_tax=Decimal("0.00"),
        total_gross=Decimal("0.00"),
        created_by=actor or "system",
    )
    db.add(cancellation)
    db.flush()

    # Negate each source line into the cancellation document + persisted lines.
    doc_lines: list[DocumentLine] = []
    for src_line in source.line_items:
        qty = -_to_decimal(src_line.quantity)
        category = src_line.tax_category or "S"
        rate = _to_decimal(src_line.tax_rate)
        line = build_line(
            position=src_line.position,
            name=src_line.name,
            quantity=qty,
            price_per_unit_gross=_to_decimal(src_line.price_per_unit),
            tax_category=category,
            tax_rate=rate,
            tax_exemption_reason=src_line.tax_exemption_reason,
            tax_exemption_reason_code=src_line.tax_exemption_reason_code,
        )
        doc_lines.append(line)
        db.add(
            InvoiceLineItem(
                invoice_id=cancellation.id,
                position=src_line.position,
                quantity=qty,
                price_per_unit=_to_decimal(src_line.price_per_unit),
                name=src_line.name,
                ticket=src_line.ticket,
                tax_category=category,
                tax_rate=rate,
                tax_scheme=src_line.tax_scheme or VAT_SCHEME,
                tax_exemption_reason=src_line.tax_exemption_reason,
                tax_exemption_reason_code=src_line.tax_exemption_reason_code,
                total_net=line.net,
                total_tax=line.tax,
                total_gross=line.gross,
                tax=src_line.tax
            )
        )
    db.flush()

    breakdown = build_tax_breakdown(doc_lines)
    total_net, total_tax, total_gross = totals(breakdown)
    cancellation.total_net = total_net
    cancellation.total_tax = total_tax
    cancellation.total_gross = total_gross

    supplier_snapshot = source.supplier or {}
    recipient_snapshot = source.recipient or {}
    doc = InvoiceDocument(
        invoice_number=cancellation.invoice_number,  # type: ignore
        invoice_type="cancellation",
        invoice_type_code=CANCELLATION_TYPE_CODE,
        issue_date=now.date(),
        currency=cancellation.currency,
        locale=cancellation.locale,
        supplier=_party_from_supplier(supplier_snapshot),
        recipient=_party_from_recipient(recipient_snapshot),
        lines=doc_lines,
        tax_breakdown=breakdown,
        total_net=total_net,
        total_tax=total_tax,
        total_gross=total_gross,
        due_date=now.date(),
        buyer_reference=recipient_snapshot.get("purchaseOrderReference", None),
        order_external_id=order.external_id,
        payment_link=order.payment_link,
        order_link=order.link,
        event_label=(event.label or {}).get("de") if event else None,
        notes=[f"Storno zur Rechnung {source.invoice_number}"],
    )

    # resolve/create document template
    document_template = ordered[-1].document_template

    pdf_bytes, xml_bytes = _generate_and_store_documents(
        cancellation, doc, document_template)
    order.status = "cancelled"
    db.flush()

    return _build_response(
        cancellation,
        order,
        event=cancellation.order.event,
        pdf_b64=base64.b64encode(pdf_bytes).decode("ascii"),
        xml_b64=base64.b64encode(xml_bytes).decode("ascii"),
    )
