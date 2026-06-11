"""Smoke test for the Invoicing endpoints (tag: Invoicing).

Covers the invoice list/detail, line-items and taxes reads, request validation,
and the step-3 seams (create / export / signed link) which return 501.
Run with ``PYTHONPATH=. python scripts/smoke_invoices.py`` or ``python -m src smoke``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.auth.service import issue_token_pair
from src.core.db import SessionLocal
from src.events.models import Event
from src.invoices.models import Invoice, InvoiceLineItem, Tax
from src.orders.models import Order
from src.services.web import app
from src.users.models import User, UserScope

_passed = 0
_failed = 0


def check(label: str, condition: bool, detail: str = "") -> None:
    global _passed, _failed
    mark = "PASS" if condition else "FAIL"
    if condition:
        _passed += 1
    else:
        _failed += 1
    print(f"[{mark}] {label}" +
          (f" :: {detail}" if detail and not condition else ""))


def seed() -> dict[str, str]:
    with SessionLocal() as db:
        admin = User(email=f"inv-admin-{uuid.uuid4().hex[:8]}@example.com",
                     first_name="Inv", last_name="Admin")
        db.add(admin)
        db.flush()
        for scope in ("invoices:read:all", "invoices:write:all"):
            db.add(UserScope(user_id=admin.id, scope=scope, created_by="smoke"))
        db.flush()

        event = Event(
            id=f"ev-{uuid.uuid4().hex[:8]}", label={"en": "Fair"}, created_by="smoke")
        db.add(event)
        db.flush()
        order = Order(event_id=event.id, external_id=f"ord-{uuid.uuid4().hex[:6]}",
                      status="open", created_by="smoke")
        db.add(order)
        db.flush()
        invoice = Invoice(order_id=order.id, event_id=event.id, currency="EUR",
                          accounting_entity="TEMA26-", accounting_number=100,
                          invoice_number="TEMA26-000100", total_net=100, total_tax=19,
                          total_gross=119, created_by="smoke")
        db.add(invoice)
        db.flush()
        tax = Tax(invoice_id=invoice.id, external_id="t1", rate=19,
                  label={"en": "VAT 19%"}, type="standard", created_by="smoke")
        db.add(tax)
        db.flush()
        db.add(InvoiceLineItem(invoice_id=invoice.id, tax_id=tax.id, position=1, quantity=1,
                               price_per_unit=119, name="Ticket", tax_rate=19,
                               total_net=100, total_tax=19, total_gross=119))

        token = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke"
        ).access_token
        ids = {"token": token, "invoice_id": str(
            invoice.id), "event_id": event.id}
        db.commit()
        return ids


def main() -> int:
    f = seed()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {f['token']}"}
    iid = f["invoice_id"]

    check("list invoices without token -> 401",
          c.get("/api/v1/invoices").status_code == 401)

    r = c.get("/api/v1/invoices", headers=h)
    check("list invoices -> 200", r.status_code ==
          200 and len(r.json()["data"]) >= 1, r.text)

    r = c.get(f"/api/v1/invoices/{iid}", headers=h)
    check("get invoice -> 200 invoiceNumber",
          r.status_code == 200 and r.json()["data"]["invoiceNumber"] == "TEMA26-000100", r.text)

    r = c.get(f"/api/v1/invoices/{iid}/line-items", headers=h)
    check("invoice line-items -> 200 + 1", r.status_code == 200 and len(r.json()["data"]) == 1,
          r.text)

    r = c.get(f"/api/v1/invoices/{iid}/taxes", headers=h)
    check("invoice taxes -> 200 + 1", r.status_code ==
          200 and len(r.json()["data"]) == 1, r.text)

    # Step-3 seams: generation, exports and signed links are not built yet.
    r = c.post("/api/v1/invoices", headers=h,
               json={"eventId": f["event_id"], "recipient": {"city": "Aachen"},
                     "lineItems": [{"quantity": 1, "pricePerUnit": 10, "externalTaxId": "t1",
                                    "name": "X"}]})
    check("create invoice -> 501", r.status_code == 501, r.text)

    r = c.post("/api/v1/invoices/export", headers=h, json={"format": "xlsx"})
    check("export invoices -> 501", r.status_code == 501, r.text)

    r = c.post(f"/api/v1/invoices/{iid}/link",
               headers=h, json={"fileType": "pdf"})
    check("invoice link -> 501", r.status_code == 501, r.text)

    # Validation: lineItems is required.
    r = c.post("/api/v1/invoices", headers=h, json={"recipient": {}})
    check("create invoice missing lineItems -> 422",
          r.status_code == 422, r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
