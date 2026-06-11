"""Smoke-test start-up mode.

Runs the end-to-end smoke suites (``scripts/smoke_*.py``) in-process against the
configured database — one container, one command, exactly like the web mode:

    python -m src smoke

Each suite seeds its own data and drives the FastAPI app via ``TestClient``
(no network listener), printing ``[PASS]/[FAIL]`` lines and a per-suite summary.
The process exits non-zero if any suite fails, so this mode works as a CI gate
or a post-deploy verification job.

Because the suites *write* to the database, this mode refuses to run against a
production database unless ``SMOKE_ALLOW_PRODUCTION=1`` is set explicitly.
"""

from __future__ import annotations

import importlib.util
import logging
import os
from pathlib import Path
from typing import Any

from src.config import settings
from src.logger import configure_logger

log = logging.getLogger("app.smoke")

# scripts/ sits next to src/ at the repo / image root (see Dockerfile COPY).
_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"


def _discover() -> list[Path]:
    if not _SCRIPTS_DIR.is_dir():
        return []
    return sorted(_SCRIPTS_DIR.glob("smoke_*.py"))


def _run_suite(path: Path) -> int:
    """Load a suite module by path and invoke its ``main() -> int``."""
    spec = importlib.util.spec_from_file_location(f"_smoke_{path.stem}", path)
    if spec is None or spec.loader is None:
        log.error("could not load smoke suite: %s", path.name)
        return 1
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    entry: Any = getattr(module, "main", None)
    if not callable(entry):
        log.error("smoke suite %s has no main() entry point", path.name)
        return 1
    result: Any = entry()
    return int(result or 0)


def run() -> int:
    configure_logger(settings.log_level)

    if settings.is_production and os.getenv("SMOKE_ALLOW_PRODUCTION") != "1":
        log.error(
            "refusing to run smoke suites against a production database; "
            "set SMOKE_ALLOW_PRODUCTION=1 to override"
        )
        return 2

    suites = _discover()
    if not suites:
        log.error("no smoke suites found in %s", _SCRIPTS_DIR)
        return 1

    failures: list[str] = []
    for path in suites:
        log.info("running smoke suite: %s", path.name)
        try:
            code = _run_suite(path)
        except Exception:
            # Report and keep going so one broken suite can't mask the others.
            log.exception("smoke suite crashed: %s", path.name)
            failures.append(path.name)
            continue
        if code != 0:
            failures.append(path.name)

    if failures:
        log.error(
            "smoke FAILED (%d/%d suites failed): %s",
            len(failures),
            len(suites),
            ", ".join(failures),
        )
        return 1

    log.info("smoke OK (%d suites passed)", len(suites))
    return 0
