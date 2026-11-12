"""Budget endpoints: monthly budgets, comparisons, copy forward, alerts."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, DbSession
from app.core.responses import Envelope, ok
from app.schemas.budget import (
    BudgetAlertResponse,
    BudgetComparisonResponse,
    BudgetResponse,
    SetBudgetRequest,
)
from app.services import budgets as svc

router = APIRouter(tags=["budgets"])


@router.get("/budgets")
def get_budget(
    user: CurrentUser,
    db: DbSession,
    month: Annotated[str, Query(description="Month in YYYY-MM format")],
) -> Envelope[BudgetResponse]:
    return ok(svc.get_budget(db, user.id, month))


@router.put("/budgets/{month}")
def set_budget(
    month: str,
    body: SetBudgetRequest,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[BudgetResponse]:
    return ok(svc.set_budget(db, user.id, month, body))


@router.post("/budgets/{month}/copy-from/{source_month}")
def copy_budget(
    month: str,
    source_month: str,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[BudgetResponse]:
    return ok(svc.copy_budget(db, user.id, month, source_month))


@router.get("/budgets/comparison")
def get_budget_comparison(
    user: CurrentUser,
    db: DbSession,
    category_id: uuid.UUID | None = None,
    months: int = 6,
) -> Envelope[BudgetComparisonResponse]:
    return ok(svc.get_budget_comparison(db, user.id, category_id, months))


@router.get("/budget-alerts")
def list_budget_alerts(
    user: CurrentUser,
    db: DbSession,
    month: str | None = None,
) -> Envelope[list[BudgetAlertResponse]]:
    return ok(svc.list_budget_alerts(db, user.id, month))

