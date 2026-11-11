"""Pagination and sort helpers shared by collection endpoints."""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import Query
from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import AppError
from app.core.responses import PageEnvelope, PageMeta

MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 25


@dataclass(frozen=True)
class PageParams:
    page: int
    page_size: int

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[
        int,
        Query(ge=1, le=MAX_PAGE_SIZE, description=f"Items per page (max {MAX_PAGE_SIZE})"),
    ] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


def parse_sort(
    sort: str | None,
    allowed: Mapping[str, ColumnElement[Any] | Any],
    default: Sequence[Any],
) -> list[Any]:
    """Translate `sort=-date,amount` into ORDER BY clauses using an allow-list."""
    if not sort:
        return list(default)
    clauses: list[Any] = []
    for raw in sort.split(","):
        token = raw.strip()
        desc = token.startswith("-")
        name = token.lstrip("-+")
        if name not in allowed:
            raise AppError(
                f"Sorting by '{name}' is not allowed",
                code="invalid_sort",
                status_code=422,
                details=[{"field": "sort", "allowed": sorted(allowed)}],
            )
        col = allowed[name]
        clauses.append(col.desc() if desc else col.asc())
    return clauses


def build_meta(params: PageParams, total: int) -> PageMeta:
    return PageMeta(
        page=params.page,
        page_size=params.page_size,
        total_items=total,
        total_pages=math.ceil(total / params.page_size) if total else 0,
    )


def paginate[T](db: Session, stmt: Select[Any], params: PageParams) -> tuple[list[Any], PageMeta]:
    total = db.scalar(select(func.count()).select_from(stmt.order_by(None).subquery())) or 0
    rows = list(db.scalars(stmt.limit(params.page_size).offset(params.offset)))
    return rows, build_meta(params, total)


def page_envelope[T](items: list[T], meta: PageMeta) -> PageEnvelope[T]:
    return PageEnvelope[T](data=items, meta=meta)
