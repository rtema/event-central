"""Smoke test for the Misc endpoints (tag: Misc): /taxes and /scopes.

Seeds an admin (backend:read) and a scope-limited user to also assert that the
backend-scoped routes reject insufficient tokens.
Run with ``PYTHONPATH=. python scripts/smoke_misc.py`` or ``python -m src smoke``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.auth.service import issue_token_pair
from src.core.db import SessionLocal
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
        admin = User(email=f"misc-admin-{uuid.uuid4().hex[:8]}@example.com",
                     first_name="Misc", last_name="Admin")
        db.add(admin)
        db.flush()
        db.add(UserScope(user_id=admin.id, scope="backend:read", created_by="smoke"))

        limited = User(email=f"misc-lim-{uuid.uuid4().hex[:8]}@example.com",
                       first_name="Lim", last_name="Ited")
        db.add(limited)
        db.flush()
        db.add(UserScope(user_id=limited.id,
               scope="events:read:all", created_by="smoke"))
        db.flush()

        token = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke"
        ).access_token
        limited_token = issue_token_pair(
            db, user=limited, requested_scope=None, client_id="smoke"
        ).access_token
        ids = {"token": token, "limited_token": limited_token}
        db.commit()
        return ids


def main() -> int:
    f = seed()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {f['token']}"}
    lh = {"Authorization": f"Bearer {f['limited_token']}"}

    check("taxes without token -> 401",
          c.get("/api/v1/taxes").status_code == 401)
    check("limited user hits /taxes (backend:read) -> 403",
          c.get("/api/v1/taxes", headers=lh).status_code == 403)

    r = c.get("/api/v1/taxes", headers=h)
    check("misc taxes -> 200 + pagination", r.status_code == 200 and "pagination" in r.json(),
          r.text)

    r = c.get("/api/v1/scopes", headers=h)
    scopes: Any = r.json().get("data", []) if r.status_code == 200 else []
    check("misc scopes -> 200 + 29", r.status_code ==
          200 and len(scopes) == 29, r.text)
    check("scope entry has label", bool(scopes and scopes[0]["label"]), r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
