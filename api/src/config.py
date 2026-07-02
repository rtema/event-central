"""Application configuration.

Configuration is read from (in order of precedence): process environment, a
local ``.env`` file, then Docker secret files. In production those secrets are
mounted under ``/run/secrets``; in development they are read from a local
``../secrets/`` directory (relative to the project root). The same image
therefore runs unchanged across every start-up mode and across dev/prod, with
secrets supplied as files.
"""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Literal
from urllib.parse import quote

from pydantic import Field, ValidationError
from pydantic_settings import BaseSettings, SettingsConfigDict


def _resolve_secrets_dir() -> str | None:
    """Locate the directory pydantic-settings reads Docker-style secret files from.

    Each setting can be supplied as a file whose name matches the (lower-case)
    field name, e.g. ``jwt_secret`` or ``db_pass``.

    Precedence:
      1. ``SECRETS_DIR`` environment variable (explicit override).
      2. ``/run/secrets`` — the Docker secrets mount used in production.
      3. ``<project root>/secrets`` — the local ``../secrets/`` directory used
         in development (resolved relative to this file, so it works regardless
         of the current working directory).

    Returns ``None`` when the resolved directory does not exist, so local runs
    without any secrets present don't emit warnings.
    """
    override = os.getenv("SECRETS_DIR")
    if override:
        candidates = [Path(override)]
    else:
        candidates = [
            Path("/run/secrets"),
            Path(__file__).resolve().parent.parent.parent / "secrets",
        ]
    for candidate in candidates:
        print(candidate)
        if candidate.is_dir():
            return str(candidate)
    return None


_SECRETS_DIR = _resolve_secrets_dir()


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env.dev",  # do not allow .env files in production
        env_file_encoding="utf-8",
        # env_prefix="api_",
        extra="ignore",
        case_sensitive=False,
        # Only enable the secrets source if a directory was found, so local dev
        # (without mounted secrets) doesn't emit warnings.
        secrets_dir=_SECRETS_DIR,
    )

    # -- General ------------------------------------------------------------
    environment: Literal["development", "production"] = "development"
    api_service_name: str = "event-central"
    log_level: str = "INFO"
    api_log_format: Literal["json", "text"] = "json"
    api_host: str = "0.0.0.0"  # noqa: S104 - intentional inside a container
    api_port: int = 7435

    # -- Database -----------------------------------------------------------
    # The SQLAlchemy URL is assembled from these individual parts (see the
    # ``database_url`` property) so credentials can be supplied as Docker
    # secrets (``db_user``, ``db_pass``, ...) rather than baked into a single
    # connection string.
    db_user: str = "event_central"
    db_password: str = "event_central"
    db_host: str = "127.0.0.1"
    db_port: int = 53542
    db_name: str = "event_central"
    api_db_scheme: str = "postgresql+psycopg"
    api_db_pool_size: int = 5
    api_db_max_overflow: int = 10
    api_db_echo: bool = False

    @property
    def database_url(self) -> str:
        """Assemble the SQLAlchemy URL from the individual ``db_*`` settings.

        User and password are percent-encoded so credentials containing
        characters such as ``@``, ``:`` or ``/`` (common in generated secrets)
        stay valid. An empty ``db_pass`` is omitted entirely.
        """
        userinfo = quote(self.db_user, safe="")
        if self.db_password:
            userinfo = f"{userinfo}:{quote(self.db_password, safe='')}"
        return f"{self.api_db_scheme}://{userinfo}@{self.db_host}:{self.db_port}/{self.db_name}"

    # -- JWT / auth ---------------------------------------------------------
    api_jwt_secret: str = Field(
        default="change-me-in-production", min_length=8)
    api_jwt_algorithm: str = "HS256"
    api_jwt_issuer: str = "event-central"
    api_jwt_audience: str = "event-central"
    api_access_token_ttl_seconds: int = 900
    api_refresh_token_ttl_seconds: int = 60 * 60 * 24 * 30

    api_signed_url_secret: str = Field(default="change-me-too", min_length=8)
    api_signed_url_ttl_seconds: int = 60 * 15

    # Public base URL used to build absolute, shareable download links. Behind
    # the Caddy TLS terminator this is the public https origin; in development
    # it is the local web port.
    api_base_url: str = "http://localhost:7435"
    app_base_url: str = "http://localhost:7430"

    otp_ttl_seconds: int = 60 * 10
    otp_code_length: int = 6

    # -- Object storage -----------------------------------------------------
    # ``s3`` (default) uses the S3-compatible backend below (MinIO in dev, dual
    # S3 in prod). ``local`` uses a filesystem directory and is intended for
    # development, CI and the in-process smoke suites where no MinIO/S3 is
    # available. Production always uses ``s3``.
    api_storage_backend: Literal["s3", "local"] = "s3"
    api_local_storage_dir: str = "/tmp/event-central-storage"  # noqa: S108 - dev only

    storage_primary_endpoint: str = "http://localhost:7450"
    storage_primary_region: str = "eu-central-1"
    storage_primary_user_key: str = "user"
    storage_primary_user_secret: str = "password"
    storage_primary_bucket: str = "event-central"

    storage_secondary_endpoint: str = "http://localhost:7452"
    storage_secondary_region: str = "eu-central-1"
    storage_secondary_user_key: str = "user"
    storage_secondary_user_secret: str = "password"
    storage_secondary_bucket: str = "event-central"

    s3_force_path_style: bool = True

    # -- Uploads ------------------------------------------------------------
    # To protect the upload endpoints, set some boundaries
    # 50 MiB hard cap on any single upload
    api_files_max_size: int = 50 * 1024 * 1024
    # ~64 MP guard against decompression bombs
    api_files_max_image_pixels: int = 64_000_000

    # -- Malware scanning ---------------------------------------------------
    # To protect from unwanted files, allow malware scanning
    clamav_host: str = "localhost"
    clamav_port: int = 7460
    clamav_timeout: float = 10.0

    # -- Observability (OpenObserve log shipping; optional) -----------------
    # When openobserve_url is set, a non-blocking background handler ships JSON
    # logs to OpenObserve's bulk ingest API. Otherwise logs go to stdout only
    # (a collector can ship them). See src/logging_config.py.
    openobserve_url: str | None = None  # e.g. https://o2.example.com
    openobserve_organization: str = "default"
    openobserve_stream: str = "event_central"
    # HTTP Basic credentials "user:pass" base64 or token
    openobserve_token: str | None = None

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
