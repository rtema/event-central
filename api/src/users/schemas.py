"""User-domain API schemas (camelCase JSON, tag: Users)."""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated, Any, Literal

from pydantic import BeforeValidator, EmailStr, Field

from src.core.schemas import CamelModel, Pagination, split_comma_separated_list

UserTitle = Literal["dr", "dr-ing", "prof", "prof-dr", "prof-dr-ing", "phd"]
UserSalutation = Literal["mr", "ms", "mx"]
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
    pagination: Pagination


class UserSearchParams(CamelModel):
    q: str | None = Field(
        default=None, description="Generic free-text search term")

    title: Annotated[list[UserTitle] | None,
                     BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated titles, e.g. dr,dr-ing,prof,prof-dr,prof-dr-ing,phd"
    )
    salutation: Annotated[list[UserSalutation] | None,
                          BeforeValidator(split_comma_separated_list)] = Field(
        default=None,
        description="Comma-separated salutations, e.g. mr,ms,mx"
    )


class UsersSearchResponse(CamelModel):
    data: list[UserOut]
    pagination: Pagination
    search: UserSearchParams


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
