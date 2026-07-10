"""Auth endpoint schemas (OAuth-style, snake_case field names)."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, EmailStr, Field

from src.core.schemas import Locale

# Grant type identifiers (the passwordless OTP grant uses the Auth0 URI).
GRANT_PASSWORD = "password"
GRANT_REFRESH = "refresh_token"
GRANT_PASSWORDLESS_OTP = "http://auth0.com/oauth/grant-type/passwordless/otp"


class AuthTokenRequest(BaseModel):
    grant_type: Literal[
        "password",
        "refresh_token",
        "http://auth0.com/oauth/grant-type/passwordless/otp",
    ]
    username: str | None = None
    password: str | None = None
    otp: str | None = None
    refresh_token: str | None = None
    client_id: str | None = None
    scope: str | None = None


class AuthTokenResponse(BaseModel):
    access_token: str
    refresh_token: str | None = None
    scope: str
    expires_in: int
    token_type: str = "Bearer"


class AuthRevokeRequest(BaseModel):
    token: str = Field(..., description="The refresh token to revoke")


class AuthUserinfoResponse(BaseModel):
    sub: str
    email: EmailStr | None = None
    name: str | None = None


class _PasswordlessAuthParams(BaseModel):
    scope: str
    redirectUri: str | None = None
    locale: Locale


class AuthPasswordlessStartRequest(BaseModel):
    client_id: str | None = None
    connection: Literal["email", "sms"]
    email: EmailStr | None = None
    phoneNumber: str | None = None
    send: Literal["link", "code"] = "code"
    authParams: _PasswordlessAuthParams


class AuthPasswordlessStartResponse(BaseModel):
    ok: bool = True


class AuthPasswordResetStartRequest(BaseModel):
    email: EmailStr
    redirectUri: str
    locale: Locale


class AuthPasswordResetStartResponse(BaseModel):
    ok: bool = True


class AuthPasswordResetConfirmRequest(BaseModel):
    email: EmailStr
    code: str
    password: str = Field(..., min_length=8)


class AuthPasswordResetConfirmResponse(BaseModel):
    ok: bool = True
