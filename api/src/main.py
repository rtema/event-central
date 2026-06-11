"""Single entry point that dispatches to one of the start-up modes.

    python -m src web        # FastAPI web request handler (default)
    python -m src queue      # queue handler
    python -m src migrate    # run DB migrations to head, then exit
    python -m src backup     # dump DB to object storage, then exit
    python -m src restore --key backups/event-central-....dump

One container image, one process per container; scale horizontally by running
more replicas of a given mode.
"""

from __future__ import annotations

import argparse
import os
import sys

from src.config import settings


def _run_web() -> None:
    import uvicorn

    # A single worker per container; scaling is done by adding containers.
    uvicorn.run(
        "src.services.web:app",
        host=settings.host,
        port=settings.port,
        workers=1,
        log_level=settings.log_level.lower(),
    )


# def _run_migrate() -> None:
#     from alembic import command
#     from alembic.config import Config

#     configure_logger(settings.log_level)
#     cfg = Config("alembic.ini")
#     cfg.set_main_option("sqlalchemy.url", settings.database_url)
#     command.upgrade(cfg, "head")

def _run_seed(email: str | None, password: str | None) -> None:
    from src.services import seed

    seed.run(email, password)


# def _run_queue() -> None:
#     from src import worker

#     worker.run()


# def _run_backup() -> None:
#     from src.services import backup

#     backup.run()


# def _run_restore(key: str | None) -> None:
#     from src.services import restore

#     restore.run(key or os.getenv("RESTORE_KEY", ""))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="event-central")
    mode_parser = parser.add_subparsers(dest="mode")

    # Mode: web
    mode_parser.add_parser("web", help="Run the web request handler")

    # Mode: seed
    seed_parser = mode_parser.add_parser(
        "seed", help="Create an initial admin account")
    seed_parser.add_argument(
        "--email", help="Email of the admin")
    seed_parser.add_argument(
        "--password", help="Password of the admin")

    # Mode: queue
    mode_parser.add_parser("queue", help="Run the queue handler")

    # Mode: migrate
    mode_parser.add_parser(
        "migrate", help="Apply database migrations and exit")

    # Mode: backup
    mode_parser.add_parser(
        "backup", help="Back up the database to object storage and exit")

    # Mode: restore
    restore_parser = mode_parser.add_parser(
        "restore", help="Restore the database from object storage")
    restore_parser.add_argument(
        "--key", help="Object storage key of the backup to restore")

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Allow APP_MODE env var as a fallback (handy for some orchestrators).
    mode = args.mode or os.getenv("APP_MODE", "web")

    # handler without args
    dispatch = {
        "web": _run_web,
        # "queue": _run_queue,
        # "migrate": _run_migrate,
        # "backup": _run_backup,
    }

    # Handler with args
    if mode == "seed":
        _run_seed(
            getattr(args, "email", None),
            getattr(args, "password", None)
        )
        return
    # if mode == "restore":
    #     _run_restore(getattr(args, "key", None))
    #     return
    handler = dispatch.get(mode)
    if handler is None:
        parser.print_help()
        sys.exit(2)
    handler()


if __name__ == "__main__":
    main()
