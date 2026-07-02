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
import time
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
    """Stateless clamd client; each call opens its own short-lived connection.

    ``timeout`` is a wall-clock budget for the *entire* exchange (connect +
    send + reply), not a per-operation deadline. Each blocking socket operation
    is re-armed with the time remaining against a single monotonic deadline, so
    a slow or stalled clamd cannot keep resetting the clock and run forever.
    """

    def __init__(
        self,
        host: str,
        port: int,
        timeout: float = 60.0,
        connect_timeout: float | None = None,
    ) -> None:
        # A None/0 timeout would silently put the socket into blocking-forever
        # or non-blocking mode, defeating the whole point — fail loudly instead.
        if not timeout or timeout <= 0:
            raise ValueError(
                f"clamav timeout must be positive, got {timeout!r}")
        self._host = host
        self._port = port
        self._timeout = float(timeout)
        # Connecting to an unreachable/filtered clamd should fail fast rather
        # than burn the whole scan budget, so cap the connect phase separately.
        # NOTE: this cap applies PER resolved address inside create_connection,
        # so worst case is connect_timeout * (number of A/AAAA records).
        if connect_timeout is None:
            connect_timeout = min(self._timeout, 5.0)
        if connect_timeout <= 0:
            raise ValueError(
                f"clamav connect_timeout must be positive, got {connect_timeout!r}"
            )
        self._connect_timeout = float(connect_timeout)

    # -- connection helpers ------------------------------------------------- #

    def _arm(self, sock: socket.socket, deadline: float) -> None:
        """Set the socket timeout to the time remaining before ``deadline``."""
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ClamAVError(
                "clamd scan exceeded timeout budget",
                error="clamav_timeout",
                http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        sock.settimeout(remaining)

    def _connect(self, deadline: float) -> socket.socket:
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ClamAVError(
                "clamd timeout budget exhausted before connect",
                error="clamav_timeout",
                http_status=status.HTTP_504_GATEWAY_TIMEOUT,
            )
        try:
            sock = socket.create_connection(
                (self._host, self._port),
                timeout=min(self._connect_timeout, remaining),
            )
        except OSError as exc:
            raise ClamAVError(
                f"Cannot connect to clamd at {self._host}:{self._port}",
                error="clamav_unreachable",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        return sock

    def _read_reply(self, sock: socket.socket, deadline: float) -> str:
        buf = bytearray()
        while True:
            self._arm(sock, deadline)
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
        deadline = time.monotonic() + self._timeout
        sock = self._connect(deadline)
        try:
            self._arm(sock, deadline)
            sock.sendall(b"zPING\x00")
            reply = self._read_reply(sock, deadline)
        except OSError as exc:
            raise ClamAVError(
                "clamd ping failed",
                error="clamav_ping_failed",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        finally:
            sock.close()
        return reply == "PONG"

    def scan_stream(self, data: bytes | bytearray | BinaryIO) -> ClamAVScanResult:
        """Scan ``data`` (bytes or a binary file-like) via INSTREAM."""
        payload = data.read() if hasattr(data, "read") else data  # type: ignore

        if not isinstance(payload, (bytes, bytearray)):
            raise TypeError("data must be bytes or a binary file-like object")

        # Per-phase timing so we can see where wall-clock time actually goes
        # (connect vs send vs recv). Logged at DEBUG on every scan.
        t0 = time.monotonic()
        deadline = t0 + self._timeout
        sock = self._connect(deadline)
        t_connected = time.monotonic()
        try:
            self._arm(sock, deadline)
            sock.sendall(b"zINSTREAM\x00")
            view = memoryview(bytes(payload))
            for start in range(0, len(view), _CHUNK_SIZE):
                chunk = view[start:start + _CHUNK_SIZE]
                self._arm(sock, deadline)
                sock.sendall(struct.pack("!I", len(chunk)))
                sock.sendall(chunk)
            self._arm(sock, deadline)
            sock.sendall(_END_CHUNK)
            t_sent = time.monotonic()
            raw = self._read_reply(sock, deadline)
            t_replied = time.monotonic()
        except OSError as exc:
            # clamd closes the socket mid-stream when StreamMaxLength is
            # exceeded; treat any I/O failure as a scan error.
            raise ClamAVError(
                "clamd connection failed during scan",
                error="clamav_connection_interrupted",
                http_status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            ) from exc
        finally:
            sock.close()

        log.debug(
            "clamd scan phases: connect=%.3fs send=%.3fs recv=%.3fs total=%.3fs "
            "(payload=%d bytes, timeout=%.1fs)",
            t_connected - t0,
            t_sent - t_connected,
            t_replied - t_sent,
            t_replied - t0,
            len(payload),
            self._timeout,
        )
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
    A positive detection raises ``AppError``. If the scanner is unreachable
    or errors out we currently return ``None`` (fail open) and log a warning.
    """
    client = ClamAVClient(
        settings.clamav_host,
        settings.clamav_port,
        timeout=settings.clamav_timeout,
    )

    start = time.monotonic()
    try:
        result = client.scan_stream(raw)
    except ClamAVError as exc:
        elapsed = time.monotonic() - start
        log.warning(
            "ClamAV scan failed after %.3fs (timeout=%s): %s",
            elapsed,
            settings.clamav_timeout,
            exc,
        )

        # scan could not be performed, return no result
        return None

    # Malware found, reject
    if not result.clean:
        raise AppError(
            f"Malware detected: {result.signature}",
            error="invalid_file",
            http_status=400,
        )

    # return scan result
    return result
