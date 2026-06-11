"""OAuth scope catalogue and matching.

Scopes follow the pattern ``<resource>:<action>:<qualifier>`` 
where the qualifier is one of ``all``, ``own`` or a concrete ``{eventId}``. 
A granted ``:all`` scope satisfies any ``:own`` or ``:{eventId}`` 
requirement for the same resource/action.
"""

from __future__ import annotations

SCOPE_USERS_READ_ALL = "users:read:all"
SCOPE_USERS_WRITE_ALL = "users:write:all"


def parse_scope(scope_str: str | None) -> set[str]:
    """Split a space-delimited scope string into a set."""
    if not scope_str:
        return set()
    return {s for s in scope_str.split() if s}


def join_scope(scopes: set[str] | list[str]) -> str:
    return " ".join(sorted(set(scopes)))


def _split(scope: str) -> tuple[str, str, str | None]:
    parts = scope.split(":")
    if len(parts) == 2:
        return parts[0], parts[1], None
    if len(parts) == 3:
        return parts[0], parts[1], parts[2]
    return scope, "", None


def scope_satisfies(granted: str, required: str) -> bool:
    """Does a single ``granted`` scope satisfy a single ``required`` scope?"""
    if granted == required:
        return True
    g_res, g_act, g_qual = _split(granted)
    r_res, r_act, r_qual = _split(required)
    if g_res != r_res or g_act != r_act:
        return False
    # An ``:all`` grant covers ``own`` and any concrete event qualifier.
    return g_qual == "all" and r_qual is not None


def has_scope(granted: set[str], required: str) -> bool:
    """True if any granted scope satisfies the required scope."""
    return any(scope_satisfies(g, required) for g in granted)


def has_any(granted: set[str], required: list[str]) -> bool:
    """True if at least one of the required scopes is satisfied.

    Endpoints in the spec list alternative scopes (read:all / read:own /
    read:{eventId}); satisfying any one of them grants access.
    """
    return any(has_scope(granted, r) for r in required)


def filter_grantable(requested: set[str], owned: set[str]) -> set[str]:
    """Restrict requested scopes to those the actor actually owns.

    If nothing is requested, all owned scopes are granted.
    """
    if not requested:
        return set(owned)
    return {r for r in requested if r in owned or has_scope(owned, r)}
