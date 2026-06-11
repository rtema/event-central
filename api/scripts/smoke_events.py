"""Smoke test for the Events endpoints (tag: Events).

Seeds one event with a single order under it, then exercises the event list,
event detail and the per-event orders route. Self-contained: run directly with
``PYTHONPATH=. python scripts/smoke_events.py`` or via ``python -m src smoke``.
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
        admin = User(email=f"ev-admin-{uuid.uuid4().hex[:8]}@example.com",
                     first_name="Ev", last_name="Admin")
        db.add(admin)
        db.flush()
        for scope in ("events:read:all", "orders:read:all"):
            db.add(UserScope(user_id=admin.id, scope=scope, created_by="smoke"))
        db.flush()

        event = Event(id=f"ev-{uuid.uuid4().hex[:8]}", label={"de": "Messe", "en": "Fair"},
                      created_by="smoke")
        db.add(event)
        db.flush()
        db.add(Order(event_id=event.id, external_id=f"ord-{uuid.uuid4().hex[:6]}",
                     status="open", created_by="smoke"))

        token = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke"
        ).access_token
        ids = {"token": token, "event_id": event.id}
        db.commit()
        return ids


def main() -> int:
    f = seed()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {f['token']}"}

    check("list events without token -> 401",
          c.get("/api/v1/events").status_code == 401)

    r = c.get("/api/v1/events", headers=h)
    check("list events -> 200 + pagination", r.status_code == 200 and "pagination" in r.json(),
          r.text)
    check("events pagination camelCase",
          "currentOffset" in r.json()["pagination"], r.text)

    r = c.get(f"/api/v1/events/{f['event_id']}", headers=h)
    check("get event -> 200 + label", r.status_code == 200 and
          r.json()["data"]["label"]["en"] == "Fair", r.text)

    r = c.get(f"/api/v1/events/{f['event_id']}/orders", headers=h)
    check("event orders -> 200 + 1 order", r.status_code == 200 and len(r.json()["data"]) == 1,
          r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
