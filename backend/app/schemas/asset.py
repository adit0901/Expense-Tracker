from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.enums import AssetType


class AssetValuationIn(BaseModel):
    as_of: date
    value: Decimal = Field(..., ge=0)


class AssetValuationOut(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    as_of: date
    value: Decimal
    created_at: datetime


class AssetCreate(BaseModel):
    type: str
    name: str = Field(..., min_length=1, max_length=100)
    current_value: Decimal = Field(..., ge=0)
    as_of: date | None = None
    is_liquid: bool = False
    details: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type")
    @classmethod
    def validate_type(cls, v: str) -> str:
        v_clean = v.strip().lower()
        if v_clean == "bank":
            raise ValueError(
                "Assets cannot be of type 'bank'. Please add a financial account instead."
            )
        try:
            AssetType(v_clean)
        except ValueError:
            valid_types = ", ".join(t.value for t in AssetType)
            raise ValueError(
                f"Invalid asset type '{v}'. Allowed types: {valid_types}"
            ) from None
        return v_clean


class AssetUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    is_liquid: bool | None = None
    details: dict[str, Any] | None = None


class AssetCloseIn(BaseModel):
    closed_at: date


class AssetOut(BaseModel):
    id: uuid.UUID
    type: AssetType
    name: str
    is_liquid: bool
    details: dict[str, Any]
    current_value: Decimal
    latest_valuation_date: date | None
    closed_at: date | None
    created_at: datetime
    updated_at: datetime


# Liability schemas
class LiabilityBalanceIn(BaseModel):
    as_of: date
    balance: Decimal = Field(..., ge=0)


class LiabilityBalanceOut(BaseModel):
    id: uuid.UUID
    liability_id: uuid.UUID
    as_of: date
    balance: Decimal
    created_at: datetime


class LiabilityCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    current_balance: Decimal = Field(..., ge=0)
    as_of: date | None = None
    notes: str | None = Field(default=None, max_length=500)


class LiabilityUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    notes: str | None = Field(default=None, max_length=500)


class LiabilityCloseIn(BaseModel):
    closed_at: date


class LiabilityOut(BaseModel):
    id: uuid.UUID
    name: str
    current_balance: Decimal
    latest_balance_date: date | None
    notes: str | None
    closed_at: date | None
    created_at: datetime
    updated_at: datetime
