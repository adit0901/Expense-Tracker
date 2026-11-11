from __future__ import annotations

import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.enums import CategoryKind

COLOR_PATTERN = r"^#[0-9A-Fa-f]{6}$"


def _strip(v: str | None) -> str | None:
    return v.strip() if isinstance(v, str) else v


class CategoryCreate(BaseModel):
    kind: CategoryKind
    name: str = Field(min_length=1, max_length=60)
    parent_id: uuid.UUID | None = None
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)
    icon: str | None = Field(default=None, max_length=40)
    is_essential: bool = False

    _s = field_validator("name")(_strip)


class CategoryUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=60)
    color: str | None = Field(default=None, pattern=COLOR_PATTERN)
    icon: str | None = Field(default=None, max_length=40)
    is_essential: bool | None = None

    _s = field_validator("name")(_strip)


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: CategoryKind
    name: str
    parent_id: uuid.UUID | None
    color: str | None
    icon: str | None
    is_essential: bool
    is_system: bool


class CategoryDeleteResult(BaseModel):
    deleted_ids: list[uuid.UUID]
    reassigned_transactions: int
    replacement_id: uuid.UUID | None
