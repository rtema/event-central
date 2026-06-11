"""User-domain API schemas (camelCase JSON, tag: Users)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Any, Literal

from pydantic import EmailStr

from src.core.schemas import CamelModel

AuthMethod = Literal["api-token", "password",
                     "backup-code", "passwordless", "otp"]


# --------------------------------------------------------------------------- #
# User
# --------------------------------------------------------------------------- #
class UserOut(CamelModel):
    id: uuid.UUID
    email: EmailStr
    title: str | None = None
    salutation: str | None = None
    first_name: str
    last_name: str
    created_at: dt.datetime
    deleted_at: dt.datetime | None = None


class UserResponse(CamelModel):
    data: UserOut


class UsersListResponse(CamelModel):
    data: list[UserOut]


class UsersCreateRequest(CamelModel):
    email: EmailStr
    title: str | None = None
    salutation: str | None = None
    first_name: str
    last_name: str


class UserUpdateRequest(CamelModel):
    email: EmailStr | None = None
    title: str | None = None
    salutation: str | None = None
    first_name: str | None = None
    last_name: str | None = None


# --------------------------------------------------------------------------- #
# User history
# --------------------------------------------------------------------------- #
class UserHistoryItem(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: dt.datetime
    created_by: str | None = None
    new_state: dict[str, Any]


class UserHistoryResponse(CamelModel):
    data: list[UserHistoryItem]


# --------------------------------------------------------------------------- #
# User auth methods
# --------------------------------------------------------------------------- #
class UserAuthOut(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    method: AuthMethod
    # Visible only on creation for api-token/backup-code/otp, always for
    # passwordless (the bound email/phone), never for password.
    secret: str | None = None
    created_by: str | None = None
    created_reason: str | None = None
    deleted_by: str | None = None
    deleted_reason: str | None = None
    created_at: dt.datetime
    deleted_at: dt.datetime | None = None


class UserAuthListResponse(CamelModel):
    data: list[UserAuthOut]


class UserAuthCreateRequest(CamelModel):
    method: AuthMethod
    # Required for the password method; ignored for generated methods.
    secret: str | None = None


# --------------------------------------------------------------------------- #
# User scopes
# --------------------------------------------------------------------------- #
class UserScopeOut(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    scope: str
    created_by: str | None = None
    deleted_by: str | None = None
    created_at: dt.datetime
    deleted_at: dt.datetime | None = None


class UserScopesListResponse(CamelModel):
    data: list[UserScopeOut]


class UserScopesUpdateRequest(CamelModel):
    scopes: list[str]


# --------------------------------------------------------------------------- #
# Arbitrary user data
# --------------------------------------------------------------------------- #
class UserDataOut(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: dt.datetime
    created_by: str | None = None
    data: dict[str, str]


class UserDataHistoryItemOut(CamelModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: dt.datetime
    created_by: str | None = None
    new_state: dict[str, str]


class UserDataHistoryResponse(CamelModel):
    data: list[UserDataHistoryItemOut]
