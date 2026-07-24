"""User-domain business logic (tag: Users), decoupled from HTTP."""

from __future__ import annotations

import datetime as dt
import uuid
from collections.abc import Sequence
from typing import Any

from sqlalchemy import ColumnElement, Select, func, or_, select
from sqlalchemy.orm import InstrumentedAttribute, Session

from src.auth import service as auth_service
from src.core.errors import AppError, NotFoundError
from src.core.security import (
    generate_api_token,
    generate_backup_code,
    generate_otp_secret,
    hash_secret,
)
from src.users.models import User, UserAuth, UserData, UserHistory, UserScope
from src.users.schemas import UserSearchParams


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _user_snapshot(user: User) -> dict[str, Any]:
    """The new-state snapshot stored in user_history (camelCase, API-shaped)."""
    return {
        "email": user.email,
        "title": user.title,
        "salutation": user.salutation,
        "firstName": user.first_name,
        "lastName": user.last_name,
    }


def _record_history(db: Session, user: User, actor: str | None) -> None:
    db.add(UserHistory(user_id=user.id, created_by=actor,
           new_state=_user_snapshot(user)))


# --------------------------------------------------------------------------- #
# Users CRUD
# --------------------------------------------------------------------------- #
def list_users(
    db: Session,
        *,
        limit: int,
        offset: int,
        include_deleted: bool = False,
) -> tuple[list[User], int]:
    """Return a page of users (newest first) and the total count."""
    base = select(User)
    count_stmt = select(func.count()).select_from(User)
    if not include_deleted:
        base = base.where(User.deleted_at.is_(None))
        count_stmt = count_stmt.where(User.deleted_at.is_(None))

    total = db.execute(count_stmt).scalar_one()
    stmt = base.order_by(User.created_at.desc()).limit(limit).offset(offset)
    return list(db.execute(stmt).scalars().all()), total


