"""Authorization guard for order-scoped routes.

The order-scoped routes authorize against the *event* the order belongs to
(e.g. ``payments:read:{eventId}``), but the event id isn't in the URL — it's a
property of the order. This guard loads the order, resolves its event and
performs the precise per-event scope check, accepting the broader ``:all``
grant as well.
"""

from __future__ import annotations

import uuid

from fastapi import Depends
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, get_authenticated_actor
from src.core import scopes as scope_utils
from src.core.deps import get_db
from src.core.errors import ForbiddenError
from src.orders.service import get_order


def require_order_scope(resource: str, action: str):
    """Dependency factory for routes carrying an ``order_id`` path parameter."""

    def _dep(
        order_id: uuid.UUID,
        db: Session = Depends(get_db),
        authenticated_actor: AuthenticatedActor = Depends(get_authenticated_actor),
    ) -> AuthenticatedActor:
        order = get_order(db, order_id)  # 404 if the order is unknown
        required = [
            scope_utils.build_scope(resource, action, "all"),
            scope_utils.build_scope(resource, action, order.event_id),
        ]
        if not scope_utils.has_any(authenticated_actor.scopes, required):
            raise ForbiddenError(
                f"missing required scope: {resource}:{action}:{order.event_id}",
                error="insufficient_scope",
            )
        return authenticated_actor

    return _dep
