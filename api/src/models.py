"""Import every ORM model so ``Base.metadata`` is complete.

Used by Alembic (autogenerate / migrations) and anywhere the full metadata is
required. Importing this module has the side effect of registering all tables.
"""

from src.auth.models import AuthChallenge, RefreshToken
from src.users.models import User, UserAuth, UserData, UserHistory, UserScope

__all__ = [
    "AuthChallenge",
    "RefreshToken",
    "User",
    "UserAuth",
    "UserScope",
    "UserHistory",
    "UserData",
]
