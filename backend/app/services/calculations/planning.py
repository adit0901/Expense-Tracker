"""Budgets, savings goals and emergency fund formulas (spec: planning)."""

from __future__ import annotations

import math
from datetime import date
from decimal import Decimal

from app.core.money import ZERO, round_money, round_pct
from app.services.calculations.periods import add_months, month_end

HUNDRED = Decimal(100)


def budget_utilization(actual_expenses: Decimal, budget_amount: Decimal) -> Decimal:
    """Budget Utilization = (Actual Expenses / Budget) * 100, rounded to 2 decimals.

    A budget of zero or negative is not allowed.
    """
    if budget_amount <= ZERO:
        raise ValueError("Budget amount must be positive")
    return round_pct((actual_expenses / budget_amount) * HUNDRED)


def budget_remaining(budget_amount: Decimal, actual_expenses: Decimal) -> Decimal:
    """Remaining amount = budget - actual (negative when overspent)."""
    return round_money(budget_amount - actual_expenses)


def savings_target_achievement(
    actual_savings: Decimal, target_amount: Decimal
) -> tuple[Decimal, Decimal]:
    """Savings Target Achievement = actual / target * 100.

    When actual savings is negative, achievement is 0.00 and shortfall = target - actual.
    Returns (achievement_pct, shortfall).
    """
    if target_amount <= ZERO:
        raise ValueError("Target amount must be positive")

    if actual_savings < ZERO:
        shortfall = round_money(target_amount - actual_savings)
        return round_pct(ZERO), shortfall

    achievement = round_pct((actual_savings / target_amount) * HUNDRED)
    shortfall = round_money(max(ZERO, target_amount - actual_savings))
    return achievement, shortfall


def goal_remaining(target_amount: Decimal, current_amount: Decimal) -> Decimal:
    """Remaining amount to reach goal target."""
    return round_money(max(ZERO, target_amount - current_amount))


def goal_progress_pct(target_amount: Decimal, current_amount: Decimal) -> Decimal:
    """Progress percentage capped at 100.00%."""
    if target_amount <= ZERO:
        return HUNDRED
    pct = round_pct((current_amount / target_amount) * HUNDRED)
    return min(HUNDRED, max(ZERO, pct))


def goal_required_monthly_contribution(
    remaining: Decimal,
    target_date: date | None,
    as_of: date,
) -> Decimal | None:
    """Required monthly contribution to meet the target date.

    Returns None if target_date has passed (overdue) or remaining is 0 or no target date.
    """
    if target_date is None or remaining <= ZERO:
        return None
    if as_of > target_date:
        return None

    # Full months remaining
    months = (target_date.year - as_of.year) * 12 + (target_date.month - as_of.month)
    if months <= 0:
        return round_money(remaining)
    return round_money(remaining / Decimal(months))


def goal_estimated_completion_date(
    remaining: Decimal,
    average_3m_monthly_contribution: Decimal,
    as_of: date,
) -> date | None:
    """Estimated completion date based on 3-month average net monthly contribution.

    Returns None ('Cannot estimate') if 3-month average is zero or negative.
    """
    if remaining <= ZERO:
        return as_of
    if average_3m_monthly_contribution <= ZERO:
        return None

    months_needed = math.ceil(remaining / average_3m_monthly_contribution)
    y, m = add_months(as_of.year, as_of.month, months_needed)
    day = min(as_of.day, month_end(y, m).day)
    return date(y, m, day)


def emergency_fund_coverage(
    liquid_savings: Decimal,
    essential_monthly_expenses: Decimal,
) -> Decimal | None:
    """Emergency Fund Coverage (months) = Liquid Savings / Essential Monthly Expenses.

    Returns None ('N/A') when essential monthly expenses is zero or negative.
    """
    if essential_monthly_expenses <= ZERO:
        return None
    return round_pct(liquid_savings / essential_monthly_expenses)
