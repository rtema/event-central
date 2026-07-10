"""Authentication business logic, decoupled from the HTTP layer."""

from __future__ import annotations

import datetime as dt
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.auth.models import AuthChallenge, RefreshToken
from src.auth.schemas import AuthTokenResponse
from src.config import settings
from src.core import scopes as scope_utils
from src.core.errors import AuthError
from src.core.security import (
    ACCESS_TOKEN_TYPE,
    REFRESH_TOKEN_TYPE,
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_numeric_code,
    hash_secret,
    verify_hashed_secret,
)
from src.users.models import User, UserAuth, UserScope

log = logging.getLogger("src.auth")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


# --------------------------------------------------------------------------- #
# Lookups
# --------------------------------------------------------------------------- #
def find_active_user_by_email(db: Session, email: str) -> User | None:
    stmt = select(User).where(
        User.email == email,
        User.deleted_at.is_(None),
    )
    return db.execute(stmt).scalar_one_or_none()


def active_scopes_for_user(db: Session, user_id: uuid.UUID) -> set[str]:
    stmt = select(UserScope.scope).where(
        UserScope.user_id == user_id,
        UserScope.deleted_at.is_(None),
    )
    return set(db.execute(stmt).scalars().all())


def _active_auth(db: Session, user_id: uuid.UUID, method: str) -> UserAuth | None:
    stmt = select(UserAuth).where(
        UserAuth.user_id == user_id,
        UserAuth.method == method,
        UserAuth.deleted_at.is_(None),
    )
    return db.execute(stmt).scalars().first()


# --------------------------------------------------------------------------- #
# Token pair issuance
# --------------------------------------------------------------------------- #
def issue_token_pair(
    db: Session,
    *,
    user: User,
    requested_scope: str | None,
    client_id: str | None,
) -> AuthTokenResponse:
    owned = active_scopes_for_user(db, user.id)
    granted = scope_utils.filter_grantable(
        scope_utils.parse_scope(requested_scope), owned)
    scope_str = scope_utils.join_scope(granted)

    sub = f"user:{user.id}"
    access, expires_in = create_access_token(
        sub=sub, scope=scope_str, client_id=client_id)
    refresh, jti, expires_at = create_refresh_token(
        sub=sub, scope=scope_str, client_id=client_id
    )
    db.add(
        RefreshToken(
            id=jti,
            user_id=user.id,
            client_id=client_id,
            scope=scope_str,
            expires_at=expires_at,
        )
    )
    return AuthTokenResponse(
        access_token=access,
        refresh_token=refresh,
        scope=scope_str,
        expires_in=expires_in,
        token_type="Bearer",
    )


# --------------------------------------------------------------------------- #
# Grants
# --------------------------------------------------------------------------- #
def grant_password(
    db: Session,
    *,
    username: str | None,
    password: str | None,
    scope: str | None,
    client_id: str | None,
) -> AuthTokenResponse:
    if not username or not password:
        raise AuthError("invalid_request",
                        description="username and password are required")

    user = find_active_user_by_email(db, username)
    # Always run a hash verification to reduce username-enumeration timing leaks.
    auth = _active_auth(db, user.id, "password") if user else None
    valid = verify_hashed_secret(password, auth.secret if auth else None)
    if not user or not auth or not valid:
        raise AuthError(
            "invalid_grant",
            description="invalid username or password",
            http_status=401,
        )
    return issue_token_pair(db, user=user, requested_scope=scope, client_id=client_id)


def grant_refresh(
    db: Session, *, refresh_token: str | None, scope: str | None, client_id: str | None
) -> AuthTokenResponse:
    if not refresh_token:
        raise AuthError("invalid_request",
                        description="refresh_token is required")
    try:
        claims = decode_token(refresh_token, expected_type=REFRESH_TOKEN_TYPE)
    except TokenError as exc:
        raise AuthError(
            "invalid_grant", description="invalid refresh token", http_status=401
        ) from exc

    record = db.get(RefreshToken, uuid.UUID(claims.jti))
    if record is None or not record.is_active:
        raise AuthError(
            "invalid_grant", description="refresh token is no longer valid", http_status=401
        )

    user = db.get(User, record.user_id)
    if user is None or user.deleted_at is not None:
        raise AuthError("invalid_grant",
                        description="account is unavailable", http_status=401)

    # Rotate: revoke the presented token, issue a fresh pair.
    record.revoked_at = _now()
    # Narrow scope to what was originally granted unless a subset is requested.
    requested = scope if scope else record.scope
    return issue_token_pair(
        db,
        user=user,
        requested_scope=requested,
        client_id=client_id or record.client_id,
    )


def grant_passwordless_otp(
    db: Session, *, username: str | None, otp: str | None, scope: str | None, client_id: str | None
) -> AuthTokenResponse:
    if not username or not otp:
        raise AuthError("invalid_request",
                        description="username and otp are required")

    challenge = _latest_valid_challenge(
        db, destination=username, purpose="passwordless")
    if challenge is None or not verify_hashed_secret(otp, challenge.code_hash):
        raise AuthError("invalid_grant",
                        description="invalid or expired code", http_status=401)

    user = (
        db.get(User, challenge.user_id)
        if challenge.user_id
        else find_active_user_by_email(db, username)
    )
    if user is None or user.deleted_at is not None:
        raise AuthError("invalid_grant",
                        description="account is unavailable", http_status=401)

    challenge.consumed_at = _now()
    requested = scope or challenge.scope
    return issue_token_pair(
        db, user=user, requested_scope=requested, client_id=client_id or challenge.client_id
    )


