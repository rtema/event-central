"""Authentication endpoints (/auth/*)."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from src.auth import service as auth_service
from src.auth.deps import AuthenticatedActor, get_authenticated_actor
from src.auth.schemas import (
    GRANT_PASSWORD,
    GRANT_PASSWORDLESS_OTP,
    GRANT_REFRESH,
    AuthPasswordlessStartRequest,
    AuthPasswordlessStartResponse,
    AuthPasswordResetConfirmRequest,
    AuthPasswordResetConfirmResponse,
    AuthPasswordResetStartRequest,
    AuthPasswordResetStartResponse,
    AuthRevokeRequest,
    AuthTokenRequest,
    AuthTokenResponse,
    AuthUserinfoResponse,
)
from src.core.deps import get_db
from src.core.errors import AppError, AuthError
from src.users.models import User

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/token", response_model=AuthTokenResponse, summary="OAuth 2.0 Token")
def auth_token(body: AuthTokenRequest, db: Session = Depends(get_db)) -> AuthTokenResponse:
    if body.grant_type == GRANT_PASSWORD:
        return auth_service.grant_password(
            db,
            username=body.username,
            password=body.password,
            scope=body.scope,
            client_id=body.client_id,
        )
    if body.grant_type == GRANT_REFRESH:
        return auth_service.grant_refresh(
            db,
            refresh_token=body.refresh_token,
            scope=body.scope,
            client_id=body.client_id,
        )
    if body.grant_type == GRANT_PASSWORDLESS_OTP:
        return auth_service.grant_passwordless_otp(
            db,
            username=body.username,
            otp=body.otp,
            scope=body.scope,
            client_id=body.client_id,
        )
    raise AuthError("unsupported_grant_type",
                    description=f"unsupported grant: {body.grant_type}")


@router.post("/revoke", summary="OAuth 2.0 Revoke Token")
def auth_revoke(body: AuthRevokeRequest, db: Session = Depends(get_db)) -> dict[str, bool]:
    auth_service.revoke_refresh_token(db, token=body.token)
    return {"ok": True}


@router.get("/userinfo", response_model=AuthUserinfoResponse, summary="OAuth 2.0 Userinfo")
def auth_userinfo(
    authenticated_actor: AuthenticatedActor = Depends(get_authenticated_actor),
    db: Session = Depends(get_db),
) -> AuthUserinfoResponse:
    user_id = authenticated_actor.user_id
    if user_id is None:
        # App / API-token authenticated_actors have no user record.
        return AuthUserinfoResponse(sub=authenticated_actor.sub)
    user = db.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise AppError("user not found",
                       error="invalid_token", http_status=404)
    return AuthUserinfoResponse(sub=authenticated_actor.sub, email=user.email, name=user.full_name)


@router.post(
    "/passwordless/start",
    response_model=AuthPasswordlessStartResponse,
    summary="Start passwordless login",
)
def auth_passwordless_start(
    body: AuthPasswordlessStartRequest, db: Session = Depends(get_db)
) -> AuthPasswordlessStartResponse:
    destination = body.email or body.phoneNumber
    if not destination:
        raise AuthError("invalid_request",
                        description="email or phoneNumber is required")

    auth_service.create_challenge(
        db,
        destination=destination,
        purpose="passwordless",
        channel=body.connection,
        client_id=body.client_id,
        scope=body.authParams.scope,
        redirect_uri=body.authParams.redirectUri,
    )

    # Opaque response so user inventory is never leaked.
    return AuthPasswordlessStartResponse(ok=True)


@router.post(
    "/password-reset/start",
    response_model=AuthPasswordResetStartResponse,
    summary="Start password reset process",
)
def auth_password_reset_start(
    body: AuthPasswordResetStartRequest, db: Session = Depends(get_db)
) -> AuthPasswordResetStartResponse:

    auth_service.create_challenge(
        db,
        destination=body.email,
        purpose="password-reset",
        channel="email",
        redirect_uri=body.redirectUri,
    )

    return AuthPasswordResetStartResponse(ok=True)


@router.post(
    "/password-reset/confirm",
    response_model=AuthPasswordResetConfirmResponse,
    summary="Finalize password reset",
)
def auth_password_reset_confirm(
    body: AuthPasswordResetConfirmRequest, db: Session = Depends(get_db)
) -> AuthPasswordResetConfirmResponse:

    auth_service.confirm_password_reset(
        db, email=body.email, code=body.code, new_password=body.password
    )

    return AuthPasswordResetConfirmResponse(ok=True)
