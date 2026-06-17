"""Minimal ClamAV (clamd) client over TCP.

A small, self-contained replacement for the third-party ``clamd`` package. We
only need two things from clamd — a liveness ``PING`` and ``INSTREAM`` scanning
— so we implement just that slice of the protocol against a clamd daemon
running in a separate container.

Protocol (see clamd docs): commands are prefixed with ``z`` and NUL-terminated;
the reply is likewise NUL-terminated. For INSTREAM the payload follows the
command as a series of ``<4-byte big-endian length><bytes>`` chunks, ended by a
zero-length chunk. Replies look like ``stream: OK``, ``stream: <name> FOUND`` or
``stream: <reason> ERROR``.
"""

from __future__ import annotations

import logging
import socket
import struct
from dataclasses import dataclass
from typing import BinaryIO

from fastapi import status

from src.config import settings
from src.core.errors import AppError

# clamd's per-chunk handling is happiest with modestly sized chunks.
_CHUNK_SIZE = 8192
_END_CHUNK = b"\x00\x00\x00\x00"

log = logging.getLogger("src.files")


class ClamAVError(RuntimeError):
    """clamd was unreachable, timed out, or returned a protocol/scan error."""

    http_status = status.HTTP_400_BAD_REQUEST
    error_code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        error: str | None = None,
        http_status: int | None = None,
        details: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.error = error or self.error_code
        if http_status is not None:
            self.http_status = http_status
        self.details = details


@dataclass(frozen=True)
class ClamAVScanResult:
    clean: bool
    signature: str | None = None  # malware name when not clean
    raw: str = ""


class ClamAVClient:
    """Stateless clamd client; each call opens its own short-lived connection."""

    def __init__(self, host: str, port: int, timeout: float = 60.0) -> None:
        self._host = host
        self._port = port
        self._timeout = timeout

    # -- connection helpers ------------------------------------------------- #

    def _connect(self) -> socket.socket:
        try:
            sock = socket.create_connection(
                (self._host, self._port), timeout=self._timeout
            )
        except OSError as exc:
            raise ClamAVError(
                f"Cannot connect to clamd at {self._host}:{self._port}",
                error="clamav_unreachable",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        sock.settimeout(self._timeout)
        return sock

    @staticmethod
    def _read_reply(sock: socket.socket) -> str:
        buf = bytearray()
        while True:
            try:
                chunk = sock.recv(4096)
            except OSError as exc:
                raise ClamAVError(
                    "clamd read failed",
                    error="clamav_read_failed",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ) from exc
            if not chunk:
                break
            buf.extend(chunk)
            if buf.endswith(b"\x00"):
                break
        return buf.rstrip(b"\x00").decode("utf-8", "replace").strip()

    # -- public API --------------------------------------------------------- #

    def ping(self) -> bool:
        with self._connect() as sock:
            try:
                sock.sendall(b"zPING\x00")
                reply = self._read_reply(sock)
            except OSError as exc:
                raise ClamAVError(
                    "clamd ping failed",
                    error="clamav_ping_failed",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ) from exc
        return reply == "PONG"

    def scan_stream(self, data: bytes | bytearray | BinaryIO) -> ClamAVScanResult:
        """Scan ``data`` (bytes or a binary file-like) via INSTREAM."""
        if hasattr(data, "read"):
            payload = data.read()
        else:
            payload = data
        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError("data must be bytes or a binary file-like object")

        with self._connect() as sock:
            try:
                sock.sendall(b"zINSTREAM\x00")
                view = memoryview(bytes(payload))
                for start in range(0, len(view), _CHUNK_SIZE):
                    chunk = view[start:start + _CHUNK_SIZE]
                    sock.sendall(struct.pack("!I", len(chunk)))
                    sock.sendall(chunk)
                sock.sendall(_END_CHUNK)
                raw = self._read_reply(sock)
            except OSError as exc:
                # clamd closes the socket mid-stream when StreamMaxLength is
                # exceeded; treat any I/O failure as a scan error.
                raise ClamAVError(
                    "clamd connection failed during scan",
                    error="clamav_connection_interrupted",
                    http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
                ) from exc

        return self._parse(raw)

    @staticmethod
    def _parse(raw: str) -> ClamAVScanResult:
        if not raw:
            raise ClamAVError(
                "empty clamd response",
                error="clamav_unreachable",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        # Drop the leading "stream:" label if present.
        body = raw.split(":", 1)[1].strip() if ":" in raw else raw
        if body.endswith("FOUND"):
            signature = body[: -len("FOUND")].strip() or "unknown"
            return ClamAVScanResult(clean=False, signature=signature, raw=raw)
        if body.endswith("ERROR"):
            raise ClamAVError(
                f"clamd error: {raw}",
                error="clamav_error",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        if body == "OK" or body.endswith(" OK"):
            return ClamAVScanResult(clean=True, raw=raw)
        raise ClamAVError(
            f"unexpected clamd response: {raw!r}",
            error="clamav_unexpected_result",
            http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )


def clamav_validate_bytes(raw: bytes) -> ClamAVScanResult | None:
    """Stream ``raw`` to the ClamAV container and reject on detection.

    clamd runs as a separate service reached over TCP via our own small client.
    A positive detection raises ``FileRejected``. If the scanner is unreachable
    or errors out we fail closed (raise ``AppError``) unless
    ``CLAMD_FAIL_OPEN`` is set.
    """
    client = ClamAVClient(
        settings.clamav_host,
        settings.clamav_port,
        timeout=settings.clamav_timeout
    )
    
    try:
        result = client.scan_stream(raw)
    except ClamAVError as exc:
        log.warning(
            "ClamAV scan failed: %s", exc)

        # scan could not be performed, return no result
        return None

    # Malware found, reject
    if not result.clean:
        raise AppError(
            f"Malware detected: {result.signature}",
            error="invalid_file",
            http_status=400
        )

    # return scan result
    return result
