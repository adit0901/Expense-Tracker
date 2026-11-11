"""Shared period query parameters (dashboard and reports)."""

from __future__ import annotations

from datetime import date
from typing import Annotated

from fastapi import Depends, Query

from app.api.deps import CurrentUser, DbSession
from app.core.errors import ValidationAppError
from app.core.timeutil import today_in
from app.services.calculations.periods import Period, PeriodKind, resolve_period
from app.services.users import get_preferences


def user_timezone(user: CurrentUser, db: DbSession) -> str:
    return get_preferences(db, user).timezone


def period_params(
    tz: Annotated[str, Depends(user_timezone)],
    period: PeriodKind = PeriodKind.this_month,
    start: date | None = None,
    end: date | None = None,
    as_of: Annotated[date | None, Query(description="Reference date (defaults to today)")] = None,
) -> Period:
    try:
        return resolve_period(period, as_of or today_in(tz), start, end)
    except ValueError as exc:
        raise ValidationAppError(
            str(exc), details=[{"field": "start", "message": "invalid"}]
        ) from exc


PeriodDep = Annotated[Period, Depends(period_params)]
TimezoneDep = Annotated[str, Depends(user_timezone)]
