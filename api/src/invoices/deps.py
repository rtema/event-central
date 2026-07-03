"""Authorization guard for invoice-scoped routes.

Resolves the spec's ``invoices:<action>:all`` / ``:own`` / ``:{eventId}``
alternatives against a concrete invoice: ``:all`` always passes, ``:{eventId}``
matches the invoice's event, and ``:own`` matches when the caller created it.
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, get_authenticated_actor
from src.core import scopes as scope_utils
from src.core.deps import get_db
from src.core.errors import ForbiddenError
from src.invoices.service import get_invoice


def require_invoice_scope(action: str):
    """Dependency factory for routes carrying an ``invoice_id`` path parameter."""

    def _dep(
        invoice_id: uuid.UUID,
        db: Session = Depends(get_db),
        authenticated_actor: AuthenticatedActor = Depends(get_authenticated_actor),
    ) -> AuthenticatedActor:
        invoice = get_invoice(db, invoice_id)  # 404 if unknown
        granted = authenticated_actor.scopes

        all_scope = scope_utils.build_scope("invoices", action, "all")
        event_scope = scope_utils.build_scope("invoices", action, invoice.order.event_id)
        own_scope = f"invoices:{action}:own"

        allowed = scope_utils.has_any(granted, [all_scope, event_scope]) or (
            scope_utils.has_scope(granted, own_scope)
            and invoice.created_by == authenticated_actor.sub
        )
        if not allowed:
            raise ForbiddenError(
                f"missing required scope for invoice {invoice_id}",
                error="insufficient_scope",
            )
        return authenticated_actor

    return _dep
