"""Transaction categories endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.pagination import PageParams, page_params
from app.core.responses import Envelope, PageEnvelope, ok
from app.models.enums import CategoryKind
from app.schemas.categories import (
    CategoryCreate,
    CategoryDeleteResult,
    CategoryOut,
    CategoryUpdate,
)
from app.services import categories as svc

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("")
def list_categories(
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends(page_params)],
    kind: Annotated[CategoryKind | None, Query()] = None,
    parent_id: uuid.UUID | None = None,
    top_level_only: bool = False,
    sort: str | None = None,
) -> PageEnvelope[CategoryOut]:
    rows, meta = svc.list_categories(
        db,
        user.id,
        params,
        kind=kind,
        parent_id=parent_id,
        top_level_only=top_level_only,
        sort=sort,
    )
    return PageEnvelope[CategoryOut](data=[CategoryOut.model_validate(c) for c in rows], meta=meta)


@router.post("", status_code=status.HTTP_201_CREATED)
def create_category(
    body: CategoryCreate, user: CurrentUser, db: DbSession
) -> Envelope[CategoryOut]:
    return ok(CategoryOut.model_validate(svc.create_category(db, user.id, body)))


@router.get("/{category_id}")
def get_category(category_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Envelope[CategoryOut]:
    return ok(
        CategoryOut.model_validate(svc.CategoryRepository(db, user.id).get_or_404(category_id))
    )


@router.patch("/{category_id}")
def update_category(
    category_id: uuid.UUID, body: CategoryUpdate, user: CurrentUser, db: DbSession
) -> Envelope[CategoryOut]:
    return ok(CategoryOut.model_validate(svc.update_category(db, user.id, category_id, body)))


@router.delete("/{category_id}")
def delete_category(
    category_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    replacement_id: uuid.UUID | None = None,
) -> Envelope[CategoryDeleteResult]:
    return ok(svc.delete_category(db, user.id, category_id, replacement_id))
