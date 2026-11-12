"""Budget schemas for request validation and response serialization."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from app.core.money import MoneyOut, OptionalMoneyOut, PositiveAmount


class BudgetLineInput(BaseModel):
    category_id: uuid.UUID
    amount: PositiveAmount
    alert_thresholds: list[int] = Field(default_factory=lambda: [80, 100])


class SetBudgetRequest(BaseModel):
    overall_amount: PositiveAmount | None = None
    lines: list[BudgetLineInput] = Field(default_factory=list)


class BudgetLineResponse(BaseModel):
    id: uuid.UUID
    category_id: uuid.UUID
    category_name: str
    parent_id: uuid.UUID | None = None
    amount: MoneyOut
    alert_thresholds: list[int]
    actual: MoneyOut
    utilization: MoneyOut
    remaining: MoneyOut
    is_over_budget: bool


class BudgetResponse(BaseModel):
    id: uuid.UUID
    month: str  # YYYY-MM
    overall_amount: OptionalMoneyOut = None
    overall_actual: MoneyOut
    overall_utilization: OptionalMoneyOut = None
    overall_remaining: OptionalMoneyOut = None
    overall_is_over_budget: bool = False
    lines: list[BudgetLineResponse] = Field(default_factory=list)
    warning: str | None = None


class BudgetMonthComparisonItem(BaseModel):
    month: str  # YYYY-MM
    month_label: str
    budget: OptionalMoneyOut = None
    actual: MoneyOut
    utilization: OptionalMoneyOut = None
    remaining: OptionalMoneyOut = None
    is_over_budget: bool = False


class BudgetComparisonResponse(BaseModel):
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    months: list[BudgetMonthComparisonItem] = Field(default_factory=list)


class BudgetAlertResponse(BaseModel):
    id: uuid.UUID
    month: str  # YYYY-MM
    budget_line_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    category_name: str | None = None
    threshold: int
    triggered_at: datetime
