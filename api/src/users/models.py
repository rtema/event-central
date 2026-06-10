"""User-domain models (tag: Users).

Tables
------
* ``users``             — the account record (soft-deletable).
* ``user_auth``         — append-only auth methods (never updated, only
                          created/soft-deleted, preserving an audit trail).
* ``user_scopes``       — append-only scope grants (soft-deleted when revoked).
* ``user_history``      — one row per change to the basic user fields.
* ``user_data``         — append-only arbitrary per-user data; the most recent
                          row is the "current" data and the full set is its
                          history (serves both /data and /data/history).
"""

from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.db import Base
from src.core.models import (
    CreatedAtMixin,
    CreatedByMixin,
    DeletedAtMixin,
    DeletedByMixin,
    UUIDType,
    uuid_pk,
)

# Enumerations from the OpenAPI spec.
USER_AUTH_METHODS = ("api-token", "password",
                     "backup-code", "passwordless", "otp")
USER_AUTH_CREATED_REASONS = ("user-request", "password-reset", "admin-request")
USER_AUTH_DELETED_REASONS = ("user-request", "password-reset",
                             "admin-request", "code-used")


class User(Base, CreatedAtMixin, DeletedAtMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()

    # Basic user data
    email: Mapped[str] = mapped_column(String(320), nullable=True, index=True)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    salutation: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str] = mapped_column(String(128), nullable=False)
    last_name: Mapped[str] = mapped_column(String(128), nullable=False)

    # Relationships
    auth_methods: Mapped[list[UserAuth]] = relationship(
        back_populates="user", lazy="selectin")
    scopes: Mapped[list[UserScope]] = relationship(
        back_populates="user", lazy="selectin")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()


class UserAuth(Base, CreatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    __tablename__ = "user_auth"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Auth Method, currently allowed are:
    # See USER_AUTH_METHODS above
    method: Mapped[str] = mapped_column(String(32), nullable=False)

    # Hash for password, api-token, backup-code
    # Raw shared secret for otp (TOTP)
    # Bound email/phone for passwordless
    secret: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # save the reasons e. g. code-used when a backup code is no longer valid
    # See USER_AUTH_CREATED_REASONS and USER_AUTH_DELETED_REASONS above
    created_reason: Mapped[str | None] = mapped_column(
        String(32), nullable=True)
    deleted_reason: Mapped[str | None] = mapped_column(
        String(32), nullable=True)

    # Relationships
    user: Mapped[User] = relationship(back_populates="auth_methods")


class UserScope(Base, CreatedAtMixin, CreatedByMixin, DeletedAtMixin, DeletedByMixin):
    __tablename__ = "user_scopes"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    scope: Mapped[str] = mapped_column(String(128), nullable=False)

    # Relationships
    user: Mapped[User] = relationship(back_populates="scopes")


class UserHistory(Base, CreatedAtMixin, CreatedByMixin):
    """One row per change to the basic user fields."""

    __tablename__ = "user_history"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # new state
    new_state: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)


class UserData(Base, CreatedAtMixin, CreatedByMixin):
    """One row per change to the arbitrary user fields."""

    __tablename__ = "user_data_history"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Arbitrary data as object of str -> str
    data: Mapped[dict[str, str]] = mapped_column(
        JSONB, nullable=False, default=dict)