def search_users(
    db: Session,
    *,
    limit: int,
    offset: int,
    search_params: UserSearchParams,
    include_deleted: bool = False,
) -> tuple[list[User], int]:
    """Return a page of files (newest first) and the total count."""
    conditions: list[ColumnElement[bool]] = []

    if not include_deleted:
        conditions.append(User.deleted_at.is_(None))

    # filters
    filters: list[tuple[InstrumentedAttribute[Any], Sequence[Any] | None]] = [
        (User.title, search_params.title),
        (User.salutation, search_params.salutation),
    ]
    for column, values in filters:
        if values:
            conditions.append(column.in_(values))

    # special values
    # Currently not implemented

    # text filters
    if search_params.q and search_params.q.strip():
        term: str = search_params.q.strip()
        # escape LIKE wildcards so user input is matched literally
        escaped: str = (
            term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        )
        pattern: str = f"%{escaped}%"
        conditions.append(
            or_(
                User.email.ilike(pattern, escape="\\"),
                User.first_name.ilike(pattern, escape="\\"),
                User.last_name.ilike(pattern, escape="\\"),
            )
        )

    # count total
    count_stmt: Select[tuple[int]] = (
        select(func.count()).select_from(User).where(*conditions)
    )
    total: int = db.execute(count_stmt).scalar_one()

    # build statement
    stmt = (
        select(User)
        .where(*conditions)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(db.execute(stmt).scalars().all()), total


def get_user(db: Session, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise NotFoundError("user not found")
    return user


def create_user(
    db: Session,
    *,
    email: str,
    first_name: str,
    last_name: str,
    title: str | None,
    salutation: str | None,
    actor: str | None,
) -> User:
    user = User(
        email=email,
        first_name=first_name,
        last_name=last_name,
        title=title,
        salutation=salutation,
    )
    db.add(user)
    db.flush()
    _record_history(db, user, actor)
    return user


def update_user(
    db: Session, user_id: uuid.UUID, *, changes: dict[str, Any], actor: str | None
) -> User:
    user = get_user(db, user_id)
    field_map = {
        "email": "email",
        "title": "title",
        "salutation": "salutation",
        "first_name": "first_name",
        "last_name": "last_name",
    }
    for key, attr in field_map.items():
        if key in changes and changes[key] is not None:
            setattr(user, attr, changes[key])
    db.flush()
    _record_history(db, user, actor)
    return user


def delete_user(db: Session, user_id: uuid.UUID, *, actor: str | None) -> User:
    user = get_user(db, user_id)
    if user.deleted_at is None:
        user.deleted_at = _now()
        db.flush()
        _record_history(db, user, actor)
        # Invalidate any active sessions for the deleted account.
        auth_service.revoke_all_for_user(db, user.id)
    return user


def restore_user(db: Session, user_id: uuid.UUID, *, actor: str | None) -> User:
    user = get_user(db, user_id)
    if user.deleted_at is not None:
        user.deleted_at = None
        db.flush()
        _record_history(db, user, actor)
    return user


def get_user_history(db: Session, user_id: uuid.UUID) -> list[UserHistory]:
    get_user(db, user_id)  # 404 if missing
    stmt = (
        select(UserHistory)
        .where(UserHistory.user_id == user_id)
        .order_by(UserHistory.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


# --------------------------------------------------------------------------- #
# User auth methods (append-only)
# --------------------------------------------------------------------------- #
def list_user_auth(db: Session, user_id: uuid.UUID) -> list[UserAuth]:
    get_user(db, user_id)
    stmt = select(UserAuth).where(UserAuth.user_id ==
                                  user_id).order_by(UserAuth.created_at.desc())
    return list(db.execute(stmt).scalars().all())


def get_user_auth(db: Session, user_id: uuid.UUID, auth_id: uuid.UUID) -> UserAuth:
    auth = db.get(UserAuth, auth_id)
    if auth is None or auth.user_id != user_id:
        raise NotFoundError("auth method not found")
    return auth


def create_user_auth(
    db: Session,
    user_id: uuid.UUID,
    *,
    method: str,
    secret: str | None,
    actor: str | None,
) -> tuple[UserAuth, str | None]:
    """Create an auth method.

    Returns ``(record, visible_secret)`` where ``visible_secret`` is the value
    to show the caller once (api-token/backup-code/otp) or the bound identifier
    (passwordless). It is ``None`` for password.
    """
    user = get_user(db, user_id)

    visible: str | None = None
    stored: str | None = None

    if method == "password":
        if not secret:
            raise AppError("a secret is required for the password method")
        stored = hash_secret(secret)
        visible = None
    elif method == "api-token":
        token = generate_api_token()
        stored = hash_secret(token)
        visible = token
    elif method == "backup-code":
        code = generate_backup_code()
        stored = hash_secret(code)
        visible = code
    elif method == "otp":
        otp_secret = generate_otp_secret()
        stored = otp_secret  # raw: required to verify TOTP codes later
        visible = otp_secret
    elif method == "passwordless":
        # Bind to the provided identifier, or default to the user's email.
        bound = secret or user.email
        stored = bound
        visible = bound
    else:  # pragma: no cover - schema restricts method
        raise AppError(f"unsupported auth method: {method}")

    record = UserAuth(
        user_id=user_id,
        method=method,
        secret=stored,
        created_by=actor,
        created_reason="admin-request",
    )
    db.add(record)
    db.flush()
    return record, visible


def delete_user_auth(
    db: Session, user_id: uuid.UUID, auth_id: uuid.UUID, *, actor: str | None
) -> UserAuth:
    auth = get_user_auth(db, user_id, auth_id)
    if auth.deleted_at is None:
        auth.deleted_at = _now()
        auth.deleted_by = actor
        auth.deleted_reason = "admin-request"
        db.flush()
    return auth


# --------------------------------------------------------------------------- #
# User scopes (append-only, reconciled on update)
# --------------------------------------------------------------------------- #
def list_user_scopes(db: Session, user_id: uuid.UUID) -> list[UserScope]:
    get_user(db, user_id)
    stmt = (
        select(UserScope).where(UserScope.user_id ==
                                user_id).order_by(UserScope.created_at.desc())
    )
    return list(db.execute(stmt).scalars().all())


def set_user_scopes(
    db: Session, user_id: uuid.UUID, *, scopes: list[str], actor: str | None
) -> list[UserScope]:
    get_user(db, user_id)
    desired = set(scopes)

    active = {
        s.scope: s
        for s in db.execute(
            select(UserScope).where(UserScope.user_id ==
                                    user_id, UserScope.deleted_at.is_(None))
        ).scalars()
    }

    # Revoke scopes that are no longer desired.
    for scope, record in active.items():
        if scope not in desired:
            record.deleted_at = _now()
            record.deleted_by = actor

    # Grant newly desired scopes.
    for scope in desired - set(active):
        db.add(UserScope(user_id=user_id, scope=scope, created_by=actor))

    db.flush()
    return list_user_scopes(db, user_id)


# --------------------------------------------------------------------------- #
# Arbitrary user data (append-only; latest row is current)
# --------------------------------------------------------------------------- #
def get_user_data(db: Session, user_id: uuid.UUID) -> UserData | None:
    get_user(db, user_id)
    stmt = (
        select(UserData)
        .where(UserData.user_id == user_id)
        .order_by(UserData.created_at.desc())
        .limit(1)
    )
    return db.execute(stmt).scalars().first()


def set_user_data(
    db: Session, user_id: uuid.UUID, *, data: dict[str, Any], actor: str | None
) -> UserData:
    get_user(db, user_id)
    record = UserData(user_id=user_id, data=data, created_by=actor)
    db.add(record)
    db.flush()
    return record


def get_user_data_history(db: Session, user_id: uuid.UUID) -> list[UserData]:
    get_user(db, user_id)
    stmt = select(UserData).where(UserData.user_id ==
                                  user_id).order_by(UserData.created_at.desc())
    return list(db.execute(stmt).scalars().all())
