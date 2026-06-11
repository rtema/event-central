"""Smoke test for the file-download endpoints (tag: Files).

These routes are authorised by a signed token (not a bearer) and stream bytes
from object storage in step 3, so for now they return 501 with a token and 422
without one. No database fixtures are required.
Run with ``PYTHONPATH=. python scripts/smoke_files.py`` or ``python -m src smoke``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.services.web import app

_passed = 0
_failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _passed, _failed
    mark = "PASS" if condition else "FAIL"
    if condition:
        _passed += 1
    else:
        _failed += 1
    print(f"[{mark}] {label}" + (f" :: {detail}" if detail and not condition else ""))


def main() -> int:
    c: Any = TestClient(app)
    invoice_id = uuid.uuid4()
    job_id = uuid.uuid4()

    r = c.get(f"/api/v1/files/invoices/{invoice_id}/inv.pdf?signedToken=abc")
    check("invoice file download -> 501", r.status_code == 501, r.text)

    r = c.get(f"/api/v1/files/invoices/{invoice_id}/inv.pdf")
    check("invoice file download without token -> 422", r.status_code == 422, r.text)

    r = c.get(f"/api/v1/files/exports/{job_id}/export.xlsx?signedToken=abc")
    check("export file download -> 501", r.status_code == 501, r.text)

    r = c.get(f"/api/v1/files/exports/{job_id}/export.xlsx")
    check("export file download without token -> 422", r.status_code == 422, r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())