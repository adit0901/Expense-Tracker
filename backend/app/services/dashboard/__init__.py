"""Overview dashboard: KPI tiles, trends and category breakdown.

Every figure comes from services.calculations via services.reports, so the dashboard and the
reports return identical values for the same period.
"""

from __future__ import annotations

import uuid
from decimal import Decimal

from sqlalchemy import exists, func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.money import ZERO, round_money
from app.core.timeutil import today_in
from app.models.account import Account
from app.models.enums import LoanStatus
from app.models.loan import Loan, LoanPayment
from app.models.net_worth import NetWorthSnapshot
from app.models.transaction import Transaction
from app.repositories import aggregates as agg
from app.schemas.reports import (
    BreakdownRow,
    BudgetAlertDashboardItem,
    CategoryBreakdown,
    LoanTrendPoint,
    NetWorthPoint,
    Overview,
    PlanningTile,
    SavingsTargetDashboardTile,
    SavingsTrend,
    Tile,
)
from app.services import accounts as accounts_service
from app.services import budgets as budgets_service
from app.services import goals as goals_service
from app.services import loans as loans_service
from app.services import net_worth as net_worth_service
from app.services import reports
from app.services.calculations.figures import (
    category_totals,
    percent_change,
    period_figures,
    top_n_with_other,
    total_expenses,
)
from app.services.calculations.periods import Period, month_end, previous_period

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

    # 1. Net worth & balance sheet
    nw = net_worth_service.get_net_worth(db, user_id, as_of=as_of)
    nw_tile = PlanningTile(
        value=nw.net_worth,
        previous=round_money(nw.net_worth - nw.mom_growth.amount_change)
        if nw.mom_growth and nw.mom_growth.amount_change is not None
        else None,
        change=nw.mom_growth.percentage_change if nw.mom_growth else None,
        change_kind="percent",
    )
    assets_tile = PlanningTile(value=nw.total_assets)
    liab_tile = PlanningTile(value=nw.total_liabilities)

    # 2. Loans & EMI
    loans_sum = loans_service.get_loans_summary(db, user_id)
    loans_tile = PlanningTile(value=loans_sum.total_outstanding)
    emi_tile = PlanningTile(value=loans_sum.total_monthly_emi_commitment)

    # 3. Savings target
    target_month = f"{as_of.year:04d}-{as_of.month:02d}"
    try:
        st = goals_service.get_savings_target(db, user_id, target_month)
        savings_target_tile = SavingsTargetDashboardTile(
            configured=True,
            target_amount=st.target_amount,
            actual_savings=st.actual_savings,
            achievement_pct=st.achievement_pct,
            shortfall=st.shortfall,
        )
    except NotFoundError:
        savings_target_tile = SavingsTargetDashboardTile(configured=False)

    # 4. Budget status
    try:
        b = budgets_service.get_budget(db, user_id, target_month)
        budget_util_pct = b.overall_utilization
        line_by_cat = {line.category_id: line for line in b.lines}
        alerts_list = budgets_service.list_budget_alerts(db, user_id, target_month)
        budget_alert_items = []
        for a in alerts_list:
            line = line_by_cat.get(a.category_id) if a.category_id else None
            cat_name = a.category_name or (line.category_name if line else "Overall")
            b_amt = line.amount if line else (b.overall_amount or ZERO)
            b_spent = line.actual if line else b.overall_actual
            b_util = line.utilization if line else (b.overall_utilization or ZERO)
            budget_alert_items.append(
                BudgetAlertDashboardItem(
                    category_id=a.category_id,
                    category_name=cat_name,
                    budgeted=b_amt,
                    spent=b_spent,
                    utilization_pct=b_util,
                    threshold_crossed=a.threshold,
                )
            )
    except NotFoundError:
        budget_util_pct = None
        budget_alert_items = []

    # 5. Trend series
    # Net worth snapshots (last 12)
    snaps = (
        db.scalars(
            select(NetWorthSnapshot)
            .where(NetWorthSnapshot.user_id == user_id)
            .order_by(NetWorthSnapshot.as_of.desc())
            .limit(12)
        )
        .all()
    )
    nw_trend = [
        NetWorthPoint(
            as_of=s.as_of,
            net_worth=s.net_worth,
            total_assets=s.total_assets,
            total_liabilities=s.total_liabilities,
        )
        for s in reversed(snaps)
    ]

    # Asset allocation
    asset_alloc = [
        {"category": item.category, "amount": item.amount, "share_pct": item.share_pct}
        for item in nw.asset_breakdown
    ]

    # Loan trend (last 12 months)
    all_loans = db.scalars(select(Loan).where(Loan.user_id == user_id)).all()
    month_dates = []
    cy, cm = as_of.year, as_of.month
    for _ in range(12):
        month_dates.append(month_end(cy, cm))
        if cm == 1:
            cy -= 1
            cm = 12
        else:
            cm -= 1
    month_dates.reverse()

    loan_trend_points: list[LoanTrendPoint] = []
    for m_end in month_dates:
        tot_out = ZERO
        if all_loans:
            paid_stmt = (
                select(
                    LoanPayment.loan_id,
                    func.coalesce(func.sum(LoanPayment.principal), ZERO),
                )
                .join(Transaction, Transaction.id == LoanPayment.transaction_id)
                .where(
                    LoanPayment.loan_id.in_([le.id for le in all_loans]),
                    Transaction.txn_date <= m_end,
                )
                .group_by(LoanPayment.loan_id)
            )
            paid_map: dict[uuid.UUID, Decimal] = dict(db.execute(paid_stmt).all())
            for loan in all_loans:
                if loan.start_date <= m_end:
                    if loan.status == LoanStatus.closed and loan.updated_at.date() <= m_end:
                        continue
                    starting_p = (
                        loan.baseline_outstanding
                        if loan.baseline_outstanding is not None
                        else loan.original_principal
                    )
                    paid = paid_map.get(loan.id, ZERO)
                    tot_out += max(ZERO, starting_p - paid)
        loan_trend_points.append(
            LoanTrendPoint(
                month=f"{m_end.year:04d}-{m_end.month:02d}",
                total_outstanding=round_money(tot_out),
            )
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
        net_worth=nw_tile,
        total_assets=assets_tile,
        total_liabilities=liab_tile,
        outstanding_loans=loans_tile,
        monthly_emi_commitment=emi_tile,
        savings_target=savings_target_tile,
        budget_utilization_pct=budget_util_pct,
        budget_alerts=budget_alert_items,
        net_worth_trend=nw_trend,
        asset_allocation=asset_alloc,
        loan_trend=loan_trend_points,
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
