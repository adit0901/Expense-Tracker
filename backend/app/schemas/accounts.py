from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.core.money import MoneyOut, SignedAmount
from app.models.enums import AccountType

LAST4_PATTERN = r"^\d{4}$"


def _strip(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


class AccountCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: AccountType
    institution: str | None = Field(default=None, max_length=100)
    last4: str | None = Field(
        default=None,
        pattern=LAST4_PATTERN,
        description="Last 4 digits only; never a full account number",
    )
    currency: str = Field(default="INR", min_length=3, max_length=3)
    opening_balance: SignedAmount = Decimal("0")
    opening_date: date | None = None

    _strip_name = field_validator("name", "institution")(_strip)


class AccountUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: AccountType | None = None
    institution: str | None = Field(default=None, max_length=100)
    last4: str | None = Field(default=None, pattern=LAST4_PATTERN)
    opening_balance: SignedAmount | None = None
    opening_date: date | None = None

    _strip_name = field_validator("name", "institution")(_strip)


class AccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: AccountType
    institution: str | None
    last4: str | None
    currency: str
    opening_balance: MoneyOut
    opening_date: date
    archived_at: datetime | None
    current_balance: MoneyOut
    is_liability: bool
    balance_label: str
    created_at: datetime


class AccountsSummary(BaseModel):
    liquid_funds: MoneyOut = Field(description="Bank + cash balances (non-archived)")
    bank_balance: MoneyOut
    cash_balance: MoneyOut
    wallet_balance: MoneyOut
    credit_card_outstanding: MoneyOut
    currency: str = "INR"
