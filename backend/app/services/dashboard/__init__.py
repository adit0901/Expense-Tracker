"""Overview dashboard: KPI tiles, trends and category breakdown.

Every figure comes from services.calculations via services.reports, so the dashboard and the
reports return identical values for the same period.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import exists, select
from sqlalchemy.orm import Session

from app.core.money import ZERO, round_money
from app.core.timeutil import today_in
from app.models.account import Account
from app.models.transaction import Transaction
from app.repositories import aggregates as agg
from app.schemas.reports import BreakdownRow, CategoryBreakdown, Overview, SavingsTrend, Tile
from app.services import accounts as accounts_service
from app.services import reports
from app.services.calculations.figures import (
    category_totals,
    percent_change,
    period_figures,
    top_n_with_other,
    total_expenses,
)
from app.services.calculations.periods import Period, previous_period

TOP_CATEGORIES = 6
OTHER_LABEL = "Other categories"


def _money_tile(cur: Decimal, prev: Decimal) -> Tile:
    return Tile(value=cur, previous=prev, change=percent_change(cur, prev), change_kind="percent")


def overview(db: Session, user_id: uuid.UUID, p: Period, tz: str) -> Overview:
    prev = previous_period(p)
    cur_f = period_figures(agg.totals_by_type(db, user_id, p.start, p.end))
    prev_f = period_figures(agg.totals_by_type(db, user_id, prev.start, prev.end))
    as_of = min(p.end, today_in(tz))
    liquid_now = accounts_service.summary(db, user_id, as_of=as_of).liquid_funds
    liquid_prev = accounts_service.summary(db, user_id, as_of=prev.end).liquid_funds
    rate_change = (
        None
        if cur_f.savings_rate is None or prev_f.savings_rate is None
        else cur_f.savings_rate - prev_f.savings_rate
    )
    return Overview(
        period=reports.period_out(p),
        previous_period=reports.period_out(prev),
        income=_money_tile(cur_f.income, prev_f.income),
        expenses=_money_tile(cur_f.expenses, prev_f.expenses),
        savings=_money_tile(cur_f.savings, prev_f.savings),
        savings_rate=Tile(
            value=cur_f.savings_rate,
            previous=prev_f.savings_rate,
            change=rate_change,
            change_kind="points",
        ),
        liquid_funds=_money_tile(round_money(liquid_now), round_money(liquid_prev)),
        has_transactions=bool(db.scalar(select(exists().where(Transaction.user_id == user_id)))),
        has_accounts=bool(db.scalar(select(exists().where(Account.user_id == user_id)))),
    )


def trends(db: Session, user_id: uuid.UUID, p: Period, months: int) -> SavingsTrend:
    return reports.savings_trend(db, user_id, p, months)


def category_breakdown(db: Session, user_id: uuid.UUID, p: Period) -> CategoryBreakdown:
    total = total_expenses(agg.totals_by_type(db, user_id, p.start, p.end))
    tops: dict[uuid.UUID, Decimal] = {}
    for top_id, _cat, net in agg.expense_net_by_category(db, user_id, p.start, p.end):
        tops[top_id] = tops.get(top_id, ZERO) + net
    cats = agg.categories_by_id(db, user_id)
    rows = top_n_with_other(category_totals(tops), TOP_CATEGORIES, total)
    out = []
    for r in rows:
        if isinstance(r.key, uuid.UUID):
            c = cats.get(r.key)
            out.append(
                BreakdownRow(
                    category_id=r.key,
                    name=c.name if c else "Unknown",
                    color=c.color if c else None,
                    total=r.total,
                    share=r.share,
                    is_other=False,
                )
            )
        else:
            out.append(
                BreakdownRow(
                    category_id=None,
                    name=OTHER_LABEL,
                    color=None,
                    total=r.total,
                    share=r.share,
                    is_other=True,
                )
            )
    return CategoryBreakdown(
        period=reports.period_out(p), total_expenses=round_money(total), categories=out
    )
