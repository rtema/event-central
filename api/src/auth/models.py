"""Authentication models (tag: Auth).

* ``refresh_tokens`` — server-side records of issued refresh tokens so they can
  be revoked (logout) and rotated. PostgreSQL is the source of truth here.
* ``auth_challenges`` — one-time codes for passwordless login / password reset.

The user-owned auth tables (``user_auth``, ``user_scopes``) live in the users
domain (src/users/models.py); this module only holds purely auth-session state.
"""

from __future__ import annotations

import datetime as dt
import uuid

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from src.core.db import Base
from src.core.models import CreatedAtMixin, TZDateTime, UUIDType, uuid_pk

AUTH_CHALLENGE_PURPOSES = ("passwordless", "password-reset")
AUTH_CHALLENGE_CHANNELS = ("email", "sms")


class RefreshToken(Base, CreatedAtMixin):
    __tablename__ = "refresh_tokens"

    # The token's jti claim is the primary key.
    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Token data
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope: Mapped[str] = mapped_column(
        String(2048), nullable=False, default="")

    # Timing
    expires_at: Mapped[dt.datetime] = mapped_column(TZDateTime, nullable=False)
    revoked_at: Mapped[dt.datetime | None] = mapped_column(
        TZDateTime, nullable=True, default=None)

    @property
    def is_active(self) -> bool:
        now = dt.datetime.now(dt.UTC)
        return self.revoked_at is None and self.expires_at > now


class AuthChallenge(Base, CreatedAtMixin):
    __tablename__ = "auth_challenges"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUIDType, ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=True
    )

    purpose: Mapped[str] = mapped_column(String(32), nullable=False)
    channel: Mapped[str | None] = mapped_column(String(16), nullable=True)
    destination: Mapped[str] = mapped_column(
        String(320), nullable=False, index=True)
    code_hash: Mapped[str] = mapped_column(String(512), nullable=False)
    client_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    scope: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    redirect_uri: Mapped[str | None] = mapped_column(
        String(2048), nullable=True)

    # Timing
    expires_at: Mapped[dt.datetime] = mapped_column(TZDateTime, nullable=False)
    consumed_at: Mapped[dt.datetime | None] = mapped_column(
        TZDateTime, nullable=True, default=None)

    @property
    def is_valid(self) -> bool:
        now = dt.datetime.now(dt.UTC)
        return self.consumed_at is None and self.expires_at > now
