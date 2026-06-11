"""Authentication dependencies: the Principal and scope guards.

These live in the auth feature because they implement authentication; other
features (e.g. users) import the guards from here.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from src.auth import service as auth_service
from src.core import scopes as scope_utils
from src.core.deps import get_db
from src.core.errors import AppError, ForbiddenError


@dataclass(slots=True)
class AuthenticatedActor:
    """The authenticated actor (a user  an app/API token)."""

    sub: str  # "user:<uuid>" or "app:<key>"
    scopes: set[str]
    client_id: str | None = None

    @property
    def user_id(self) -> uuid.UUID | None:
        if self.sub.startswith("user:"):
            try:
                return uuid.UUID(self.sub.split(":", 1)[1])
            except ValueError:
                return None
        return None


def _get_bearer_token(request: Request) -> str:
    header = request.headers.get("Authorization", "")
    scheme, _, credential = header.partition(" ")
    if scheme.lower() != "bearer" or not credential:
        raise AppError("missing bearer token",
                       error="missing_token", http_status=401)
    return credential.strip()


def get_authenticated_actor(request: Request, db: Session = Depends(get_db)) -> AuthenticatedActor:
    token = _get_bearer_token(request)
    sub, granted, client_id = auth_service.verify_access_token(db, token)
    return AuthenticatedActor(sub=sub, scopes=granted, client_id=client_id)


def require_all_scopes(*required: str):
    """Dependency factory: authenticated_actor must hold *all* the given scopes."""

    def _dep(authenticated_actor: AuthenticatedActor = Depends(
            get_authenticated_actor)) -> AuthenticatedActor:
        for scope in required:
            if not scope_utils.has_scope(authenticated_actor.scopes, scope):
                raise ForbiddenError(
                    f"missing required scope: {scope}", error="insufficient_scope")
        return authenticated_actor

    return _dep


def require_any_scope(*required: str):
    """Dependency factory: authenticated_actor must hold at least one of the scopes."""

    def _dep(authenticated_actor: AuthenticatedActor = Depends(get_authenticated_actor)
             ) -> AuthenticatedActor:
        if not scope_utils.has_any(authenticated_actor.scopes, list(required)):
            raise ForbiddenError(
                f"missing one of required scopes: {', '.join(required)}",
                error="insufficient_scope",
            )
        return authenticated_actor

    return _dep
