"""Smoke test for the Orders endpoints (tags: Orders, Payments, Invoicing).

Covers the order list/detail, the order-scoped payment list + create, the
order-scoped invoice list, and order cancellation (a step-3 seam returning 501).
Run with ``PYTHONPATH=. python scripts/smoke_orders.py`` or ``python -m src smoke``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.auth.service import issue_token_pair
from src.core.db import SessionLocal
from src.events.models import Event
from src.invoices.models import Invoice
from src.orders.models import Order
from src.payments.models import Payment
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
        admin = User(email=f"ord-admin-{uuid.uuid4().hex[:8]}@example.com",
                     first_name="Ord", last_name="Admin")
        db.add(admin)
        db.flush()
        for scope in ("orders:read:all", "orders:write:all",
                      "payments:read:all", "payments:write:all", "invoices:read:all"):
            db.add(UserScope(user_id=admin.id, scope=scope, created_by="smoke"))
        db.flush()

        event = Event(
            id=f"ev-{uuid.uuid4().hex[:8]}", label={"en": "Fair"}, created_by="smoke")
        db.add(event)
        db.flush()
        order = Order(event_id=event.id, external_id=f"ord-{uuid.uuid4().hex[:6]}",
                      status="open", recipient={"city": "Aachen"}, created_by="smoke")
        db.add(order)
        db.flush()
        db.add(Invoice(order_id=order.id, event_id=event.id, currency="EUR",
                       invoice_number=f"INV-{uuid.uuid4().hex[:6]}", created_by="smoke"))
        db.add(Payment(order_id=order.id, external_id=f"pay-{uuid.uuid4().hex[:6]}",
                       provider="PayOne", type="payment", amount=119, currency="EUR",
                       created_by="smoke"))

        token = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke"
        ).access_token
        ids = {"token": token, "order_id": str(order.id)}
        db.commit()
        return ids


def main() -> int:
    f = seed()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {f['token']}"}
    oid = f["order_id"]

    check("list orders without token -> 401",
          c.get("/api/v1/orders").status_code == 401)

    r = c.get("/api/v1/orders", headers=h)
    check("list orders -> 200", r.status_code ==
          200 and len(r.json()["data"]) >= 1, r.text)

    r = c.get(f"/api/v1/orders/{oid}", headers=h)
    check("get order -> 200 camel eventId", r.status_code == 200 and "eventId" in r.json()["data"],
          r.text)

    r = c.get(f"/api/v1/orders/{oid}/payments", headers=h)
    check("order payments -> 200 + 1", r.status_code ==
          200 and len(r.json()["data"]) == 1, r.text)

    r = c.post(f"/api/v1/orders/{oid}/payments", headers=h,
               json={"amount": 50, "type": "refund", "provider": "PayOne", "currency": "EUR"})
    check("create order payment -> 201", r.status_code == 201 and
          r.json()["data"]["type"] == "refund", r.text)

    r = c.get(f"/api/v1/orders/{oid}/invoices", headers=h)
    check("order invoices -> 200 + 1", r.status_code ==
          200 and len(r.json()["data"]) == 1, r.text)

    r = c.delete(f"/api/v1/orders/{oid}", headers=h)
    check("cancel order -> 501", r.status_code == 501, r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
