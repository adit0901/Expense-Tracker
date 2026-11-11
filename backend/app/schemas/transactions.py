from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field, field_validator

from app.core.money import MoneyOut, PositiveAmount
from app.core.responses import PageMeta
from app.models.enums import PaymentMethod, TransactionType

MAX_TAGS = 20


def _clean_text(v: str | None) -> str | None:
    if v is None:
        return None
    v = v.strip()
    return v or None


def _clean_tags(v: list[str] | None) -> list[str] | None:
    if v is None:
        return None
    out: list[str] = []
    for t in v:
        t = t.strip().lower()
        if t and t not in out:
            out.append(t)
    return out


class DeductionIn(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    amount: PositiveAmount


class SalaryBreakdownIn(BaseModel):
    gross: PositiveAmount
    deductions: list[DeductionIn] = Field(default_factory=list, max_length=20)


class TransactionFields(BaseModel):
    """Fields shared by create and update (all optional here; create tightens)."""

    account_id: uuid.UUID | None = None
    counter_account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    income_source_id: uuid.UUID | None = None
    amount: PositiveAmount | None = None
    txn_date: date | None = None
    payment_method: PaymentMethod | None = None
    payee: str | None = Field(default=None, max_length=120)
    description: str | None = Field(default=None, max_length=255)
    notes: str | None = Field(default=None, max_length=2000)
    tags: list[str] | None = Field(default=None, max_length=MAX_TAGS)
    refund_of_id: uuid.UUID | None = None
    salary_breakdown: SalaryBreakdownIn | None = None

    _t = field_validator("payee", "description", "notes")(_clean_text)
    _g = field_validator("tags")(_clean_tags)

    @field_validator("tags")
    @classmethod
    def _tag_length(cls, v: list[str] | None) -> list[str] | None:
        if v and any(len(t) > 40 for t in v):
            raise ValueError("each tag must be at most 40 characters")
        return v


class TransactionCreate(TransactionFields):
    type: TransactionType
    account_id: uuid.UUID
    amount: PositiveAmount
    txn_date: date
    confirm_duplicate: bool = False


class TransactionUpdate(TransactionFields):
    type: TransactionType | None = None
    confirm_duplicate: bool = False


class AttachmentOut(BaseModel):
    id: uuid.UUID
    original_name: str
    mime_type: str
    size_bytes: int
    created_at: datetime


class SalaryComponentOut(BaseModel):
    kind: str
    name: str
    amount: MoneyOut


class SalaryBreakdownOut(BaseModel):
    gross: MoneyOut
    deductions: list[SalaryComponentOut]
    total_deductions: MoneyOut
    net: MoneyOut


class TransactionOut(BaseModel):
    id: uuid.UUID
    type: TransactionType
    status: str
    account_id: uuid.UUID
    account_name: str | None
    counter_account_id: uuid.UUID | None
    counter_account_name: str | None
    category_id: uuid.UUID | None
    category_name: str | None
    parent_category_id: uuid.UUID | None
    parent_category_name: str | None
    income_source_id: uuid.UUID | None
    amount: MoneyOut
    currency: str
    txn_date: date
    payment_method: PaymentMethod | None
    payee: str | None
    description: str | None
    notes: str | None
    tags: list[str]
    refund_of_id: uuid.UUID | None
    import_batch_id: uuid.UUID | None
    salary_breakdown: SalaryBreakdownOut | None
    attachments: list[AttachmentOut]
    created_at: datetime
    updated_at: datetime


class DuplicateCandidate(BaseModel):
    id: uuid.UUID
    txn_date: date
    amount: MoneyOut
    type: TransactionType
    payee: str | None
    description: str | None


class DuplicateCheckOut(BaseModel):
    is_possible_duplicate: bool
    candidates: list[DuplicateCandidate]


class TransactionTotals(BaseModel):
    count: int
    total_amount: MoneyOut
    income: MoneyOut
    expense: MoneyOut
    refund: MoneyOut
    transfer: MoneyOut
    net_expense: MoneyOut = Field(description="expense - refund")


class TransactionPageMeta(PageMeta):
    totals: TransactionTotals


class TransactionPage(BaseModel):
    data: list[TransactionOut]
    meta: TransactionPageMeta


class TransactionFilters(BaseModel):
    date_from: date | None = None
    date_to: date | None = None
    types: list[TransactionType] | None = None
    account_id: uuid.UUID | None = None
    category_id: uuid.UUID | None = None
    payment_method: PaymentMethod | None = None
    amount_min: Decimal | None = None
    amount_max: Decimal | None = None
    tag: str | None = None
    q: str | None = None
    income_source_id: uuid.UUID | None = None
    import_batch_id: uuid.UUID | None = None
