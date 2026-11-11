"""Success envelope models: {"data": ..., "meta": {...}}."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class Envelope[T](BaseModel):
    data: T
    meta: dict[str, Any] = Field(default_factory=dict)


class PageMeta(BaseModel):
    page: int
    page_size: int
    total_items: int
    total_pages: int


class PageEnvelope[T](BaseModel):
    data: list[T]
    meta: PageMeta


def ok[T](data: T, **meta: Any) -> Envelope[T]:
    return Envelope[T](data=data, meta=meta)
