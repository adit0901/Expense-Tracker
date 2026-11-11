"""Overview dashboard endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.api.v1.periods import PeriodDep, TimezoneDep
from app.core.responses import Envelope, ok
from app.schemas.reports import CategoryBreakdown, Overview, SavingsTrend
from app.services import dashboard as svc

router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/overview")
def overview(
    user: CurrentUser, db: DbSession, period: PeriodDep, tz: TimezoneDep
) -> Envelope[Overview]:
    return ok(svc.overview(db, user.id, period, tz))


@router.get("/trends")
def trends(
    user: CurrentUser,
    db: DbSession,
    period: PeriodDep,
    months: Annotated[int, Query(ge=1, le=36)] = 12,
) -> Envelope[SavingsTrend]:
    return ok(svc.trends(db, user.id, period, months))


@router.get("/category-breakdown")
def category_breakdown(
    user: CurrentUser, db: DbSession, period: PeriodDep
) -> Envelope[CategoryBreakdown]:
    return ok(svc.category_breakdown(db, user.id, period))
