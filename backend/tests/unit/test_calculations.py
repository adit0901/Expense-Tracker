"""Table-driven tests for services.calculations.

Test names carry ids (FC01...) referenced by docs/financial-calculations.md.
"""

from datetime import date
from decimal import Decimal

import pytest

from app.models.enums import TransactionType as T
from app.services.calculations.figures import (
    CategoryTotal,
    category_totals,
    percent_change,
    period_figures,
    savings,
    savings_rate,
    share,
    top_n_with_other,
    total_expenses,
    total_income,
)
from app.services.calculations.periods import (
    PeriodKind,
    add_months,
    custom_period,
    fy_period,
    fy_start_year,
    month_period,
    months_in,
    previous_period,
    quarter_period,
    resolve_period,
    trailing_months,
    year_period,
)

D = Decimal


def test_fc01_decimal_sum_no_float_drift() -> None:
    total = total_expenses({T.expense: D("0.10") + D("0.20") + D("0.30")})
    assert total == D("0.60")


def test_fc02_income_counts_only_income_transactions() -> None:
    by_type = {T.income: D("80000.00"), T.transfer: D("20000.00"), T.expense: D("100.00")}
    assert total_income(by_type) == D("80000.00")


def test_fc03_expenses_are_net_of_refunds() -> None:
    assert total_expenses({T.expense: D("3000.00"), T.refund: D("1000.00")}) == D("2000.00")


def test_fc04_card_purchase_and_bill_payment_counted_once() -> None:
    # A 15000 card purchase (expense) and the 15000 bill payment (transfer) in one month.
    assert total_expenses({T.expense: D("15000.00"), T.transfer: D("15000.00")}) == D("15000.00")


def test_fc05_overspending_gives_negative_savings() -> None:
    f = period_figures({T.income: D("80000.00"), T.expense: D("95000.00")})
    assert f.savings == D("-15000.00")
    assert f.savings_rate == D("-18.75")


def test_fc06_savings_rate() -> None:
    f = period_figures({T.income: D("120000.00"), T.expense: D("90000.00")})
    assert (f.income, f.expenses, f.savings, f.savings_rate) == (
        D("120000.00"),
        D("90000.00"),
        D("30000.00"),
        D("25.00"),
    )


def test_fc07_zero_income_rate_is_null() -> None:
    f = period_figures({T.expense: D("5000.00")})
    assert f.savings == D("-5000.00")
    assert f.savings_rate is None
    assert period_figures({}).savings_rate is None


@pytest.mark.parametrize(
    ("income", "sav", "expected"),
    [
        (D("3"), D("1"), D("33.33")),
        (D("3"), D("2"), D("66.67")),
        (D("200"), D("0.01"), D("0.01")),
        (D("8"), D("-1"), D("-12.50")),
    ],
)
def test_fc08_rate_rounds_half_up_to_2dp(income: Decimal, sav: Decimal, expected: Decimal) -> None:
    assert savings_rate(income, sav) == expected


def test_fc09_category_share() -> None:
    assert share(D("15000.00"), D("60000.00")) == D("25.00")
    assert share(D("1"), D("0")) is None
    rows = category_totals({"food": D("15000"), "rent": D("45000")})
    assert [(r.key, r.total, r.share) for r in rows] == [
        ("rent", D("45000.00"), D("75.00")),
        ("food", D("15000.00"), D("25.00")),
    ]
    assert category_totals({"x": D("0")})[0].share is None


def test_fc10_financial_year() -> None:
    p = resolve_period(PeriodKind.this_fy, date(2026, 11, 11))
    assert (p.start, p.end, p.label) == (date(2026, 4, 1), date(2027, 3, 31), "FY 2026-27")
    assert fy_start_year(date(2027, 3, 31)) == 2026 and fy_start_year(date(2027, 4, 1)) == 2027


def test_fc11_back_dated_entry_belongs_to_txn_month() -> None:
    october = month_period(2026, 10)
    assert october.start <= date(2026, 10, 31) <= october.end
    assert not (october.start <= date(2026, 11, 2) <= october.end)


