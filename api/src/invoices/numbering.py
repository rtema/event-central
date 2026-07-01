"""Gap-free, race-safe invoice number assignment within an accounting entity.

Invoice numbers are issued per *accounting entity* (Rechnungskreis), which is
identified by a ``prefix``. The next sequence value is::

    n = max(existing_max_in_prefix + 1, first_invoice_number)
    invoice_number = f"{prefix}{n:0{pad}d}"

Because the API runs across several horizontally-scaled web workers, two
concurrent ``POST /invoices`` calls for the same entity could otherwise read
the same ``max`` and mint a duplicate number. We serialise per-prefix with a
PostgreSQL *transaction-level advisory lock* (``pg_advisory_xact_lock``): the
lock is keyed on a stable hash of the prefix, is held until the surrounding
transaction commits/rolls back, and only blocks other issuers for the *same*
prefix — different entities proceed in parallel.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from src.invoices.models import Invoice

# Arbitrary namespace constant so our advisory locks don't collide with any
# other subsystem's advisory locks (the two-int form gives us a private space).
_LOCK_NAMESPACE = 0x4E564349  # "NVCI"


def _prefix_lock_key(prefix: str) -> int:
    """Map a prefix to a stable signed 32-bit int for pg_advisory_xact_lock."""
    h = zlib.crc32(prefix.encode("utf-8")) & 0xFFFFFFFF
    # Fold into the signed int4 range Postgres expects for the 2-arg form.
    return h - 0x100000000 if h >= 0x80000000 else h


@dataclass(slots=True)
class AssignedNumber:
    accounting_number: int
    invoice_number: str


def assign_invoice_number(
    db: Session,
    *,
    prefix: str,
    first_invoice_number: int = 1,
    pad: int = 0,
) -> AssignedNumber:
    """Reserve and format the next invoice number for ``prefix``.

    Must be called inside an open transaction; the advisory lock is released
    automatically when that transaction ends, so the caller should persist the
    new invoice in the *same* transaction to keep numbering gap-free.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(:ns, :key)"),
        {"ns": _LOCK_NAMESPACE, "key": _prefix_lock_key(prefix)},
    )

    current_max = db.execute(
        select(func.max(Invoice.accounting_number)).where(
            Invoice.accounting_entity == prefix
        )
    ).scalar_one_or_none()

    nxt = (
        first_invoice_number
        if current_max is None
        else max(current_max + 1, first_invoice_number)
    )
    number = f"{prefix}{nxt:0{pad}d}" if pad else f"{prefix}{nxt}"
    return AssignedNumber(accounting_number=nxt, invoice_number=number)
