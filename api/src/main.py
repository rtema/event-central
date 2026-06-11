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
from src.logger import configure_logger


def _run_web() -> None:
    import uvicorn

    # A single worker per container; scaling is done by adding containers.
    uvicorn.run(
        "src.web:app",
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
    """Create an initial admin account.

    This grants a full set of resource-wide admin scopes and adds a
    password login.

    Idempotent: re-running with the same email won't duplicate the user or its
    scope grants. A password method is added when one is supplied, or generated
    for a brand-new admin so the account is immediately usable.
    """
    import logging
    import secrets

    from sqlalchemy import select

    from src.auth.service import active_scopes_for_user
    from src.core.db import SessionLocal
    from src.core.scopes import SCOPE_CATALOGUE
    from src.users import service as users_service
    from src.users.models import User, UserScope

    configure_logger(settings.log_level)
    log = logging.getLogger("src.seed")

    email = email or os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")

    # Resource-wide admin scopes. A granted ":all" already satisfies ":own" and
    # ":{eventId}", so we only need the ":all" grants plus the backend flags.
    admin_scopes = sorted(
        s for s in SCOPE_CATALOGUE if s.endswith(":all") or s.startswith("backend:")
    )

    with SessionLocal() as db:
        user = db.execute(select(User).where(User.email == email)).scalars().first()

        created = user is None
        if created:
            user = users_service.create_user(
                db,
                email=email,
                first_name="Admin",
                last_name="User",
                title=None,
                salutation=None,
                actor="seed",
            )
            log.info("created admin user", extra={"user_id": str(user.id), "email": email})
        else:
            log.info("admin user exists", extra={"user_id": str(user.id), "email": email})

        # Grant any missing admin scopes
        owned = active_scopes_for_user(db, user.id)
        for scope in admin_scopes:
            if scope not in owned:
                db.add(UserScope(user_id=user.id, scope=scope, created_by="seed"))
        db.flush()

        # Add a password login: use the supplied password, or generate one for a
        # freshly created admin so the account can be used right away.
        generated: str | None = None
        if password is None and created:
            password = generated = secrets.token_urlsafe(18)
        if password is not None:
            users_service.create_user_auth(
                db, user.id, method="password", secret=password, actor="seed"
            )

        db.commit()

    log.info("seed complete", extra={"email": email, "scope_count": len(admin_scopes)})

    # Print the generated credential to stdout — not via the logger, which may
    # ship to a log aggregator — so the operator can capture it once.
    if generated:
        print(
            f"\nAdmin account ready:\n  email:    {email}\n"
            f"  password: {generated}\n\nStore this now; it will not be shown again.\n"
        )
    elif created:
        print(f"\nAdmin account ready: {email} (password as supplied).\n")
    else:
        print(f"\nAdmin account updated: {email}.\n")



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
    sub = parser.add_subparsers(dest="mode")
    sub.add_parser("web", help="Run the web request handler")
    seed_parser = sub.add_parser("seed", help="Create an initial admin account")
    seed_parser.add_argument(
        "--email", help="Email of the admin")
    seed_parser.add_argument(
        "--password", help="Password of the admin")
    sub.add_parser("queue", help="Run the queue handler")
    sub.add_parser("migrate", help="Apply database migrations and exit")
    sub.add_parser(
        "backup", help="Back up the database to object storage and exit")
    restore_parser = sub.add_parser(
        "restore", help="Restore the database from object storage")
    restore_parser.add_argument(
        "--key", help="Object storage key of the backup to restore")
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    # Allow APP_MODE env var as a fallback (handy for some orchestrators).
    mode = args.mode or os.getenv("APP_MODE", "web")

    dispatch = {
        "web": _run_web,
        # "queue": _run_queue,
        # "migrate": _run_migrate,
        # "backup": _run_backup,
    }
    if mode == "seed":
        _run_seed(getattr(args, "email", None), getattr(args, "password", None))
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
