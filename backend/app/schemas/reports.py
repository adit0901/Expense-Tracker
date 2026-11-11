from __future__ import annotations

import uuid
from datetime import date

from pydantic import BaseModel

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
