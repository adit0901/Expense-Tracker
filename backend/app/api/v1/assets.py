"""Assets and liabilities API router."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.responses import Envelope, ok
from app.schemas.asset import (
    AssetCloseIn,
    AssetCreate,
    AssetOut,
    AssetUpdate,
    AssetValuationIn,
    AssetValuationOut,
    LiabilityBalanceIn,
    LiabilityBalanceOut,
    LiabilityCloseIn,
    LiabilityCreate,
    LiabilityOut,
    LiabilityUpdate,
)
from app.services import assets as svc

router = APIRouter(tags=["assets-and-liabilities"])


# --- Assets ---


@router.get("/assets")
def list_assets(
    user: CurrentUser,
    db: DbSession,
    as_of: Annotated[date | None, Query()] = None,
    include_closed: Annotated[bool, Query()] = False,
) -> Envelope[list[AssetOut]]:
    return ok(svc.list_assets(db, user.id, as_of=as_of, include_closed=include_closed))


@router.post("/assets", status_code=status.HTTP_201_CREATED)
def create_asset(
    body: AssetCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[AssetOut]:
    return ok(svc.create_asset(db, user.id, body))


@router.get("/assets/{id}")
def get_asset(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    as_of: Annotated[date | None, Query()] = None,
) -> Envelope[AssetOut]:
    return ok(svc.get_asset(db, user.id, id, as_of=as_of))


@router.patch("/assets/{id}")
def update_asset(
    id: uuid.UUID,
    body: AssetUpdate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[AssetOut]:
    return ok(svc.update_asset(db, user.id, id, body))


@router.post("/assets/{id}/close")
def close_asset(
    id: uuid.UUID,
    body: AssetCloseIn,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[AssetOut]:
    return ok(svc.close_asset(db, user.id, id, body))


@router.get("/assets/{id}/valuations")
def list_valuations(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[list[AssetValuationOut]]:
    return ok(svc.list_valuations(db, user.id, id))


@router.post("/assets/{id}/valuations", status_code=status.HTTP_201_CREATED)
def add_valuation(
    id: uuid.UUID,
    body: AssetValuationIn,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[AssetValuationOut]:
    return ok(svc.add_valuation(db, user.id, id, body))


# --- Liabilities ---


@router.get("/liabilities")
def list_liabilities(
    user: CurrentUser,
    db: DbSession,
    as_of: Annotated[date | None, Query()] = None,
    include_closed: Annotated[bool, Query()] = False,
) -> Envelope[list[LiabilityOut]]:
    return ok(
        svc.list_liabilities(
            db, user.id, as_of=as_of, include_closed=include_closed
        )
    )


@router.post("/liabilities", status_code=status.HTTP_201_CREATED)
def create_liability(
    body: LiabilityCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LiabilityOut]:
    return ok(svc.create_liability(db, user.id, body))


@router.get("/liabilities/{id}")
def get_liability(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    as_of: Annotated[date | None, Query()] = None,
) -> Envelope[LiabilityOut]:
    return ok(svc.get_liability(db, user.id, id, as_of=as_of))


@router.patch("/liabilities/{id}")
def update_liability(
    id: uuid.UUID,
    body: LiabilityUpdate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LiabilityOut]:
    return ok(svc.update_liability(db, user.id, id, body))


@router.post("/liabilities/{id}/close")
def close_liability(
    id: uuid.UUID,
    body: LiabilityCloseIn,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LiabilityOut]:
    return ok(svc.close_liability(db, user.id, id, body))


@router.get("/liabilities/{id}/balances")
def list_balances(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[list[LiabilityBalanceOut]]:
    return ok(svc.list_balances(db, user.id, id))


@router.post("/liabilities/{id}/balances", status_code=status.HTTP_201_CREATED)
def add_balance(
    id: uuid.UUID,
    body: LiabilityBalanceIn,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LiabilityBalanceOut]:
    return ok(svc.add_balance(db, user.id, id, body))

