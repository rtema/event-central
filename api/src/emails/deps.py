"""Email delivery machinery for the emails module.

Everything the request path does *not* call directly lives here: rendering +
queueing (``queue_email``), the SMTP transport helpers, and the two send
entrypoints — ``send_queued_email_sync`` (inline, lock held) and
``drain_email_queue`` (background worker). Route-facing CRUD/search lives in
``src.emails.service``; this module imports ``_now`` from there.
"""

from __future__ import annotations

import datetime as dt
import mimetypes
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from io import BytesIO

from sqlalchemy import or_, select
from sqlalchemy.orm import Session
from src.config import settings
from src.core.security import decrypt_secret
from src.emails.models import (
    Email,
    EmailAttachment,
    EmailSender,
    EmailTemplate,
)
from src.emails.renderer import render_email
from src.emails.schemas import (
    EMAIL_STATUS_DELIVERED,
    EMAIL_STATUS_FAILED,
    EMAIL_STATUS_SCHEDULED,
)
from src.events.models import Event
from src.files.models import File
from src.files.service import create_file, get_file, get_file_data
from src.invoices.models import Invoice
from src.orders.models import Order
from src.users.models import User


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _save_attachment_file(
    db: Session, file_name: str, data: BytesIO, *, created_by: str,
) -> File:
    """Return a canonical File for these bytes, reusing an existing row when the
    content hash already exists. New content goes through create_file so it is
    size-bounded, AV-scanned, sniffed and stored exactly like any upload."""

    file = create_file(
        db,
        data,
        label={},
        base_path="email-attachments",
        created_by=created_by,
        filename=file_name
    )
    return file


# --------------------------------------------------------------------------- #
# Queueing
# --------------------------------------------------------------------------- #
def queue_email(
    db: Session,
    email_template: EmailTemplate,
    email_sender: EmailSender,
    to: list[str],
    cc: list[str],
    bcc: list[str],
    attachments: list[tuple[str, BytesIO]],
    *,
    created_by: str,
    send_time: dt.datetime | None = None,
    user: User | None = None,
    event: Event | None = None,
    order: Order | None = None,
    invoice: Invoice | None = None,
    extra: dict[str, str] | None = None
) -> Email:
    """Render the template and persist a scheduled Email (plus its attachment
    files). Does no network I/O: the row is left in EMAIL_STATUS_SCHEDULED for
    send_email to deliver, either inline right after queuing or later from a
    background worker that polls for due, scheduled rows.
    """

    # render email
    body, subject, email_template_version_id = render_email(
        db,
        email_template,
        user=user,
        event=event,
        order=order,
        invoice=invoice,
        extra=extra
    )

    # create email
    email = Email(
        email_template_version_id=email_template_version_id,
        email_sender=email_sender,
        locale=email_template.locale,
        to=to,
        cc=cc,
        bcc=bcc,
        sender=formataddr(
            (email_sender.from_name or "", email_sender.from_email)),
        subject=subject,
        body=body,
        status=EMAIL_STATUS_SCHEDULED,
        send_after=send_time if send_time else _now(),
        retry_after=None,
        retries=0,
        delivered_at=None,
        server_response=None,
        created_by=created_by
    )
    db.add(email)
    # Flush so email.id is populated before we attach rows that reference it.
    db.flush()

    # Save attachments as canonical files (AV-scanned, size-bounded) and link
    # them to the email. The bytes live in storage; send_email reads them back.
    for file_name, file_contents in attachments:
        file = _save_attachment_file(
            db, file_name, file_contents, created_by=created_by)

        attachment = EmailAttachment(
            email_id=email.id,
            file=file,
            file_name=file_name
        )
        db.add(attachment)

    db.flush()

    return email


# --------------------------------------------------------------------------- #
# SMTP transport
# --------------------------------------------------------------------------- #
def _build_email_message(
    email: Email,
    email_sender: EmailSender,
    attachments: list[tuple[str, bytes]],
) -> EmailMessage:
    """Turn a persisted Email row into a MIME message ready for the relay.

    ``email.body`` is the rendered template output (HTML); we send it as the
    HTML alternative and provide a minimal plaintext fallback so the message is
    well-formed for clients that refuse HTML.
    """
    msg = EmailMessage()
    msg["Subject"] = email.subject
    # Prefer a properly-encoded From over raw string interpolation so a missing
    # from_name doesn't produce a literal "None <addr>".
    msg["From"] = formataddr(
        (email_sender.from_name or "", email_sender.from_email))
    msg["To"] = ", ".join(email.to)
    if email.cc:
        msg["Cc"] = ", ".join(email.cc)
    if email_sender.reply_to:
        msg["Reply-To"] = email_sender.reply_to

    msg.set_content("This message requires an HTML-capable email client.")
    msg.add_alternative(email.body, subtype="html")

    for file_name, raw in attachments:
        ctype, _ = mimetypes.guess_type(file_name)
        maintype, subtype = (
            ctype.split("/", 1) if ctype else ("application", "octet-stream")
        )
        msg.add_attachment(
            raw, maintype=maintype, subtype=subtype, filename=file_name
        )

    return msg


