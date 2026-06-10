"""Application configuration.

Configuration is read from (in order of precedence): process environment, a
local ``.env`` file, then Docker secret files mounted under ``/run/secrets``.
The same image therefore runs unchanged across every start-up mode and across
dev/prod, with secrets supplied as files in production.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict

# Docker secrets are mounted here. Each setting can be supplied as a file whose
# name matches the (lower-case) field name, e.g. /run/secrets/jwt_secret.
_SECRETS_DIR = os.getenv("SECRETS_DIR", "/run/secrets")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev", # do not allow .env files in production
        env_file_encoding="utf-8",
        env_prefix="api_",
        extra="ignore",
        case_sensitive=False,
        # Only enable the secrets source if the directory exists, so local dev
        # (without mounted secrets) doesn't emit warnings.
        secrets_dir=_SECRETS_DIR if Path(_SECRETS_DIR).is_dir() else None,
    )

    # -- General ------------------------------------------------------------
    environment: Literal["development", "production"] = "development"
    service_name: str = "event-central"
    log_level: str = "INFO"
    log_format: Literal["json", "text"] = "json"
    host: str = "0.0.0.0"  # noqa: S104 - intentional inside a container
    port: int = 7435

    # -- Database -----------------------------------------------------------
    database_url: str = "postgresql+psycopg://eventcentral:eventcentral@db:5432/eventcentral"
    db_pool_size: int = 5
    db_max_overflow: int = 10
    db_echo: bool = False

    # -- JWT / auth ---------------------------------------------------------
    jwt_secret: str = Field(default="change-me-in-production", min_length=8)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "event-central"
    jwt_audience: str = "event-central"
    access_token_ttl_seconds: int = 900
    refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30

    signed_url_secret: str = Field(default="change-me-too", min_length=8)
    signed_url_ttl_seconds: int = 60 * 15

    otp_ttl_seconds: int = 60 * 10
    otp_code_length: int = 6

    # -- Object storage -----------------------------------------------------
    s3_primary_endpoint: str = "http://minio:9000"
    s3_primary_region: str = "us-east-1"
    s3_primary_access_key: str = "minioadmin"
    s3_primary_secret_key: str = "minioadmin"
    s3_primary_bucket: str = "event-central"

    s3_secondary_endpoint: str | None = None
    s3_secondary_region: str | None = None
    s3_secondary_access_key: str | None = None
    s3_secondary_secret_key: str | None = None
    s3_secondary_bucket: str | None = None

    s3_force_path_style: bool = True

    # -- Observability (OpenObserve log shipping; optional) -----------------
    # When openobserve_url is set, a non-blocking background handler ships JSON
    # logs to OpenObserve's bulk ingest API. Otherwise logs go to stdout only
    # (a collector can ship them). See src/logging_config.py.
    openobserve_url: str | None = None  # e.g. https://o2.example.com
    openobserve_organization: str = "default"
    openobserve_stream: str = "event_central"
    openobserve_token: str | None = None  # HTTP Basic credentials "user:pass" base64 or token

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    try:
        return Settings()
    except ValidationError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Invalid configuration:\n{exc}") from exc


settings = get_settings()
