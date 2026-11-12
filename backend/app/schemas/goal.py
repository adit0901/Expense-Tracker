from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.models.enums import GoalContributionKind, GoalStatus, GoalType


class SavingsTargetIn(BaseModel):
    amount: Decimal = Field(..., gt=0)


class SavingsTargetOut(BaseModel):
    id: uuid.UUID | None = None
    month: str
    effective_from: date
    target_amount: Decimal
    actual_savings: Decimal
    achievement_pct: Decimal
    shortfall: Decimal
    is_achieved: bool


class GoalCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    type: GoalType
    target_amount: Decimal = Field(..., gt=0)
    target_date: date | None = None
    starting_amount: Decimal = Field(default=Decimal("0.00"), ge=0)
    notes: str | None = Field(default=None, max_length=500)


class GoalUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: GoalType | None = None
    target_amount: Decimal | None = Field(default=None, gt=0)
    target_date: date | None = None
    status: GoalStatus | None = None
    notes: str | None = Field(default=None, max_length=500)


class GoalOut(BaseModel):
    id: uuid.UUID
    name: str
    type: GoalType
    target_amount: Decimal
    target_date: date | None
    starting_amount: Decimal
    status: GoalStatus
    notes: str | None
    current_amount: Decimal
    progress_pct: Decimal
    remaining_amount: Decimal
    required_monthly_contribution: Decimal | None
    estimated_completion_date: date | None
    estimated_completion_label: str
    is_overdue: bool
    is_achieved: bool
    created_at: datetime
    updated_at: datetime


class GoalContributionCreate(BaseModel):
    amount: Decimal = Field(..., gt=0)
    date: date
    kind: GoalContributionKind = GoalContributionKind.contribution
    transaction_id: uuid.UUID | None = None
    notes: str | None = Field(default=None, max_length=255)


class GoalContributionOut(BaseModel):
    id: uuid.UUID
    goal_id: uuid.UUID
    kind: GoalContributionKind
    amount: Decimal
    date: date
    transaction_id: uuid.UUID | None
    notes: str | None
    created_at: datetime

