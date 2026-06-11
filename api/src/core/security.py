"""Cryptographic primitives: password hashing, JWTs, signed links, OTP codes.

Kept dependency-light: argon2 for password/secret hashing and PyJWT for tokens.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from src.config import settings

_ph = PasswordHasher()

ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"


# --------------------------------------------------------------------------- #
# Password / secret hashing
# --------------------------------------------------------------------------- #
def hash_secret(plain: str) -> str:
    """Hash a password, API token or OTP secret with argon2."""
    return _ph.hash(plain)


def verify_hashed_secret(plain: str, hash: str | None) -> bool:
    """Verify a plaintext secret against an argon2 hash (constant-ish time)."""
    if not hash:
        return False
    try:
        return _ph.verify(hash, plain)
    except VerifyMismatchError:
        return False
    except Exception:
        return False


def needs_rehash(hash: str) -> bool:
    return _ph.check_needs_rehash(hash)


# --------------------------------------------------------------------------- #
# Random token generation
# --------------------------------------------------------------------------- #
def generate_api_token() -> str:
    """A long-lived, URL-safe opaque API token."""
    return f"ec_{secrets.token_urlsafe(40)}"


def generate_numeric_code(length: int | None = None) -> str:
    length = length or settings.otp_code_length
    return "".join(secrets.choice("0123456789") for _ in range(length))


def generate_backup_code() -> str:
    """A human-readable backup code, e.g. ``XXXX-XXXX-XXXX``."""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no ambiguous chars
    groups = ["".join(secrets.choice(alphabet)
                      for _ in range(4)) for _ in range(3)]
    return "-".join(groups)


def generate_otp_secret() -> str:
    """A base32 shared secret for TOTP authenticator apps."""
    import base64

    return base64.b32encode(secrets.token_bytes(20)).decode().rstrip("=")


# --------------------------------------------------------------------------- #
# JWT access / refresh tokens
# --------------------------------------------------------------------------- #
@dataclass(slots=True)
class TokenClaims:
    sub: str
    scope: str
    token_type: str
    jti: str
    client_id: str | None
    exp: int
    iat: int


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _encode(payload: dict[str, Any]) -> str:
    base_payload = {
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
    }
    base_payload.update(payload)
    return jwt.encode(base_payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_access_token(
    *, sub: str, scope: str, client_id: str | None = None
) -> tuple[str, int]:
    """Return ``(token, expires_in_seconds)``."""
    iat = _now()
    exp = iat + dt.timedelta(seconds=settings.access_token_ttl_seconds)
    token = _encode(
        {
            "sub": sub,
            "scope": scope,
            "token_type": ACCESS_TOKEN_TYPE,
            "client_id": client_id,
            "jti": str(uuid.uuid4()),
            "iat": int(iat.timestamp()),
            "exp": int(exp.timestamp()),
        }
    )
    return token, settings.access_token_ttl_seconds


def create_refresh_token(
    *, sub: str, scope: str, client_id: str | None = None, jti: uuid.UUID | None = None
) -> tuple[str, uuid.UUID, dt.datetime]:
    """Return ``(token, jti, expires_at)``.

    The ``jti`` must be persisted (RefreshToken row) so the token can later be
    revoked. Callers either pass a pre-allocated jti or use the returned one.
    """
    jti = jti or uuid.uuid4()
    iat = _now()
    exp = iat + dt.timedelta(seconds=settings.refresh_token_ttl_seconds)
    token = _encode(
        {
            "sub": sub,
            "scope": scope,
            "token_type": REFRESH_TOKEN_TYPE,
            "client_id": client_id,
            "jti": str(jti),
            "iat": int(iat.timestamp()),
            "exp": int(exp.timestamp()),
        }
    )
    return token, jti, exp


class TokenError(Exception):
    """Raised when a JWT cannot be decoded or fails validation."""


def decode_token(token: str, *, expected_type: str | None = None) -> TokenClaims:
    try:
        data = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc

    if expected_type is not None and data.get("token_type") != expected_type:
        raise TokenError("unexpected token type")

    return TokenClaims(
        sub=data["sub"],
        scope=data.get("scope", ""),
        token_type=data.get("token_type", ""),
        jti=data.get("jti", ""),
        client_id=data.get("client_id"),
        exp=data["exp"],
        iat=data["iat"],
    )


# --------------------------------------------------------------------------- #
# HMAC-signed file-download links (used by the /link and /files endpoints)
# --------------------------------------------------------------------------- #
def sign_download_token(*, resource: str, expires_at: int) -> str:
    """Create an opaque, tamper-evident token of the form ``<payload>.<sig>``."""
    payload = f"{resource}:{expires_at}"
    sig = hmac.new(
        settings.signed_url_secret.encode(), payload.encode(), hashlib.sha256
    ).hexdigest()
    return f"{resource}.{expires_at}.{sig}"


def verify_download_token(token: str, *, resource: str) -> bool:
    try:
        token_resource, exp_str, sig = token.rsplit(".", 2)
        expires_at = int(exp_str)
    except (ValueError, AttributeError):
        return False
    if token_resource != resource:
        return False
    if expires_at < int(_now().timestamp()):
        return False
    expected = hmac.new(
        settings.signed_url_secret.encode(),
        f"{resource}:{expires_at}".encode(),
        hashlib.sha256,
    ).hexdigest()
    return hmac.compare_digest(expected, sig)
