"""Income sources endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, status

from app.api.deps import CurrentUser, DbSession
from app.core.pagination import PageParams, page_params
from app.core.responses import Envelope, PageEnvelope, ok
from app.schemas.income import IncomeSourceCreate, IncomeSourceOut, IncomeSourceUpdate
from app.services import income as svc

router = APIRouter(prefix="/income-sources", tags=["income"])


@router.get("")
def list_sources(
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends(page_params)],
    include_inactive: bool = False,
    sort: str | None = None,
) -> PageEnvelope[IncomeSourceOut]:
    rows, meta = svc.list_sources(db, user.id, params, include_inactive=include_inactive, sort=sort)
    return PageEnvelope[IncomeSourceOut](
        data=[IncomeSourceOut.model_validate(r) for r in rows], meta=meta
    )


@router.post("", status_code=status.HTTP_201_CREATED)
def create_source(
    body: IncomeSourceCreate, user: CurrentUser, db: DbSession
) -> Envelope[IncomeSourceOut]:
    return ok(IncomeSourceOut.model_validate(svc.create_source(db, user.id, body)))


@router.get("/{source_id}")
def get_source(source_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Envelope[IncomeSourceOut]:
    src = svc.IncomeSourceRepository(db, user.id).get_or_404(source_id)
    return ok(IncomeSourceOut.model_validate(src))


@router.patch("/{source_id}")
def update_source(
    source_id: uuid.UUID, body: IncomeSourceUpdate, user: CurrentUser, db: DbSession
) -> Envelope[IncomeSourceOut]:
    return ok(IncomeSourceOut.model_validate(svc.update_source(db, user.id, source_id, body)))
