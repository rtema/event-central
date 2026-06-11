"""End-to-end smoke test for the Step 1 auth surface.

Seeds a user directly, then drives every /auth endpoint through the FastAPI
app using a real PostgreSQL database. Run with: python scripts/smoke_auth.py
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.core.db import SessionLocal
from src.core.security import generate_api_token, hash_secret
from src.services.web import app
from src.users.models import User, UserAuth, UserScope

PASSWORD = "correct horse battery staple"
EMAIL = f"smoke-{uuid.uuid4().hex[:8]}@example.com"

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


def seed() -> tuple[uuid.UUID, str]:
    with SessionLocal() as db:
        user = User(email=EMAIL, first_name="Smoke", last_name="Tester")
        db.add(user)
        db.flush()
        db.add(
            UserAuth(
                user_id=user.id,
                method="password",
                secret=hash_secret(PASSWORD),
                created_by="system",
                created_reason="admin-request",
            )
        )
        api_token = generate_api_token()
        db.add(
            UserAuth(
                user_id=user.id,
                method="api-token",
                secret=hash_secret(api_token),
                created_by="system",
                created_reason="admin-request",
            )
        )
        for scope in ["invoices:read:all", "invoices:write:all", "users:read:all"]:
            db.add(UserScope(user_id=user.id, scope=scope, created_by="system"))
        db.commit()
        return user.id, api_token


def main() -> int:
    user_id, api_token = seed()
    client: Any = TestClient(app)

    # 1. Health
    check("health", client.get("/health").json()["status"] == "ok")

    # 2. Password grant
    r = client.post(
        "/auth/token",
        json={
            "grant_type": "password",
            "username": EMAIL,
            "password": PASSWORD,
            "scope": "invoices:read:all",
        },
    )
    check("password grant -> 200", r.status_code == 200, r.text)
    tok = r.json()
    check("access_token present", bool(tok.get("access_token")))
    check("refresh_token present", bool(tok.get("refresh_token")))
    check("granted scope narrowed", tok.get("scope")
          == "invoices:read:all", tok.get("scope"))
    access, refresh = tok["access_token"], tok["refresh_token"]

    # 3. Wrong password
    r = client.post(
        "/auth/token",
        json={"grant_type": "password", "username": EMAIL, "password": "nope"},
    )
    check("wrong password -> 401", r.status_code == 401, r.text)
    check("auth error shape", r.json().get("error") == "invalid_grant")

    # 4. userinfo with access token
    r = client.get("/auth/userinfo",
                   headers={"Authorization": f"Bearer {access}"})
    check("userinfo -> 200", r.status_code == 200, r.text)
    check("userinfo sub", r.json().get("sub") == f"user:{user_id}")
    check("userinfo email", r.json().get("email") == EMAIL)

    # 5. userinfo without token
    check("userinfo no token -> 401",
          client.get("/auth/userinfo").status_code == 401)

    # 6. userinfo with API token (opaque long-lived credential)
    r = client.get("/auth/userinfo",
                   headers={"Authorization": f"Bearer {api_token}"})
    check("api-token auth -> 200", r.status_code == 200, r.text)

    # 7. Refresh grant rotates token
    r = client.post(
        "/auth/token", json={"grant_type": "refresh_token", "refresh_token": refresh})
    check("refresh grant -> 200", r.status_code == 200, r.text)
    new_refresh = r.json()["refresh_token"]
    check("refresh rotated", new_refresh != refresh)

    # 8. Old refresh token now rejected (rotation revokes it)
    r = client.post(
        "/auth/token", json={"grant_type": "refresh_token", "refresh_token": refresh})
    check("reused refresh -> 401", r.status_code == 401, r.text)

    # 9. Revoke the new refresh token (logout)
    r = client.post("/auth/revoke", json={"token": new_refresh})
    check("revoke -> 200", r.status_code == 200, r.text)
    r = client.post(
        "/auth/token", json={"grant_type": "refresh_token", "refresh_token": new_refresh}
    )
    check("revoked refresh -> 401", r.status_code == 401, r.text)

    # 10. Passwordless start is opaque
    r = client.post(
        "/auth/passwordless/start",
        json={
            "connection": "email",
            "email": EMAIL,
            "send": "code",
            "authParams": {"scope": "invoices:read:all", "locale": "de"},
        },
    )
    check("passwordless start -> 200 ok", r.status_code ==
          200 and r.json()["ok"] is True, r.text)

    # 11. Password reset full flow
    r = client.post(
        "/auth/password-reset/start",
        json={"email": EMAIL,
              "redirectUri": "https://app.example/reset", "locale": "de"},
    )
    check("reset start -> ok", r.status_code ==
          200 and r.json()["ok"] is True, r.text)

    # Fetch the code straight from the challenge row (delivery is stubbed).
    r = client.post(
        "/auth/password-reset/confirm",
        json={"email": EMAIL, "code": "000000",
              "password": "brand new password 1"},
    )
    check("reset confirm wrong code -> 400", r.status_code == 400, r.text)

    # Happy path: drive create_challenge directly to obtain the plaintext code
    # (email/SMS delivery is stubbed in Step 1).
    from src.auth import service as auth_service

    with SessionLocal() as db:
        code = auth_service.create_challenge(
            db, destination=EMAIL, purpose="password-reset", channel="email"
        )
        db.commit()
    new_password = "brand new password 1"
    r = client.post(
        "/auth/password-reset/confirm",
        json={"email": EMAIL, "code": code, "password": new_password},
    )
    check("reset confirm -> ok", r.status_code ==
          200 and r.json()["ok"] is True, r.text)

    # 12. Old password fails, new password works
    r = client.post(
        "/auth/token", json={"grant_type": "password", "username": EMAIL, "password": PASSWORD}
    )
    check("old password -> 401", r.status_code == 401, r.text)
    r = client.post(
        "/auth/token",
        json={"grant_type": "password",
              "username": EMAIL, "password": new_password},
    )
    check("new password -> 200", r.status_code == 200, r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
