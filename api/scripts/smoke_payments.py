"""Smoke test for the Payments collection endpoint (tag: Payments).

Seeds an order with two payments, then exercises the cross-order payments list.
Run with ``PYTHONPATH=. python scripts/smoke_payments.py`` or ``python -m src smoke``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.auth.service import issue_token_pair
from src.core.db import SessionLocal
from src.events.models import Event
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
        admin = User(email=f"pay-admin-{uuid.uuid4().hex[:8]}@example.com",
                     first_name="Pay", last_name="Admin")
        db.add(admin)
        db.flush()
        db.add(UserScope(user_id=admin.id,
               scope="payments:read:all", created_by="smoke"))
        db.flush()

        event = Event(
            id=f"ev-{uuid.uuid4().hex[:8]}", label={"en": "Fair"}, created_by="smoke")
        db.add(event)
        db.flush()
        order = Order(event_id=event.id, external_id=f"ord-{uuid.uuid4().hex[:6]}",
                      status="open", created_by="smoke")
        db.add(order)
        db.flush()
        for kind in ("payment", "refund"):
            db.add(Payment(order_id=order.id, external_id=f"pay-{uuid.uuid4().hex[:6]}",
                           provider="PayOne", type=kind, amount=119, currency="EUR",
                           created_by="smoke"))

        token = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke"
        ).access_token
        ids = {"token": token}
        db.commit()
        return ids


def main() -> int:
    f = seed()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {f['token']}"}

    check("list payments without token -> 401",
          c.get("/api/v1/payments").status_code == 401)

    r = c.get("/api/v1/payments", headers=h)
    check("list payments -> 200 + total>=2",
          r.status_code == 200 and r.json()["pagination"]["total"] >= 2, r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