def _smtp_send(
    email_sender: EmailSender, msg: EmailMessage, recipients: list[str]
) -> str:
    """Open a connection according to the sender's security mode, authenticate
    if credentials are present, and hand the message to the relay.

    Returns a short server response string on success; raises on failure.
    """
    security = (email_sender.security or "starttls").lower()
    host, port = email_sender.host, email_sender.port

    if security == "ssl":
        context = ssl.create_default_context()
        smtp: smtplib.SMTP = smtplib.SMTP_SSL(
            host, port, context=context, timeout=settings.api_email_smtp_timeout_seconds
        )
    else:
        smtp = smtplib.SMTP(
            host, port, timeout=settings.api_email_smtp_timeout_seconds)

    try:
        smtp.ehlo()
        if security == "starttls":
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()

        if email_sender.username:
            smtp.login(
                email_sender.username,
                decrypt_secret(
                    email_sender.password) if email_sender.password else ""
            )

        # Passing to_addrs explicitly keeps Bcc out of the visible headers while
        # still delivering to those recipients. A non-empty return means some
        # recipients were refused, which we treat as a failure.
        refused = smtp.send_message(msg, to_addrs=recipients)
        if refused:
            raise smtplib.SMTPRecipientsRefused(refused)

        return "250 Message accepted for delivery"
    finally:
        try:
            smtp.quit()
        except Exception:
            smtp.close()


def _load_attachment_bytes(db: Session, attachment: EmailAttachment) -> bytes | None:
    if attachment.file_id is None:
        return None
    file = get_file(db, attachment.file_id)
    if file is None:
        return None

    return get_file_data(db, attachment.file_id)


def _send_email(db: Session, email: Email) -> Email:
    """Deliver an already-queued Email via its sender's SMTP relay and record
    the outcome on the row (status / delivered_at / server_response /
    retry_after / retries).

    Idempotent for already-sent rows. Delivery failures are captured rather
    than raised so a flaky relay never rolls back the caller's transaction; the
    row is rescheduled with exponential backoff until MAX_EMAIL_RETRIES, then
    marked failed. This is the single place that talks to SMTP, so it serves
    both an inline send right after queue_email and a scheduled worker.

    Typical worker loop:
        due = db.execute(
            select(Email).where(
                Email.status == EMAIL_STATUS_SCHEDULED,
                Email.send_after <= _now(),
                or_(Email.retry_after.is_(None), Email.retry_after <= _now()),
            )
        ).scalars().all()
        for email in due:
            send_email(db, email)
    """
    if email.status == EMAIL_STATUS_DELIVERED:
        return email

    email_sender = email.email_sender
    if email_sender is None:
        email.status = EMAIL_STATUS_FAILED
        email.server_response = "no email sender configured"
        db.flush()
        return email

    recipients = [*email.to, *email.cc, *email.bcc]
    if not recipients:
        email.status = EMAIL_STATUS_FAILED
        email.server_response = "no recipients"
        db.flush()
        return email

    # Read attachment bytes back from storage.
    attachments: list[tuple[str, bytes]] = []
    for att in email.email_attachments:
        raw = _load_attachment_bytes(db, att)
        if raw is not None:
            attachments.append((att.file_name, raw))

    try:
        msg = _build_email_message(email, email_sender, attachments)
        server_response = _smtp_send(email_sender, msg, recipients)
    except Exception as exc:  # noqa: BLE001 - persist any delivery failure
        email.retries += 1
        email.server_response = str(exc)[:2000]
        if email.retries >= settings.api_email_max_retries:
            email.status = EMAIL_STATUS_FAILED
            email.retry_after = None
        else:
            email.status = EMAIL_STATUS_SCHEDULED
            backoff = settings.api_email_backoff_minutes ** email.retries
            email.retry_after = _now() + dt.timedelta(minutes=backoff)
        db.flush()
        return email

    email.status = EMAIL_STATUS_DELIVERED
    email.delivered_at = _now()
    email.server_response = server_response
    email.retry_after = None
    db.flush()
    return email


def _lock_email(db: Session, email: Email) -> Email:
    """Take a Postgres row lock (SELECT ... FOR UPDATE) on this email's row.

    Blocks until the lock is free, so if a worker is mid-send on the same row
    this waits rather than racing it. The lock lives until the surrounding
    transaction commits or rolls back, so the caller must keep the row locked
    for the entire send by not committing until delivery is done.
    """
    return db.execute(
        select(Email).where(Email.id == email.id).with_for_update()
    ).scalar_one()


# --------------------------------------------------------------------------- #
# Synchronous send (lock held for the duration of the send)
# --------------------------------------------------------------------------- #
def send_queued_email_sync(db: Session, email: Email) -> Email:
    """Synchronously deliver an already-queued row, locking it first so a
    concurrent worker can't also grab it. Caller commits to release the lock."""
    _lock_email(db, email)
    return _send_email(db, email)


# --------------------------------------------------------------------------- #
# Asynchronous worker (lock held for the duration of the send)
# --------------------------------------------------------------------------- #
def drain_email_queue(db: Session, *, batch_size: int = 10) -> int:
    """Deliver a batch of due, scheduled emails. Worker entrypoint: it owns the
    transaction and commits at the end, which is what releases the row locks.

    Rows are claimed with FOR UPDATE SKIP LOCKED, so any number of workers can
    run this concurrently and partition the due rows between them without
    blocking or double-sending. Each locked row is held for its entire send,
    then all locks drop together on commit. Call on a loop (e.g. every few
    seconds) from cron / APScheduler / Celery beat.

    Returns the number of emails processed this pass.
    """
    now = _now()
    stmt = (
        select(Email)
        .where(
            Email.status == EMAIL_STATUS_SCHEDULED,
            Email.send_after <= now,
            or_(Email.retry_after.is_(None), Email.retry_after <= now),
        )
        .order_by(Email.send_after)
        .limit(batch_size)
        # of=Email keeps the lock on the emails row only, so eager-loaded
        # relations (sender, attachments) don't get locked too.
        .with_for_update(skip_locked=True, of=Email)
    )
    emails = list(db.execute(stmt).scalars().all())

    for email in emails:
        _send_email(db, email)

    db.commit()  # releases every FOR UPDATE lock taken above
    return len(emails)
