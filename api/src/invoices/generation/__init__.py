"""E-invoice document generation (step 3).

Turns a normalized, ORM-free invoice description (:mod:`model`) into the two
artefacts the API returns and stores:

* an **XRechnung**-conformant UN/CEFACT **CII** XML (:mod:`cii`), and
* a hybrid **ZUGFeRD** PDF/A-3 that embeds that same XML (:mod:`render`).

The package is deliberately decoupled from SQLAlchemy and FastAPI so the
generators can be unit-tested in isolation and reused by the queue worker.
"""

from __future__ import annotations

from src.invoices.generation.documents import build_documents
from src.invoices.generation.model import (
    DocumentLine,
    InvoiceDocument,
    Party,
    TaxBreakdownEntry,
)

__all__ = [
    "build_documents",
    "DocumentLine",
    "InvoiceDocument",
    "Party",
    "TaxBreakdownEntry",
]
