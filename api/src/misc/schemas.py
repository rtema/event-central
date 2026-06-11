"""Misc API schemas (tag: Misc)."""

from __future__ import annotations

from src.core.schemas import CamelModel, MultiLanguageLabel


class ScopeOut(CamelModel):
    scope: str
    label: MultiLanguageLabel


class ScopesListResponse(CamelModel):
    data: list[ScopeOut]
