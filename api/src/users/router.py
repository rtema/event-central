"""User endpoints (/api/v1/users, tag: Users).

Note: the spec uses POST (not PUT/PATCH) for the update/set operations.
"""

from __future__ import annotations

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.orm import Session

from src.auth.deps import AuthenticatedActor, require_all_scopes
from src.core.deps import PageParams, get_db, page_params
from src.core.schemas import make_pagination
from src.core.scopes import SCOPE_USERS_READ_ALL, SCOPE_USERS_WRITE_ALL
from src.users import service
from src.users.models import UserAuth, UserData
from src.users.schemas import (
    UserAuthCreateRequest,
    UserAuthListResponse,
    UserAuthOut,
    UserDataHistoryItemOut,
    UserDataHistoryResponse,
    UserDataOut,
    UserHistoryItem,
    UserHistoryResponse,
    UserOut,
    UserResponse,
    UserScopeOut,
    UserScopesListResponse,
    UserScopesUpdateRequest,
    UsersCreateRequest,
    UserSearchParams,
    UsersListResponse,
    UsersSearchResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/api/v1/users", tags=["Users"])


def _user_data_out(record: UserData) -> UserDataOut:
    return UserDataOut(
        id=record.id,
        user_id=record.user_id,
        created_at=record.created_at,
        created_by=record.created_by,
        data=record.data or {},
    )


# --------------------------------------------------------------------------- #
# Users collection
# --------------------------------------------------------------------------- #
@router.get("", response_model=UsersListResponse, summary="List users")
def list_users(
    page: PageParams = Depends(page_params),
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL))
) -> UsersListResponse:
    users, total = service.list_users(db, limit=page.limit, offset=page.offset)
    return UsersListResponse(
        data=[UserOut.model_validate(u) for u in users],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
    )


