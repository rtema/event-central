"""Smoke test for the Document Templates endpoints (tag: Document Templates).

Seeds a private + public template, then exercises the read routes plus the
public create / versioned update flow and its slug/duplicate validation.
Run with ``PYTHONPATH=. python scripts/smoke_templates.py`` or ``python -m src smoke``.
"""

from __future__ import annotations

import sys
import uuid
from typing import Any

from fastapi.testclient import TestClient
from src.auth.service import issue_token_pair
from src.core.db import SessionLocal
from src.document_templates.models import DocumentTemplate, PublicDocumentTemplate
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
        admin = User(email=f"tmpl-admin-{uuid.uuid4().hex[:8]}@example.com",
                     first_name="Tmpl", last_name="Admin")
        db.add(admin)
        db.flush()
        for scope in ("backend:read", "backend:write"):
            db.add(UserScope(user_id=admin.id, scope=scope, created_by="smoke"))
        db.flush()

        dt = DocumentTemplate(html="<h1>{{ invoice.invoiceNumber }}</h1>", css="h1{color:#000}",
                              created_by="smoke")
        db.add(dt)
        db.flush()
        public = PublicDocumentTemplate(id=f"tmpl-{uuid.uuid4().hex[:6]}",
                                        document_template_id=dt.id, label={"en": "Default"})
        db.add(public)
        dt.public_document_template_id = public.id

        token = issue_token_pair(
            db, user=admin, requested_scope=None, client_id="smoke"
        ).access_token
        ids = {"token": token, "document_template_id": str(
            dt.id), "public_id": public.id}
        db.commit()
        return ids


def main() -> int:
    f = seed()
    c: Any = TestClient(app)
    h = {"Authorization": f"Bearer {f['token']}"}

    check("list templates without token -> 401",
          c.get("/api/v1/document-templates").status_code == 401)

    r = c.get("/api/v1/document-templates", headers=h)
    check("list document-templates -> 200", r.status_code == 200 and len(r.json()["data"]) >= 1,
          r.text)

    r = c.get(
        f"/api/v1/document-templates/{f['document_template_id']}", headers=h)
    check("get document-template -> 200", r.status_code == 200, r.text)

    r = c.get("/api/v1/document-templates/public", headers=h)
    check("list public templates -> 200", r.status_code == 200 and len(r.json()["data"]) >= 1,
          r.text)

    r = c.get(f"/api/v1/document-templates/public/{f['public_id']}", headers=h)
    check("get public template -> 200", r.status_code == 200, r.text)

    new_slug = f"created-{uuid.uuid4().hex[:6]}"
    r = c.post("/api/v1/document-templates/public", headers=h,
               json={"id": new_slug, "html": "<p>hi</p>", "css": "p{}"})
    check("create public template -> 201",
          r.status_code == 201 and r.json()["data"]["id"] == new_slug, r.text)
    first_tmpl = r.json()["data"]["documentTemplateId"]

    r = c.post(f"/api/v1/document-templates/public/{new_slug}", headers=h,
               json={"html": "<p>v2</p>"})
    check("update public template repoints version",
          r.status_code == 200 and r.json()["data"]["documentTemplateId"] != first_tmpl, r.text)

    r = c.post("/api/v1/document-templates/public", headers=h,
               json={"id": "Bad Slug!", "html": "x"})
    check("invalid slug -> 400", r.status_code == 400, r.text)

    r = c.post("/api/v1/document-templates/public",
               headers=h, json={"id": new_slug})
    check("duplicate public slug -> 409", r.status_code == 409, r.text)

    print(f"\n{_passed} passed, {_failed} failed")
    return 1 if _failed else 0


if __name__ == "__main__":
    sys.exit(main())
