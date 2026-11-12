from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from pydantic import BaseModel, Field

from app.core.money import MoneyOut, OptionalMoneyOut


class PeriodOut(BaseModel):
    start: date
    end: date
    label: str
    granularity: str


class MonthFigures(BaseModel):
    month: str  # YYYY-MM
    label: str
    income: MoneyOut
    expenses: MoneyOut
    savings: MoneyOut
    savings_rate: OptionalMoneyOut


class MonthIncome(BaseModel):
    month: str
    label: str
    income: MoneyOut


class SourceTotal(BaseModel):
    source_id: uuid.UUID | None
    name: str
    type: str | None
    total: MoneyOut
    share: OptionalMoneyOut


class CategoryAmount(BaseModel):
    category_id: uuid.UUID | None
    name: str
    color: str | None = None
    total: MoneyOut
    share: OptionalMoneyOut


class ExpenseCategoryRow(CategoryAmount):
    subcategories: list[CategoryAmount] = []


class Deduction(BaseModel):
    name: str
    amount: MoneyOut


class SalaryMonth(BaseModel):
    month: str
    label: str
    gross: MoneyOut
    total_deductions: MoneyOut
    net: MoneyOut


class SalarySummary(BaseModel):
    gross: MoneyOut
    deductions: list[Deduction]
    total_deductions: MoneyOut
    net: MoneyOut
    months: list[SalaryMonth]


class IncomeReport(BaseModel):
    period: PeriodOut
    total_income: MoneyOut
    months: list[MonthIncome]
    by_source: list[SourceTotal]
    by_category: list[CategoryAmount]
    salary: SalarySummary


class MethodTotal(BaseModel):
    method: str
    total: MoneyOut
    share: OptionalMoneyOut


class ExpenseReport(BaseModel):
    period: PeriodOut
    total_expenses: MoneyOut
    by_category: list[ExpenseCategoryRow]
    by_payment_method: list[MethodTotal]


class SavingsTrend(BaseModel):
    period: PeriodOut
    months: list[MonthFigures]


class Tile(BaseModel):
    value: OptionalMoneyOut
    previous: OptionalMoneyOut
    change: OptionalMoneyOut
    change_kind: str  # "percent" | "points"


class PlanningTile(BaseModel):
    value: MoneyOut
    previous: OptionalMoneyOut = None
    change: OptionalMoneyOut = None
    change_kind: str = "percent"


class SavingsTargetDashboardTile(BaseModel):
    configured: bool
    target_amount: OptionalMoneyOut = None
    actual_savings: OptionalMoneyOut = None
    achievement_pct: OptionalMoneyOut = None
    shortfall: OptionalMoneyOut = None


class NetWorthPoint(BaseModel):
    as_of: date
    net_worth: MoneyOut
    total_assets: MoneyOut
    total_liabilities: MoneyOut


class LoanTrendPoint(BaseModel):
    month: str
    total_outstanding: MoneyOut


class BudgetAlertDashboardItem(BaseModel):
    category_id: uuid.UUID | None
    category_name: str
    budgeted: MoneyOut
    spent: MoneyOut
    utilization_pct: MoneyOut
    threshold_crossed: int


class Overview(BaseModel):
    period: PeriodOut
    previous_period: PeriodOut
    income: Tile
    expenses: Tile
    savings: Tile
    savings_rate: Tile
    liquid_funds: Tile
    has_transactions: bool
    has_accounts: bool

    # P1 additions:
    net_worth: PlanningTile | None = None
    total_assets: PlanningTile | None = None
    total_liabilities: PlanningTile | None = None
    outstanding_loans: PlanningTile | None = None
    monthly_emi_commitment: PlanningTile | None = None
    savings_target: SavingsTargetDashboardTile | None = None

    # Budget status
    budget_utilization_pct: OptionalMoneyOut = None
    budget_alerts: list[BudgetAlertDashboardItem] = Field(default_factory=list)

    # Trend series
    net_worth_trend: list[NetWorthPoint] = Field(default_factory=list)
    asset_allocation: list[dict[str, Any]] = Field(default_factory=list)
    loan_trend: list[LoanTrendPoint] = Field(default_factory=list)


class BreakdownRow(BaseModel):
    category_id: uuid.UUID | None
    name: str
    color: str | None
    total: MoneyOut
    share: OptionalMoneyOut
    is_other: bool


class CategoryBreakdown(BaseModel):
    period: PeriodOut
    total_expenses: MoneyOut
    categories: list[BreakdownRow]