def test_fc12_percent_change() -> None:
    assert percent_change(D("110"), D("100")) == D("10.00")
    assert percent_change(D("50"), D("100")) == D("-50.00")
    assert percent_change(D("100"), D("0")) is None
    assert percent_change(D("-50"), D("-100")) == D("50.00")


def test_fc13_top_six_plus_other() -> None:
    rows = category_totals({f"c{i}": D(i) for i in range(1, 9)})
    total = sum((r.total for r in rows), D(0))
    out = top_n_with_other(rows, 6, total)
    assert len(out) == 7 and out[-1].key == "other"
    assert out[-1].total == D("3.00")  # c1 + c2
    assert sum((r.total for r in out), D(0)) == total
    assert top_n_with_other(rows[:3], 6, total) == rows[:3]


def test_savings_helper() -> None:
    assert savings(D("1"), D("2")) == D("-1")
    assert isinstance(CategoryTotal("k", D(1), None).key, str)


@pytest.mark.parametrize(
    ("kind", "today", "start", "end", "label"),
    [
        (
            PeriodKind.this_month,
            date(2026, 11, 11),
            date(2026, 11, 1),
            date(2026, 11, 30),
            "Nov 2026",
        ),
        (
            PeriodKind.last_month,
            date(2026, 1, 15),
            date(2025, 12, 1),
            date(2025, 12, 31),
            "Dec 2025",
        ),
        (
            PeriodKind.this_quarter,
            date(2026, 11, 11),
            date(2026, 10, 1),
            date(2026, 12, 31),
            "Q4 2026",
        ),
        (
            PeriodKind.this_quarter,
            date(2026, 2, 28),
            date(2026, 1, 1),
            date(2026, 3, 31),
            "Q1 2026",
        ),
        (PeriodKind.this_year, date(2026, 11, 11), date(2026, 1, 1), date(2026, 12, 31), "2026"),
        (PeriodKind.this_fy, date(2026, 2, 1), date(2025, 4, 1), date(2026, 3, 31), "FY 2025-26"),
    ],
)
def test_resolve_period(kind: PeriodKind, today: date, start: date, end: date, label: str) -> None:
    p = resolve_period(kind, today)
    assert (p.start, p.end, p.label) == (start, end, label)


def test_custom_period_inclusive_and_validation() -> None:
    p = resolve_period(PeriodKind.custom, date(2026, 1, 1), date(2026, 7, 15), date(2026, 9, 15))
    assert (p.start, p.end, p.days) == (date(2026, 7, 15), date(2026, 9, 15), 63)
    with pytest.raises(ValueError):
        resolve_period(PeriodKind.custom, date(2026, 1, 1))
    with pytest.raises(ValueError):
        custom_period(date(2026, 2, 1), date(2026, 1, 1))


@pytest.mark.parametrize(
    ("current", "expected_start", "expected_end"),
    [
        (month_period(2026, 1), date(2025, 12, 1), date(2025, 12, 31)),
        (month_period(2026, 3), date(2026, 2, 1), date(2026, 2, 28)),
        (quarter_period(2026, 1), date(2025, 10, 1), date(2025, 12, 31)),
        (year_period(2026), date(2025, 1, 1), date(2025, 12, 31)),
        (fy_period(2026), date(2025, 4, 1), date(2026, 3, 31)),
        (custom_period(date(2026, 7, 15), date(2026, 9, 15)), date(2026, 5, 13), date(2026, 7, 14)),
    ],
)
def test_previous_period(current: object, expected_start: date, expected_end: date) -> None:
    prev = previous_period(current)  # type: ignore[arg-type]
    assert (prev.start, prev.end) == (expected_start, expected_end)


def test_month_helpers() -> None:
    assert add_months(2026, 1, -1) == (2025, 12)
    assert add_months(2026, 12, 1) == (2027, 1)
    assert month_period(2024, 2).end == date(2024, 2, 29)
    assert months_in(custom_period(date(2026, 7, 15), date(2026, 9, 15))) == [
        (2026, 7),
        (2026, 8),
        (2026, 9),
    ]
    trail = trailing_months(date(2026, 11, 30), 12)
    assert trail[0] == (2025, 12) and trail[-1] == (2026, 11) and len(trail) == 12
