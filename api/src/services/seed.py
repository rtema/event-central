"""Database restore start-up mode.

Downloads a named backup artifact from object storage and restores it with
``pg_restore``. The artifact key is provided via the ``RESTORE_KEY`` env var or
the ``--key`` CLI argument.
"""

from __future__ import annotations

import logging
import os

from src.config import settings
from src.logger import configure_logger

log = logging.getLogger("app.restore")


def run(email: str | None, password: str | None) -> None:
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
