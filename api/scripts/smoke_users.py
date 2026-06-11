"""End-to-end smoke test for the Users endpoints.

Seeds an admin with users:read/write scopes, mints an access token, then
drives every /api/v1/users endpoint via the FastAPI app against real Postgres.
Run with: PYTHONPATH=. python scripts/smoke_users.py
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
    _passed += condition
    _failed += not condition
    print(f"[{mark}] {label}" +
          (f" :: {detail}" if detail and not condition else ""))


def seed_admin() -> str:
    """Create an admin user with read/write scopes and return an access token."""
    with SessionLocal() as db:
        admin = User(
            email=f"admin-{uuid.uuid4().hex[:8]}@example.com",
            first_name="Admin",
            last_name="User",
        )
        db.add(admin)
        db.flush()
        for scope in ["users:read:all", "users:write:all"]:
            db.add(UserScope(user_id=admin.id, scope=scope, created_by="system"))
        db.flush()
        tokens = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke")
        db.commit()
        return tokens.access_token


def main() -> int:
    token = seed_admin()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {token}"}

    # No auth -> 401
    check("list without token -> 401", c.get("/api/v1/users").status_code == 401)

    # Create
    email = f"u-{uuid.uuid4().hex[:8]}@example.com"
    r = c.post(
        "/api/v1/users",
        headers=h,
        json={"email": email, "firstName": "Grace",
              "lastName": "Hopper", "title": "Dr"},
    )
    check("create user -> 201", r.status_code == 201, r.text)
    body = r.json()
    check("create returns camelCase", "firstName" in body["data"], body)
    uid = body["data"]["id"]

    # Get
    r = c.get(f"/api/v1/users/{uid}", headers=h)
    check("get user -> 200", r.status_code ==
          200 and r.json()["data"]["email"] == email, r.text)

    # List
    r = c.get("/api/v1/users", headers=h)
    check(
        "list users -> 200", r.status_code == 200 and any(
            u["id"] == uid for u in r.json()["data"])
    )

    # Update (POST)
    r = c.post(f"/api/v1/users/{uid}", headers=h,
               json={"lastName": "Hopper-Murray"})
    check(
        "update user -> 200",
        r.status_code == 200 and r.json(
        )["data"]["lastName"] == "Hopper-Murray",
        r.text,
    )

    # History reflects create + update
    r = c.get(f"/api/v1/users/{uid}/history", headers=h)
    check("history >= 2 entries", r.status_code ==
          200 and len(r.json()["data"]) >= 2, r.text)
    check(
        "history newState camel", r.json()["data"][0]["newState"].get(
            "lastName") == "Hopper-Murray"
    )

    # --- Auth methods ---
    r = c.post(f"/api/v1/users/{uid}/auth",
               headers=h, json={"method": "api-token"})
    check("create api-token -> 200", r.status_code == 200, r.text)
    check("api-token secret shown once", bool(r.json().get("secret")), r.text)
    auth_id = r.json()["id"]

    r = c.post(
        f"/api/v1/users/{uid}/auth",
        headers=h,
        json={"method": "password", "secret": "hunter2hunter2"},
    )
    check(
        "create password (secret hidden)",
        r.status_code == 200 and r.json().get("secret") is None,
        r.text,
    )

    r = c.get(f"/api/v1/users/{uid}/auth/{auth_id}", headers=h)
    check("get auth hides secret", r.status_code ==
          200 and r.json().get("secret") is None, r.text)

    r = c.get(f"/api/v1/users/{uid}/auth", headers=h)
    check("list auth -> 2 methods", r.status_code ==
          200 and len(r.json()["data"]) == 2, r.text)

    r = c.delete(f"/api/v1/users/{uid}/auth/{auth_id}", headers=h)
    check(
        "delete auth -> soft-deleted",
        r.status_code == 200 and r.json()["deletedAt"] is not None,
        r.text,
    )

    # --- Scopes ---
    r = c.post(
        f"/api/v1/users/{uid}/scopes",
        headers=h,
        json={"scopes": ["events:read:all", "orders:read:all"]},
    )
    check("set scopes -> 200", r.status_code == 200, r.text)
    active = [s for s in r.json()["data"] if s["deletedAt"] is None]
    check("two active scopes", len(active) == 2, r.text)

    # Reconcile: drop one, add one
    r = c.post(
        f"/api/v1/users/{uid}/scopes",
        headers=h,
        json={"scopes": ["events:read:all", "payments:read:all"]},
    )
    data = r.json()["data"]
    active = {s["scope"] for s in data if s["deletedAt"] is None}
    revoked = {s["scope"] for s in data if s["deletedAt"] is not None}
    check("reconcile active set", active == {
          "events:read:all", "payments:read:all"}, str(active))
    check("reconcile revoked orders", "orders:read:all" in revoked, str(revoked))

    # --- Arbitrary data ---
    r = c.get(f"/api/v1/users/{uid}/data", headers=h)
    check("empty data -> {}", r.status_code ==
          200 and r.json()["data"] == {}, r.text)

    r = c.post(f"/api/v1/users/{uid}/data",
               headers=h, json={"theme": "dark", "n": "1"})
    check(
        "set data v1 -> 200", r.status_code == 200 and r.json()[
            "data"]["theme"] == "dark", r.text
    )

    r = c.post(f"/api/v1/users/{uid}/data", headers=h, json={"theme": "light"})
    check(
        "set data v2 -> 200",
        r.status_code == 200 and r.json()["data"] == {"theme": "light"},
        r.text,
    )

    r = c.get(f"/api/v1/users/{uid}/data", headers=h)
    check("current data = latest", r.json()[
          "data"] == {"theme": "light"}, r.text)

    r = c.get(f"/api/v1/users/{uid}/data/history", headers=h)
    check("data history -> 2 entries", r.status_code ==
          200 and len(r.json()["data"]) == 2, r.text)

    # --- Delete + restore ---
    r = c.delete(f"/api/v1/users/{uid}", headers=h)
    check(
        "delete user -> deletedAt set",
        r.status_code == 200 and r.json()["data"]["deletedAt"] is not None,
        r.text,
    )

    r = c.post(f"/api/v1/users/{uid}/restore", headers=h)
    check(
        "restore user -> deletedAt null",
        r.status_code == 200 and r.json()["data"]["deletedAt"] is None,
        r.text,
    )

    # 404 for unknown user
    check(
        "unknown user -> 404", c.get(
            f"/api/v1/users/{uuid.uuid4()}", headers=h).status_code == 404
    )

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
