"""Reports & analytics endpoints (P0: income, expenses, savings trend) with CSV exports."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Query, Response

from app.api.deps import CurrentUser, DbSession
from app.api.v1.periods import PeriodDep
from app.core.responses import Envelope, ok
from app.schemas.reports import ExpenseReport, IncomeReport, SavingsTrend
from app.services import reports as svc

router = APIRouter(prefix="/reports", tags=["reports"])
Months = Annotated[int, Query(ge=1, le=36)]


def _csv(body: str, name: str) -> Response:
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{name}"'},
    )


@router.get("/income")
def income(user: CurrentUser, db: DbSession, period: PeriodDep) -> Envelope[IncomeReport]:
    return ok(svc.income_report(db, user.id, period))


@router.get("/income/export.csv", response_class=Response)
def income_csv(user: CurrentUser, db: DbSession, period: PeriodDep) -> Response:
    return _csv(svc.income_report_csv(svc.income_report(db, user.id, period)), "income.csv")


@router.get("/expenses")
def expenses(user: CurrentUser, db: DbSession, period: PeriodDep) -> Envelope[ExpenseReport]:
    return ok(svc.expense_report(db, user.id, period))


@router.get("/expenses/export.csv", response_class=Response)
def expenses_csv(user: CurrentUser, db: DbSession, period: PeriodDep) -> Response:
    return _csv(svc.expense_report_csv(svc.expense_report(db, user.id, period)), "expenses.csv")


@router.get("/savings-trend")
def savings_trend(
    user: CurrentUser, db: DbSession, period: PeriodDep, months: Months = 12
) -> Envelope[SavingsTrend]:
    return ok(svc.savings_trend(db, user.id, period, months))


@router.get("/savings-trend/export.csv", response_class=Response)
def savings_trend_csv(
    user: CurrentUser, db: DbSession, period: PeriodDep, months: Months = 12
) -> Response:
    return _csv(
        svc.savings_trend_csv(svc.savings_trend(db, user.id, period, months)), "savings-trend.csv"
    )
