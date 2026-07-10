"""Logging configuration.

Defaults to structured JSON on stdout so a log collector (or OpenObserve's
own collector) can ingest it directly. When ``OPENOBSERVE_URL`` is configured,
a non-blocking background handler also ships logs to OpenObserve's bulk-ingest
HTTP API. Shipping happens on a daemon thread with a bounded queue, so logging
never blocks request handling and failures are best-effort.
"""

from __future__ import annotations

import contextlib
import datetime as dt
import json
import logging
import queue
import sys
import threading
import urllib.request

from src.config import settings

# Standard LogRecord attributes we don't want to duplicate into the JSON body.
_RESERVED = set(logging.LogRecord("", 0, "", 0, "", None, None).__dict__.keys()) | {
    "message",
    "asctime",
    "taskName",
}


class JsonFormatter(logging.Formatter):
    """Render each record as a single JSON line with service metadata."""

    def __init__(self, service: str, environment: str) -> None:
        super().__init__()
        self._service = service
        self._environment = environment

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "_timestamp": dt.datetime.fromtimestamp(record.created, dt.UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "service": self._service,
            "environment": self._environment,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Include any structured extras passed via logger.info(..., extra={...}).
        for key, value in record.__dict__.items():
            if key not in _RESERVED and not key.startswith("_"):
                payload[key] = value
        return json.dumps(payload, default=str)


class OpenObserveHandler(logging.Handler):
    """Best-effort, non-blocking log shipping to OpenObserve.

    Records are placed on a bounded queue and flushed in batches by a daemon
    thread to the ``/_json`` bulk endpoint. If the queue is full or the network
    fails, records are dropped rather than blocking the application.
    """

    def __init__(
        self,
        *,
        base_url: str,
        organization: str,
        stream: str,
        token: str | None,
        formatter: logging.Formatter,
        batch_size: int = 50,
        flush_interval: float = 2.0,
    ) -> None:
        super().__init__()
        self._endpoint = f"{base_url.rstrip('/')}/api/{organization}/{stream}/_json"
        self._token = token
        self._batch_size = batch_size
        self._flush_interval = flush_interval
        self._queue: queue.Queue[str] = queue.Queue(maxsize=10_000)
        self.setFormatter(formatter)
        self._thread = threading.Thread(
            target=self._run, daemon=True, name="openobserve-log")
        self._thread.start()

    def emit(self, record: logging.LogRecord) -> None:
        # Drop under back-pressure; stdout still has the record.
        with contextlib.suppress(queue.Full):
            self._queue.put_nowait(self.format(record))

    def _run(self) -> None:
        import time

        batch: list[str] = []
        last = time.monotonic()
        while True:
            timeout = max(0.0, self._flush_interval -
                          (time.monotonic() - last))
            with contextlib.suppress(queue.Empty):
                batch.append(self._queue.get(timeout=timeout))
            if batch and (
                len(batch) >= self._batch_size or time.monotonic() -
                    last >= self._flush_interval
            ):
                self._ship(batch)
                batch = []
                last = time.monotonic()

    def _ship(self, batch: list[str]) -> None:
        try:
            body = ("[" + ",".join(batch) + "]").encode()
            req = urllib.request.Request(
                self._endpoint, data=body, headers={
                    "Content-Type": "application/json"}
            )
            if self._token:
                req.add_header("Authorization", f"Basic {self._token}")
            urllib.request.urlopen(req, timeout=5)  # noqa: S310 - configured internal URL
        except Exception:  # noqa: BLE001 - shipping is best-effort
            pass


# save if logging has been configured to prevent the setup from being run twice
_logging_configured: bool = False


def configure_logger(level: str | None = None) -> None:
    global _logging_configured
    if _logging_configured is True:
        return

    level = (level or settings.log_level).upper()
    if settings.api_log_format == "json":
        formatter: logging.Formatter = JsonFormatter(
            settings.api_service_name, settings.environment)
    else:
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)-8s %(name)s :: %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        )

    handlers: list[logging.Handler] = []
    stdout = logging.StreamHandler(sys.stdout)
    stdout.setFormatter(formatter)
    handlers.append(stdout)

    if settings.openobserve_url:
        handlers.append(
            OpenObserveHandler(
                base_url=settings.openobserve_url,
                organization=settings.openobserve_organization,
                stream=settings.openobserve_stream,
                token=settings.openobserve_token,
                formatter=formatter,
            )
        )

    root = logging.getLogger()
    root.handlers.clear()
    for h in handlers:
        root.addHandler(h)
    root.setLevel(level)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

    # mark as configuration successful
    _logging_configured = True
