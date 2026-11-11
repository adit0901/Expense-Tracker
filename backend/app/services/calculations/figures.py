"""Authoritative financial formulas (spec: financial-calculations).

All functions are pure and take Decimals; final figures are rounded half-up to 2 dp only
at the end. See docs/financial-calculations.md for definitions and worked examples.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from decimal import Decimal

from app.core.money import ZERO, round_money, round_pct
from app.models.enums import TransactionType

HUNDRED = Decimal(100)


@dataclass(frozen=True)
class PeriodFigures:
    income: Decimal
    expenses: Decimal
    savings: Decimal
    savings_rate: Decimal | None


def total_income(by_type: Mapping[TransactionType, Decimal]) -> Decimal:
    """Monthly Income = sum of `income` transactions (net salary as credited)."""
    return by_type.get(TransactionType.income, ZERO)


def total_expenses(by_type: Mapping[TransactionType, Decimal]) -> Decimal:
    """Monthly Expenses = sum of `expense` minus sum of `refund`.

    Transfers (incl. credit-card bill payments), salary deductions, and later loan principal
    and investment purchases are not expenses and are therefore not read here.
    """
    return by_type.get(TransactionType.expense, ZERO) - by_type.get(TransactionType.refund, ZERO)


def savings(income: Decimal, expenses: Decimal) -> Decimal:
    """Savings = Income - Expenses (may be negative)."""
    return income - expenses


def savings_rate(income: Decimal, savings_amount: Decimal) -> Decimal | None:
    """Savings Rate = Savings / Income x 100; None (N/A) when income is zero."""
    if income == ZERO:
        return None
    return round_pct(savings_amount / income * HUNDRED)


def period_figures(by_type: Mapping[TransactionType, Decimal]) -> PeriodFigures:
    inc = total_income(by_type)
    exp = total_expenses(by_type)
    sav = savings(inc, exp)
    return PeriodFigures(
        income=round_money(inc),
        expenses=round_money(exp),
        savings=round_money(sav),
        savings_rate=savings_rate(inc, sav),
    )


def share(part: Decimal, total: Decimal) -> Decimal | None:
    """part / total x 100, None when the total is zero."""
    if total == ZERO:
        return None
    return round_pct(part / total * HUNDRED)


def percent_change(current: Decimal, previous: Decimal) -> Decimal | None:
    """Change vs the previous period in %; None ("—") when the previous value is zero."""
    if previous == ZERO:
        return None
    return round_pct((current - previous) / abs(previous) * HUNDRED)


@dataclass(frozen=True)
class CategoryTotal:
    key: object
    total: Decimal
    share: Decimal | None


def category_totals[K](net_by_category: Mapping[K, Decimal]) -> list[CategoryTotal]:
    """Category shares of total expenses, largest first (subcategories rolled up by caller)."""
    grand = sum(net_by_category.values(), ZERO)
    rows = [CategoryTotal(k, round_money(v), share(v, grand)) for k, v in net_by_category.items()]
    return sorted(rows, key=lambda r: (-r.total, str(r.key)))


def top_n_with_other(
    rows: list[CategoryTotal], n: int, total: Decimal, other_key: object = "other"
) -> list[CategoryTotal]:
    """Keep the n largest categories and group the rest into one 'other' row."""
    if len(rows) <= n:
        return rows
    head, tail = rows[:n], rows[n:]
    other = sum((r.total for r in tail), ZERO)
    return [*head, CategoryTotal(other_key, round_money(other), share(other, total))]


def sum_amounts(values: Iterable[Decimal]) -> Decimal:
    return sum(values, ZERO)
