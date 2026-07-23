"""OAuth scope catalogue and matching.

Scopes follow the pattern ``<resource>:<action>:<qualifier>`` 
where the qualifier is one of ``all``, ``own`` or a concrete ``{eventId}``. 
A granted ``:all`` scope satisfies any ``:own`` or ``:{eventId}`` 
requirement for the same resource/action.
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from src.events.service import get_event_ids

# --------------------------------------------------------------------------- #
# IMPORTANT:
# Prevent any event name that is reserved and may lead to the expansion of access rights:
# There fore the scope qualifiers are reserved labels that can NEVER be uses as event ids
# --------------------------------------------------------------------------- #
RESERVED_LABELS = {"all", "own", "read"}

# --------------------------------------------------------------------------- #
# Scope constants
# --------------------------------------------------------------------------- #
# Users
SCOPE_USERS_READ_ALL = "users:read:all"
SCOPE_USERS_WRITE_ALL = "users:write:all"

# Invoices
SCOPE_INVOICES_READ_ALL = "invoices:read:all"
SCOPE_INVOICES_READ_OWN = "invoices:read:own"
SCOPE_INVOICES_WRITE_ALL = "invoices:write:all"
SCOPE_INVOICES_WRITE_OWN = "invoices:write:own"

# Orders
SCOPE_ORDERS_READ_ALL = "orders:read:all"
SCOPE_ORDERS_READ_OWN = "orders:read:own"
SCOPE_ORDERS_WRITE_ALL = "orders:write:all"
SCOPE_ORDERS_WRITE_OWN = "orders:write:own"

# Events
SCOPE_EVENTS_READ_ALL = "events:read:all"
SCOPE_EVENTS_READ_OWN = "events:read:own"
SCOPE_EVENTS_WRITE_ALL = "events:write:all"
SCOPE_EVENTS_WRITE_OWN = "events:write:own"

# Payments
SCOPE_PAYMENTS_READ_ALL = "payments:read:all"
SCOPE_PAYMENTS_READ_OWN = "payments:read:own"
SCOPE_PAYMENTS_WRITE_ALL = "payments:write:all"
SCOPE_PAYMENTS_WRITE_OWN = "payments:write:own"

# Files
SCOPE_FILES_READ_ALL = "files:read:all"
SCOPE_FILES_WRITE_ALL = "files:write:all"

# Emails (read-only, reserved for a later feature)
SCOPE_EMAILS_READ_ALL = "emails:read:all"

# Backend / misc data (document templates, taxes, scope catalogue, ...)
SCOPE_BACKEND_READ_ALL = "backend:read:all"
SCOPE_BACKEND_WRITE_ALL = "backend:write:all"


@dataclass(frozen=True, slots=True)
class ScopeDef:
    """A documented scope and its human-readable labels (for /api/v1/scopes)."""

    scope: str
    de: str
    en: str


# Resources that follow the read/write × all/own/{eventId} matrix, with the
# plural noun used to render labels.
_RESOURCE_LABELS = {
    "invoices": ("Rechnungen", "invoices"),
    "orders": ("Bestellungen", "orders"),
    "events": ("Events", "events"),
    "payments": ("Zahlungen", "payments"),
}
_ACTION_LABELS = {
    "read": ("Zugriff auf", "Allow access to"),
    "write": ("Bearbeiten/erstellen von", "Allow creation/modification of"),
}


def _qualifier_phrase(
    resource: str, qualifier: str, de_plural: str, en_plural: str
) -> tuple[str, str]:
    if qualifier == "all":
        return f"alle {de_plural}", f"all {en_plural}"
    if qualifier == "own":
        return f"eigene {de_plural}", f"{en_plural} created by the user/app"
    # Per-event variant ({eventId}); events read as a single specific event.
    if resource == "events":
        return "ein bestimmtes Event", "a specific event"
    return f"{de_plural} eines Events", f"{en_plural} associated with an event"


def build_scope_catalogue(
    db: Session, *, include_dynamic: bool = True
) -> list[ScopeDef]:
    out: list[ScopeDef] = [
        ScopeDef(SCOPE_USERS_READ_ALL, "Zugriff auf alle Nutzer",
                 "Allow access to all users"),
        ScopeDef(
            SCOPE_USERS_WRITE_ALL, "Bearbeiten/erstellen von allen Nutzern",
            "Allow creation/modification of all users"
        ),
    ]

    # get qualifiers
    qualifiers: list[str] = ["all", "own"]


    # get list of events
    if(include_dynamic):
        event_ids = get_event_ids(db)

        # append event qualifiers
        qualifiers += event_ids

    for resource, (de_plural, en_plural) in _RESOURCE_LABELS.items():
        for action, (de_verb, en_verb) in _ACTION_LABELS.items():
            for qualifier in qualifiers:
                de_q, en_q = _qualifier_phrase(
                    resource, qualifier, de_plural, en_plural)
                out.append(
                    ScopeDef(
                        f"{resource}:{action}:{qualifier}",
                        f"{de_verb} {de_q}",
                        f"{en_verb} {en_q}",
                    )
                )
    
    # all 
    out.append(
        ScopeDef(SCOPE_EMAILS_READ_ALL, "Zugriff auf alle E-Mails",
                 "Allow access to all emails")
    )
    out.append(
        ScopeDef(
            SCOPE_BACKEND_READ_ALL,
            "Backend-Daten lesen",
            "Read misc data necessary to access the backend",
        )
    )
    out.append(
        ScopeDef(
            SCOPE_BACKEND_WRITE_ALL,
            "Backend-Daten schreiben",
            "Write misc data necessary to access the backend",
        )
    )
    out.append(
        ScopeDef(
            SCOPE_FILES_READ_ALL,
            "Dateien ansehen",
            "View uploaded files",
        )
    )
    out.append(
        ScopeDef(
            SCOPE_FILES_WRITE_ALL,
            "Dateien hochladen/editieren",
            "Upload files / update files",
        )
    )
    return out


def build_scope(resource: str, action: str, qualifier: str) -> str:
    """Build a concrete scope, e.g. ``invoices:read:tema-2026`` or ``invoices:read:all``."""
    return f"{resource}:{action}:{qualifier}"


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
