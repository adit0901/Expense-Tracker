"""Financial accounts endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, Query, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.pagination import PageParams, page_params
from app.core.responses import Envelope, PageEnvelope, ok
from app.models.enums import AccountType
from app.schemas.accounts import AccountCreate, AccountOut, AccountsSummary, AccountUpdate
from app.services import accounts as svc

router = APIRouter(prefix="/accounts", tags=["accounts"])


@router.get("")
def list_accounts(
    user: CurrentUser,
    db: DbSession,
    params: Annotated[PageParams, Depends(page_params)],
    include_archived: bool = False,
    type: Annotated[AccountType | None, Query()] = None,
    sort: str | None = None,
) -> PageEnvelope[AccountOut]:
    items, meta = svc.list_accounts(
        db, user.id, params, include_archived=include_archived, account_type=type, sort=sort
    )
    return PageEnvelope[AccountOut](data=items, meta=meta)


@router.get("/summary")
def accounts_summary(user: CurrentUser, db: DbSession) -> Envelope[AccountsSummary]:
    return ok(svc.summary(db, user.id))


@router.post("", status_code=status.HTTP_201_CREATED)
def create_account(body: AccountCreate, user: CurrentUser, db: DbSession) -> Envelope[AccountOut]:
    return ok(svc.create_account(db, user.id, body))


@router.get("/{account_id}")
def get_account(account_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Envelope[AccountOut]:
    return ok(svc.get_account(db, user.id, account_id))


@router.patch("/{account_id}")
def update_account(
    account_id: uuid.UUID, body: AccountUpdate, user: CurrentUser, db: DbSession
) -> Envelope[AccountOut]:
    return ok(svc.update_account(db, user.id, account_id, body))


@router.post("/{account_id}/archive")
def archive_account(
    account_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> Envelope[AccountOut]:
    return ok(svc.archive_account(db, user.id, account_id))


@router.post("/{account_id}/unarchive")
def unarchive_account(
    account_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> Envelope[AccountOut]:
    return ok(svc.unarchive_account(db, user.id, account_id))


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_account(account_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    svc.delete_account(db, user.id, account_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