@router.get("/search", response_model=UsersSearchResponse, summary="Search users")
def search_users(
    page: Annotated[PageParams, Depends(page_params)],
    search_params: Annotated[UserSearchParams, Query()],
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL))
) -> UsersSearchResponse:
    users, total = service.search_users(
        db, limit=page.limit, offset=page.offset, search_params=search_params
    )
    return UsersSearchResponse(
        data=[UserOut.model_validate(u) for u in users],
        pagination=make_pagination(
            total, limit=page.limit, offset=page.offset),
        search=search_params,
    )


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create user",
)
def create_user(
    body: UsersCreateRequest,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserResponse:
    user = service.create_user(
        db,
        email=body.email,
        first_name=body.first_name,
        last_name=body.last_name,
        title=body.title,
        salutation=body.salutation,
        actor=authenticated_actor.sub,
    )
    return UserResponse(data=UserOut.model_validate(user))


# --------------------------------------------------------------------------- #
# Single user
# --------------------------------------------------------------------------- #
@router.get("/{user_id}", response_model=UserResponse, summary="Get a user")
def get_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserResponse:
    return UserResponse(data=UserOut.model_validate(service.get_user(db, user_id)))


@router.post("/{user_id}", response_model=UserResponse, summary="Update user")
def update_user(
    user_id: uuid.UUID,
    body: UserUpdateRequest,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserResponse:
    user = service.update_user(
        db, user_id, changes=body.model_dump(exclude_unset=True), actor=authenticated_actor.sub
    )
    return UserResponse(data=UserOut.model_validate(user))


@router.delete("/{user_id}", response_model=UserResponse, summary="Delete user")
def delete_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserResponse:
    user = service.delete_user(db, user_id, actor=authenticated_actor.sub)
    return UserResponse(data=UserOut.model_validate(user))


@router.get("/{user_id}/history", response_model=UserHistoryResponse, summary="History of a user")
def get_user_history(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserHistoryResponse:
    items = service.get_user_history(db, user_id)
    return UserHistoryResponse(data=[UserHistoryItem.model_validate(i) for i in items])


@router.post("/{user_id}/restore", response_model=UserResponse, summary="Restore a user")
def restore_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserResponse:
    user = service.restore_user(db, user_id, actor=authenticated_actor.sub)
    return UserResponse(data=UserOut.model_validate(user))


# --------------------------------------------------------------------------- #
# User auth methods
# --------------------------------------------------------------------------- #
@router.get(
    "/{user_id}/auth",
    response_model=UserAuthListResponse,
    summary="Authentication configuration for a user",
)
def list_user_auth(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserAuthListResponse:
    methods = service.list_user_auth(db, user_id)
    # Never expose stored secrets on listing.
    return UserAuthListResponse(data=[_auth_out(m, reveal=False) for m in methods])


@router.post(
    "/{user_id}/auth",
    response_model=UserAuthOut,
    summary="Set up an auth method for a user",
)
def create_user_auth(
    user_id: uuid.UUID,
    body: UserAuthCreateRequest,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserAuthOut:
    record, visible = service.create_user_auth(
        db, user_id, method=body.method, secret=body.secret, actor=authenticated_actor.sub
    )
    out = _auth_out(record, reveal=False)

    # Show the freshly generated secret exactly once.
    out.secret = visible
    return out


@router.get(
    "/{user_id}/auth/{user_auth_id}",
    response_model=UserAuthOut,
    summary="Get authentication method",
)
def get_user_auth(
    user_id: uuid.UUID,
    user_auth_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserAuthOut:
    return _auth_out(service.get_user_auth(db, user_id, user_auth_id), reveal=False)


@router.delete(
    "/{user_id}/auth/{user_auth_id}",
    response_model=UserAuthOut,
    summary="Disable an authentication method",
)
def delete_user_auth(
    user_id: uuid.UUID,
    user_auth_id: uuid.UUID,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserAuthOut:
    record = service.delete_user_auth(
        db, user_id, user_auth_id, actor=authenticated_actor.sub)
    return _auth_out(record, reveal=False)


def _auth_out(record: UserAuth, *, reveal: bool) -> UserAuthOut:
    """Map a UserAuth row to the response, controlling secret visibility.

    Passwordless always shows its bound identifier; everything else is hidden
    unless ``reveal`` is set (only on creation, handled by the caller).
    """
    out = UserAuthOut.model_validate(record)
    if record.method == "passwordless":
        out.secret = record.secret
    elif not reveal:
        out.secret = None
    return out


# --------------------------------------------------------------------------- #
# User scopes
# --------------------------------------------------------------------------- #
@router.get(
    "/{user_id}/scopes",
    response_model=UserScopesListResponse,
    summary="Scopes the user has access to",
)
def list_user_scopes(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserScopesListResponse:
    scopes = service.list_user_scopes(db, user_id)
    return UserScopesListResponse(data=[UserScopeOut.model_validate(s) for s in scopes])


@router.post(
    "/{user_id}/scopes",
    response_model=UserScopesListResponse,
    summary="Set access scopes",
)
def set_user_scopes(
    user_id: uuid.UUID,
    body: UserScopesUpdateRequest,
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserScopesListResponse:
    scopes = service.set_user_scopes(
        db, user_id, scopes=body.scopes, actor=authenticated_actor.sub)
    return UserScopesListResponse(data=[UserScopeOut.model_validate(s) for s in scopes])


# --------------------------------------------------------------------------- #
# Arbitrary user data
# --------------------------------------------------------------------------- #
@router.get("/{user_id}/data", response_model=UserDataOut, summary="Arbitrary user data")
def get_user_data(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserDataOut:
    record = service.get_user_data(db, user_id)
    if record is None:
        # No data set yet — return an empty, id-less envelope.
        return UserDataOut(
            id=uuid.UUID(int=0), user_id=user_id, created_at=_epoch(), created_by=None, data={}
        )
    return _user_data_out(record)


@router.post("/{user_id}/data", response_model=UserDataOut, summary="Set new user data")
def set_user_data(
    user_id: uuid.UUID,
    body: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    authenticated_actor: AuthenticatedActor = Depends(
        require_all_scopes(SCOPE_USERS_WRITE_ALL)),
) -> UserDataOut:
    record = service.set_user_data(
        db, user_id, data=body, actor=authenticated_actor.sub)
    return _user_data_out(record)


@router.get(
    "/{user_id}/data/history",
    response_model=UserDataHistoryResponse,
    summary="History of arbitrary user data",
)
def get_user_data_history(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    _: AuthenticatedActor = Depends(require_all_scopes(SCOPE_USERS_READ_ALL)),
) -> UserDataHistoryResponse:
    rows = service.get_user_data_history(db, user_id)
    return UserDataHistoryResponse(
        data=[
            UserDataHistoryItemOut(
                id=r.id,
                user_id=r.user_id,
                created_at=r.created_at,
                created_by=r.created_by,
                new_state=r.data or {},
            )
            for r in rows
        ]
    )


def _epoch():
    import datetime as dt

    return dt.datetime(1970, 1, 1, tzinfo=dt.UTC)
