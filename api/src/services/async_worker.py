"""Queue handler start-up mode.

A simple, durable worker: it claims one job at a time from the PostgreSQL
``jobs`` table using ``FOR UPDATE SKIP LOCKED`` (so multiple horizontally-scaled
queue containers never grab the same job), runs the registered handler, and
records the outcome. No in-container worker pool — scale by adding containers.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import signal
import socket
import time
from collections.abc import Callable
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from src.config import settings
from src.core.db import SessionLocal
from src.jobs.models import Job
from src.logger import configure_logger

log = logging.getLogger("app.worker")

# Handlers are registered by feature modules in later steps, e.g. invoice
# generation. Each takes the job payload and returns a JSON-serialisable result.
JobHandler = Callable[[dict[str, Any]], dict[str, Any] | None]
_HANDLERS: dict[str, JobHandler] = {}

POLL_INTERVAL_SECONDS = 2.0
_shutdown = False


def register_handler(job_type: str, handler: JobHandler) -> None:
    _HANDLERS[job_type] = handler


def _worker_id() -> str:
    return f"{socket.gethostname()}:{os.getpid()}"


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


def _claim_one(db: Session, worker_id: str) -> Job | None:
    stmt = (
        select(Job)
        .where(
            Job.status == "queued",
            Job.available_at <= _now(),
        )
        .order_by(Job.available_at.asc())
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    job = db.execute(stmt).scalars().first()
    if job is None:
        return None
    job.status = "running"
    job.locked_at = _now()
    job.locked_by = worker_id
    job.attempts += 1
    db.flush()
    return job


def _run_job(db: Session, job: Job) -> None:
    handler = _HANDLERS.get(job.type)
    if handler is None:
        job.status = "failed"
        job.error = f"no handler registered for job type '{job.type}'"
        log.error(job.error)
        return
    try:
        result = handler(job.payload or {})
        job.status = "succeeded"
        job.result = result or {}
        job.error = None
    except Exception as exc:  # noqa: BLE001 - record any handler failure
        log.exception("job %s (%s) failed", job.id, job.type)
        if job.attempts >= job.max_attempts:
            job.status = "failed"
            job.error = str(exc)
        else:
            # Re-queue with a simple linear backoff.
            job.status = "queued"
            job.locked_at = None
            job.locked_by = None
            job.available_at = _now() + dt.timedelta(seconds=30 * job.attempts)
            job.error = str(exc)


def _install_signal_handlers() -> None:
    def _handle(exit_code: int, _frame):  # type: ignore
        global _shutdown
        log.info("received signal %s, shutting down after current job", exit_code)
        _shutdown = True

    signal.signal(signal.SIGTERM, _handle)  # type: ignore
    signal.signal(signal.SIGINT, _handle)  # type: ignore


def run() -> None:
    configure_logger(settings.log_level)
    _install_signal_handlers()
    worker_id = _worker_id()
    log.info("queue handler started (%s); %d handler(s) registered",
             worker_id, len(_HANDLERS))

    while not _shutdown:
        with SessionLocal() as db:
            try:
                job = _claim_one(db, worker_id)
                if job is None:
                    db.commit()
                    time.sleep(POLL_INTERVAL_SECONDS)
                    continue
                job_id = job.id
                db.commit()  # release the row lock; job is marked running

                _run_job(db, job)
                db.commit()
                log.info("job %s finished with status=%s", job_id, job.status)
            except Exception:
                db.rollback()
                log.exception("worker loop error")
                time.sleep(POLL_INTERVAL_SECONDS)

    log.info("queue handler stopped")