# --------------------------------------------------------------------------- #
# Revocation
# --------------------------------------------------------------------------- #
def revoke_refresh_token(db: Session, *, token: str) -> None:
    """Revoke a refresh token. Always succeeds opaquely (no enumeration)."""
    try:
        claims = decode_token(token, expected_type=REFRESH_TOKEN_TYPE)
        record = db.get(RefreshToken, uuid.UUID(claims.jti))
        if record and record.revoked_at is None:
            record.revoked_at = _now()
    except (TokenError, ValueError):
        # Opaque: never reveal whether the token was valid.
        return


def revoke_all_for_user(db: Session, user_id: uuid.UUID) -> None:
    stmt = select(RefreshToken).where(
        RefreshToken.user_id == user_id,
        RefreshToken.revoked_at.is_(None),
    )
    for record in db.execute(stmt).scalars():
        record.revoked_at = _now()


# --------------------------------------------------------------------------- #
# Challenges (passwordless login / password reset)
# --------------------------------------------------------------------------- #
def _latest_valid_challenge(db: Session, *, destination: str, purpose: str) -> AuthChallenge | None:
    stmt = (
        select(AuthChallenge)
        .where(
            AuthChallenge.destination == destination,
            AuthChallenge.purpose == purpose,
            AuthChallenge.consumed_at.is_(None),
            AuthChallenge.expires_at > _now(),
        )
        .order_by(AuthChallenge.created_at.desc())
    )
    return db.execute(stmt).scalars().first()


def create_challenge(
    db: Session,
    *,
    destination: str,
    purpose: str,
    channel: str | None = None,
    client_id: str | None = None,
    scope: str | None = None,
    redirect_uri: str | None = None,
) -> str:
    """Create a one-time code challenge and return the *plaintext* code.

    The caller is responsible for delivering the code (email/SMS). In this step
    delivery is stubbed and the code is logged for development.
    """
    user = find_active_user_by_email(db, destination)
    code = generate_numeric_code()
    challenge = AuthChallenge(
        user_id=user.id if user else None,
        purpose=purpose,
        channel=channel,
        destination=destination,
        code_hash=hash_secret(code),
        client_id=client_id,
        scope=scope,
        redirect_uri=redirect_uri,
        expires_at=_now() + dt.timedelta(seconds=settings.otp_ttl_seconds),
    )
    db.add(challenge)
    # NOTE: real email/SMS delivery is wired up in a later step. For now we log
    # only in development so flows are testable; never log codes in production.
    if not settings.is_production:
        log.info("[dev] %s code for %s: %s", purpose, destination, code)
    return code


def confirm_password_reset(db: Session, *, email: str, code: str, new_password: str) -> bool:
    challenge = _latest_valid_challenge(
        db, destination=email, purpose="password-reset")
    if challenge is None or not verify_hashed_secret(code, challenge.code_hash):
        raise AuthError("invalid_grant",
                        description="invalid or expired code", http_status=400)

    user = find_active_user_by_email(db, email)
    if user is None:
        # Opaque-ish: the challenge existed, but the account is gone.
        raise AuthError("invalid_grant",
                        description="invalid or expired code", http_status=400)

    challenge.consumed_at = _now()

    # Append-only auth: soft-delete existing password methods, create a new one.
    existing = db.execute(
        select(UserAuth).where(
            UserAuth.user_id == user.id,
            UserAuth.method == "password",
            UserAuth.deleted_at.is_(None),
        )
    ).scalars()
    for record in existing:
        record.deleted_at = _now()
        record.deleted_by = "system"
        record.deleted_reason = "password-reset"

    db.add(
        UserAuth(
            user_id=user.id,
            method="password",
            secret=hash_secret(new_password),
            created_by="system",
            created_reason="password-reset",
        )
    )
    # Invalidate every outstanding session.
    revoke_all_for_user(db, user.id)
    return True


# --------------------------------------------------------------------------- #
# Access-token verification (used by the API dependency layer)
# --------------------------------------------------------------------------- #
def resolve_api_token(db: Session, token: str) -> tuple[User, set[str]] | None:
    """Resolve a long-lived API token to (user, scopes) or None."""
    stmt = select(UserAuth).where(
        UserAuth.method == "api-token",
        UserAuth.deleted_at.is_(None),
    )
    for record in db.execute(stmt).scalars():
        if verify_hashed_secret(token, record.secret):
            user = db.get(User, record.user_id)
            if user and user.deleted_at is None:
                return user, active_scopes_for_user(db, user.id)
    return None


def verify_access_token(db: Session, token: str) -> tuple[str, set[str], str | None]:
    """Return (sub, scopes, client_id) for a bearer credential.

    Accepts either a signed access JWT or a long-lived API token.
    """
    # First try as a JWT access token.
    try:
        claims = decode_token(token, expected_type=ACCESS_TOKEN_TYPE)
        return claims.sub, scope_utils.parse_scope(claims.scope), claims.client_id
    except TokenError:
        pass

    # Fall back to an opaque API token.
    resolved = resolve_api_token(db, token)
    if resolved is not None:
        user, user_scopes = resolved
        return f"user:{user.id}", user_scopes, None

    raise AuthError("invalid_token",
                    description="invalid or expired token", http_status=401)
