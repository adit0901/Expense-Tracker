"""Reports (income, expenses, savings trend) built only from services.calculations."""

from __future__ import annotations

import uuid
from collections import defaultdict
from decimal import Decimal

from sqlalchemy.orm import Session

from app.core.money import ZERO, round_money
from app.models.enums import PaymentMethod, SalaryComponentKind
from app.repositories import aggregates as agg
from app.schemas.reports import (
    CategoryAmount,
    Deduction,
    ExpenseCategoryRow,
    ExpenseReport,
    IncomeReport,
    MethodTotal,
    MonthFigures,
    MonthIncome,
    PeriodOut,
    SalaryMonth,
    SalarySummary,
    SavingsTrend,
    SourceTotal,
)
from app.services.calculations.figures import (
    category_totals,
    period_figures,
    share,
    total_expenses,
)
from app.services.calculations.periods import (
    Period,
    month_label,
    months_in,
    trailing_months,
)
from app.services.transactions.csv_export import write_csv

TREND_MONTHS = 12


def period_out(p: Period) -> PeriodOut:
    return PeriodOut(start=p.start, end=p.end, label=p.label, granularity=p.granularity)


def _key(y: int, m: int) -> str:
    return f"{y:04d}-{m:02d}"


# ---- expenses ------------------------------------------------------------------------------


def expense_report(db: Session, user_id: uuid.UUID, p: Period) -> ExpenseReport:
    by_type = agg.totals_by_type(db, user_id, p.start, p.end)
    total = total_expenses(by_type)
    cats = agg.categories_by_id(db, user_id)
    rows = agg.expense_net_by_category(db, user_id, p.start, p.end)
    top_totals: dict[uuid.UUID, Decimal] = defaultdict(lambda: ZERO)
    subs: dict[uuid.UUID, dict[uuid.UUID, Decimal]] = defaultdict(dict)
    for top_id, cat_id, net in rows:
        top_totals[top_id] += net
        if cat_id != top_id:
            subs[top_id][cat_id] = subs[top_id].get(cat_id, ZERO) + net
    by_category = []
    for ct in category_totals(top_totals):
        cid = ct.key
        assert isinstance(cid, uuid.UUID)
        c = cats.get(cid)
        by_category.append(
            ExpenseCategoryRow(
                category_id=cid,
                name=c.name if c else "Unknown",
                color=c.color if c else None,
                total=ct.total,
                share=ct.share,
                subcategories=[
                    CategoryAmount(
                        category_id=sid,
                        name=cats[sid].name if sid in cats else "Unknown",
                        color=cats[sid].color if sid in cats else None,
                        total=round_money(v),
                        share=share(v, total),
                    )
                    for sid, v in sorted(subs[cid].items(), key=lambda kv: -kv[1])
                ],
            )
        )
    methods = agg.expense_net_by_method(db, user_id, p.start, p.end)
    by_method = [
        MethodTotal(
            method=m.value,
            total=round_money(methods.get(m.value, ZERO)),
            share=share(methods.get(m.value, ZERO), total),
        )
        for m in PaymentMethod
    ]
    return ExpenseReport(
        period=period_out(p),
        total_expenses=round_money(total),
        by_category=by_category,
        by_payment_method=by_method,
    )


def expense_report_csv(r: ExpenseReport) -> str:
    rows: list[list[object]] = []
    for c in r.by_category:
        rows.append(["category", c.name, "", f"{c.total:.2f}", _pct(c.share)])
        rows.extend(
            ["category", c.name, s.name, f"{s.total:.2f}", _pct(s.share)] for s in c.subcategories
        )
    rows.extend(
        ["payment_method", m.method, "", f"{m.total:.2f}", _pct(m.share)]
        for m in r.by_payment_method
    )
    rows.append(["total", "", "", f"{r.total_expenses:.2f}", "100.00" if r.total_expenses else ""])
    return write_csv(["group", "name", "subcategory", "amount", "share_pct"], rows)


def _pct(v: Decimal | None) -> str:
    return "" if v is None else f"{v:.2f}"


# ---- savings trend (also used by the dashboard) -------------------------------------------


def trend_months(p: Period, count: int = TREND_MONTHS) -> tuple[list[tuple[int, int]], Period]:
    """Months to chart: the months within the period when it spans more than one month,
    otherwise the `count` months ending with the period's month. Returns months and the
    effective date range queried."""
    months = months_in(p)
    if len(months) > 1:
        return months, p
    months = trailing_months(p.end, count)
    from datetime import date

    first = date(months[0][0], months[0][1], 1)
    return months, Period(first, p.end, "custom", p.label)


