"""Database restore start-up mode.

Downloads a named backup artifact from object storage and restores it with
``pg_restore``. The artifact key is provided via the ``RESTORE_KEY`` env var or
the ``--key`` CLI argument.
"""

from __future__ import annotations

import logging
import os

import src.models  # type: ignore # noqa: F401 (import needs to be done here for sqlalchemy to build the full class registry)
from src.config import settings
from src.core.scopes import build_scope_catalogue
from src.logger import configure_logger

log = logging.getLogger("app.restore")


def create_secrets(secret_names: list[str], directory: str) -> bool:
    """Create every necessary secret to start up the development environment.

    For each name in ``list_of_secrets`` a file ``<directory>/<name>`` is
    created containing a freshly generated, URL-safe random token. The file
    names are expected to match the lower-case setting names that
    pydantic-settings reads from ``secrets_dir`` (e.g. ``jwt_secret``,
    ``signed_url_secret``).

    Existing secrets are never overwritten.

    Returns ``True`` only if every requested secret now exists (whether it was
    just created or was already present); ``False`` if anything went wrong,
    e.g. the directory is not writable or a secret name is unsafe.
    """
    import logging
    import os
    from pathlib import Path
    from secrets import token_urlsafe

    configure_logger(settings.log_level)
    log = logging.getLogger("seed")

    target = Path(directory)

    # --- Make sure the target directory exists and is usable ---------------
    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        log.error("cannot create secrets directory %s: %s", target, exc)
        return False

    if not target.is_dir():
        log.error("secrets path %s exists but is not a directory", target)
        return False

    if not os.access(target, os.W_OK | os.X_OK):
        log.error("secrets directory %s is not writable", target)
        return False

    created = 0
    skipped = 0
    failed = 0

    for secret_name in secret_names:
        # Reject names that would escape the directory or aren't a plain file.
        if (not secret_name or secret_name in {".", ".."} or
                "/" in secret_name or "\\" in secret_name):
            log.error("invalid secret name %r, skipping", secret_name)
            failed += 1
            continue

        path = target / secret_name
        if path.exists():
            log.info("secret %r already exists, leaving untouched", secret_name)
            skipped += 1
            continue

        try:
            # O_EXCL: never clobber (also guards against a concurrent writer).
            # mode 0o600: readable/writable by the owner only.
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            try:
                # No trailing newline: the token is the exact secret value.
                os.write(fd, token_urlsafe(32).encode("utf-8"))
            finally:
                os.close(fd)
        except FileExistsError:
            # Lost a race with another writer; treat as "already there".
            log.info("secret %r already exists, leaving untouched", secret_name)
            skipped += 1
            continue
        except OSError as exc:
            log.error("failed to write secret %r: %s", secret_name, exc)
            failed += 1
            continue

        log.info("created secret %r", secret_name)
        created += 1

    log.info(
        "secrets summary: %d created, %d skipped, %d failed (in %s)",
        created,
        skipped,
        failed,
        target,
    )

    # Only proceed if every secret is already set up
    return (failed == 0 and created == 0)


def create_admin_account(email: str | None, password: str | None) -> None:
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
    from src.users import service as users_service
    from src.users.models import User, UserScope

    configure_logger(settings.log_level)
    log = logging.getLogger("seed")

    email = email or os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")

    with SessionLocal() as db:
        # Resource-wide admin scopes. A granted ":all" already satisfies ":own" and
        # ":{eventId}", so we only need the ":all" grants.
        scope_catalogue = build_scope_catalogue(db, include_dynamic=False)
        admin_scopes = sorted(
            s.scope for s in scope_catalogue if s.scope.endswith(":all")
        )

        user = db.execute(select(User).where(
            User.email == email)).scalars().first()

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
            log.info("created admin user", extra={
                     "user_id": str(user.id), "email": email})
        else:
            log.info("admin user exists", extra={
                     "user_id": str(user.id), "email": email})

        # Grant any missing admin scopes
        owned = active_scopes_for_user(db, user.id)
        for scope in admin_scopes:
            if scope not in owned:
                db.add(UserScope(user_id=user.id,
                       scope=scope, created_by="seed"))
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

    log.info("seed complete", extra={
        "email": email, "scope_count": len(admin_scopes)})

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


def run(email: str | None, password: str | None) -> None:
    # create all necessary secrets
    proceed = create_secrets(
        [
            "db_password",
            "api_jwt_secret",
            "api_signed_url_secret",
            "storage_root_key",
            "storage_root_secret",
            "storage_primary_user_key",
            "storage_primary_user_secret",
            "storage_secondary_user_key",
            "storage_secondary_user_secret"
        ],
        "../secrets"
    )

    if not proceed:
        print(
            "[NOT FINISHED] Please start all development containers and restart this script")
        exit(1)

    # initialize the admin account
    proceed = create_admin_account(email, password)
