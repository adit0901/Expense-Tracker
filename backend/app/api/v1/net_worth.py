"""API endpoints for net worth, snapshots, and metrics."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.responses import Envelope, ok
from app.schemas.net_worth import (
    EmergencyFundMetricsOut,
    NetWorthOut,
    NetWorthSnapshotCreate,
    NetWorthSnapshotOut,
)
from app.services import net_worth as net_worth_service

router = APIRouter(tags=["net-worth"])


@router.get("/net-worth")
def get_net_worth(
    user: CurrentUser,
    db: DbSession,
    as_of: Annotated[date | None, Query(description="As of date (YYYY-MM-DD)")] = None,
) -> Envelope[NetWorthOut]:
    return ok(net_worth_service.get_net_worth(db, user.id, as_of))


@router.get("/net-worth/snapshots")
def list_snapshots(
    user: CurrentUser,
    db: DbSession,
) -> Envelope[list[NetWorthSnapshotOut]]:
    return ok(net_worth_service.list_snapshots(db, user.id))


@router.post("/net-worth/snapshots", status_code=status.HTTP_201_CREATED)
def create_snapshot(
    user: CurrentUser,
    db: DbSession,
    payload: NetWorthSnapshotCreate | None = None,
) -> Envelope[NetWorthSnapshotOut]:
    target_date = payload.as_of if payload else None
    return ok(net_worth_service.create_snapshot(db, user.id, target_date))


@router.post("/net-worth/snapshots/{as_of}/recompute")
def recompute_snapshot(
    as_of: date,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[NetWorthSnapshotOut]:
    return ok(net_worth_service.recompute_snapshot(db, user.id, as_of))


@router.get("/metrics/emergency-fund", tags=["metrics"])
def get_emergency_fund_metric(
    user: CurrentUser,
    db: DbSession,
    as_of: Annotated[date | None, Query(description="As of date")] = None,
) -> Envelope[EmergencyFundMetricsOut]:
    return ok(net_worth_service.get_emergency_fund_metrics(db, user.id, as_of))
