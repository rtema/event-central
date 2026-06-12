"""S3-compatible object storage.

* Development uses a single MinIO instance.
* Production configures a *secondary* store as well; writes go to both
  (dual-write) so a single store failure cannot lose data, and reads fall back
  to the secondary if the primary is unavailable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError, EndpointConnectionError
from mypy_boto3_s3.client import S3Client

from src.config import settings

log = logging.getLogger("app.storage")


@dataclass(slots=True)
class _Target:
    name: str
    client: S3Client
    bucket: str


def _make_client(endpoint: str, region: str, access_key: str, secret_key: str) -> S3Client:
    return boto3.client(  # pyright: ignore[reportUnknownMemberType]
        "s3",
        endpoint_url=endpoint,
        region_name=region,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path" if settings.s3_force_path_style else "auto"},
        ),
    )


class ObjectStorage:
    """Thin wrapper over one or two S3-compatible stores."""

    def __init__(self) -> None:
        # attach to primary endpoint
        self._targets: list[_Target] = [
            _Target(
                name="primary",
                client=_make_client(
                    settings.storage_primary_endpoint,
                    settings.storage_primary_region,
                    settings.storage_primary_user_key,
                    settings.storage_primary_user_secret,
                ),
                bucket=settings.storage_primary_bucket,
            )
        ]

        # attach to secondary endpoint
        self._targets.append(
            _Target(
                name="secondary",
                client=_make_client(
                    settings.storage_secondary_endpoint,
                    settings.storage_secondary_region,
                    settings.storage_secondary_user_key,
                    settings.storage_secondary_user_secret,
                ),
                bucket=settings.storage_secondary_bucket,
            )
        )

    @property
    def is_dual(self) -> bool:
        return len(self._targets) > 1

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        """Write to every configured target. Raises if the primary fails."""
        errors: list[str] = []
        for target in self._targets:
            try:
                target.client.put_object(
                    Bucket=target.bucket, Key=key, Body=data, ContentType=content_type
                )
            except ClientError as exc:
                errors.append(f"{target.name}: {exc}")
                if target.name == "primary":
                    raise
                log.error("dual-write to %s failed for %s: %s",
                          target.name, key, exc)
        if errors:
            log.warning("object %s written with partial errors: %s",
                        key, "; ".join(errors))

    def get(self, key: str) -> bytes:
        """Read from primary; fall back to secondary if present."""
        last_exc: Exception | None = None
        for target in self._targets:
            try:
                resp = target.client.get_object(Bucket=target.bucket, Key=key)
                return resp["Body"].read()
            except ClientError as exc:
                last_exc = exc
                log.warning("read from %s failed for %s: %s",
                            target.name, key, exc)
        raise FileNotFoundError(
            f"object not found in any store: {key}") from last_exc

    def ensure_buckets(self) -> None:
        """Create the configured buckets if they don't exist (dev convenience)."""
        for target in self._targets:
            try:
                target.client.head_bucket(Bucket=target.bucket)
            except ClientError:
                target.client.create_bucket(Bucket=target.bucket)
                log.info("created bucket %s on %s", target.bucket, target.name)

    def test_connections(self) -> tuple[dict[str, str], int]:
        """Check if the connection to all servers can be established."""
        code: int = 200
        status: dict[str, str] = {}

        for target in self._targets:
            # check general connection
            try:
                target.client.list_buckets()
                status[target.name] = "connection-successful"
            except EndpointConnectionError as e:
                status[target.name] = "connection-failed"
                code = 500

                # temporary error message
                print(f"{target.name}: Could not reach endpoint: {e}")

                # do not further check endpoint
                continue
            except ClientError as e:
                status[target.name] = "s3-error"
                code = 500

                # temporary error message
                print(f"{target.name}: AWS/S3 error: {e}")

                # do not further check endpoint
                continue

            # check if bucket exists
            try:
                target.client.head_bucket(Bucket=target.bucket)
                status[target.name] = "ok"
            except ClientError as e:
                status[target.name] = "bucket-does-not-exist"
                code = 404

                # temporary error message
                print(f"{target.name}: Bucket does not exist: {e}")

        return status, code


class LocalStorage:
    """Filesystem-backed object storage for development, CI and smoke tests.

    Implements the same surface as :class:`ObjectStorage` (``put``/``get``/
    ``ensure_buckets``/``is_dual``) so callers are oblivious to the backend.
    Objects are written under ``settings.local_storage_dir``; keys map directly
    to relative paths. Never selected in production (see ``get_storage``).
    """

    def __init__(self) -> None:
        self._root = Path(settings.api_local_storage_dir) / \
            settings.storage_primary_bucket

    @property
    def is_dual(self) -> bool:
        return False

    def _path(self, key: str) -> Path:
        # Keys are caller-controlled but always of the form ``a/b/c``; resolve
        # and confine them under the root to avoid escaping via ``..``.
        target = (self._root / key).resolve()
        root = self._root.resolve()
        if not str(target).startswith(str(root)):
            raise ValueError(f"refusing to write outside storage root: {key}")
        return target

    def put(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._path(key)
        if not path.is_file():
            raise FileNotFoundError(f"object not found: {key}")
        return path.read_bytes()

    def ensure_buckets(self) -> None:
        self._root.mkdir(parents=True, exist_ok=True)

    def test_connections(self) -> tuple[dict[str, str], int]:
        """Return static ok message."""

        return {"local-storage": "ok"}, 200


_storage: ObjectStorage | LocalStorage | None = None


def get_storage() -> ObjectStorage | LocalStorage:
    global _storage
    if _storage is None:
        if settings.api_storage_backend == "local" and not settings.is_production:
            log.info("using local filesystem storage at %s",
                     settings.api_local_storage_dir)
            _storage = LocalStorage()
        else:
            _storage = ObjectStorage()
    return _storage
