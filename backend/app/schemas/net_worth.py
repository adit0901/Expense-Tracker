"""Pydantic schemas for Net Worth and Snapshots."""

from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict, field_serializer

from app.core.money import round_money


class BreakdownItemOut(BaseModel):
    category: str
    amount: Decimal
    share_pct: Decimal


class GrowthOut(BaseModel):
    amount_change: Decimal | None = None
    percentage_change: Decimal | None = None


class NetWorthOut(BaseModel):
    as_of: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    liquid_assets: Decimal
    asset_breakdown: list[BreakdownItemOut]
    liability_breakdown: list[BreakdownItemOut]
    mom_growth: GrowthOut | None = None
    yoy_growth: GrowthOut | None = None
    is_stale: bool = False


class NetWorthSnapshotCreate(BaseModel):
    as_of: date | None = None


class NetWorthSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    as_of: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    breakdown: dict[str, Any]
    computed_at: datetime
    is_stale: bool

    @field_serializer("total_assets", "total_liabilities", "net_worth")
    def _ser_money(self, v: Decimal) -> str:
        return str(round_money(v))


class EmergencyFundMetricsOut(BaseModel):
    liquid_savings: Decimal
    essential_monthly_expenses: Decimal
    coverage_months: Decimal | None
