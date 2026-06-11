"""Shared Pydantic schema building blocks."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

Locale = Literal["de", "en"]
Currency = Literal["EUR"]


class CamelModel(BaseModel):
    """Base for API models that serialise/accept camelCase JSON keys.

    Fields are declared in snake_case but read and written as camelCase (e.g.
    ``first_name`` <-> ``firstName``). ``populate_by_name`` also allows the
    snake_case name on input.
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        extra="ignore",
        from_attributes=True,
    )


class MultiLanguageLabel(BaseModel):
    de: str | None = None
    en: str | None = None