def savings_trend(
    db: Session, user_id: uuid.UUID, p: Period, count: int = TREND_MONTHS
) -> SavingsTrend:
    months, rng = trend_months(p, count)
    data = agg.monthly_by_type(db, user_id, rng.start, rng.end)
    out = []
    for y, m in months:
        f = period_figures(data.get((y, m), {}))
        out.append(
            MonthFigures(
                month=_key(y, m),
                label=month_label(y, m),
                income=f.income,
                expenses=f.expenses,
                savings=f.savings,
                savings_rate=f.savings_rate,
            )
        )
    return SavingsTrend(period=period_out(p), months=out)


def savings_trend_csv(t: SavingsTrend) -> str:
    return write_csv(
        ["month", "income", "expenses", "savings", "savings_rate_pct"],
        [
            [
                m.month,
                f"{m.income:.2f}",
                f"{m.expenses:.2f}",
                f"{m.savings:.2f}",
                _pct(m.savings_rate),
            ]
            for m in t.months
        ],
    )


# ---- income --------------------------------------------------------------------------------


def income_report(db: Session, user_id: uuid.UUID, p: Period) -> IncomeReport:
    by_type = agg.totals_by_type(db, user_id, p.start, p.end)
    f = period_figures(by_type)
    monthly = agg.monthly_by_type(db, user_id, p.start, p.end)
    months = [
        MonthIncome(
            month=_key(y, m),
            label=month_label(y, m),
            income=period_figures(monthly.get((y, m), {})).income,
        )
        for y, m in months_in(p)
    ]
    by_source = sorted(
        (
            SourceTotal(
                source_id=sid,
                name=name or "No source",
                type=stype,
                total=round_money(total),
                share=share(total, f.income),
            )
            for sid, name, stype, total in agg.income_by_source(db, user_id, p.start, p.end)
        ),
        key=lambda s: -s.total,
    )
    cats = agg.categories_by_id(db, user_id)
    by_category = []
    for ct in category_totals(agg.income_by_category(db, user_id, p.start, p.end)):
        cat = cats.get(ct.key) if isinstance(ct.key, uuid.UUID) else None
        by_category.append(
            CategoryAmount(
                category_id=cat.id if cat else None,
                name=cat.name if cat else "Unknown",
                color=cat.color if cat else None,
                total=ct.total,
                share=ct.share,
            )
        )
    return IncomeReport(
        period=period_out(p),
        total_income=f.income,
        months=months,
        by_source=by_source,
        by_category=by_category,
        salary=_salary_summary(db, user_id, p),
    )


def _salary_summary(db: Session, user_id: uuid.UUID, p: Period) -> SalarySummary:
    comps = agg.salary_components(db, user_id, p.start, p.end)
    gross_by_month: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    ded_by_month: dict[tuple[int, int], Decimal] = defaultdict(lambda: ZERO)
    ded_by_name: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for y, m, kind, name, amount in comps:
        if kind == SalaryComponentKind.gross:
            gross_by_month[(y, m)] += amount
        else:
            ded_by_month[(y, m)] += amount
            ded_by_name[name] += amount
    gross = sum(gross_by_month.values(), ZERO)
    deductions = sum(ded_by_month.values(), ZERO)
    months = [
        SalaryMonth(
            month=_key(y, m),
            label=month_label(y, m),
            gross=round_money(gross_by_month[(y, m)]),
            total_deductions=round_money(ded_by_month[(y, m)]),
            net=round_money(gross_by_month[(y, m)] - ded_by_month[(y, m)]),
        )
        for y, m in months_in(p)
    ]
    return SalarySummary(
        gross=round_money(gross),
        deductions=[
            Deduction(name=n, amount=round_money(v))
            for n, v in sorted(ded_by_name.items(), key=lambda kv: -kv[1])
        ],
        total_deductions=round_money(deductions),
        net=round_money(gross - deductions),
        months=months,
    )


def income_report_csv(r: IncomeReport) -> str:
    salary = {s.month: s for s in r.salary.months}
    rows: list[list[object]] = [
        [
            m.month,
            f"{m.income:.2f}",
            f"{salary[m.month].gross:.2f}",
            f"{salary[m.month].total_deductions:.2f}",
            f"{salary[m.month].net:.2f}",
        ]
        for m in r.months
    ]
    rows.append(
        [
            "total",
            f"{r.total_income:.2f}",
            f"{r.salary.gross:.2f}",
            f"{r.salary.total_deductions:.2f}",
            f"{r.salary.net:.2f}",
        ]
    )
    rows.append([])
    rows.append(["source", "total", "share_pct", "", ""])
    rows.extend([s.name, f"{s.total:.2f}", _pct(s.share), "", ""] for s in r.by_source)
    return write_csv(
        ["month", "net_income", "salary_gross", "salary_deductions", "salary_net"], rows
    )
