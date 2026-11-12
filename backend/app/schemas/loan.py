from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Literal

from pydantic import BaseModel, Field

from app.models.enums import LoanEventKind, LoanStatus, LoanType


class LoanCreate(BaseModel):
    type: LoanType
    lender: str = Field(..., min_length=1, max_length=100)
    original_principal: Decimal = Field(..., gt=0)
    annual_rate: Decimal = Field(..., ge=0)
    tenure_months: int = Field(..., gt=0)
    start_date: date
    first_emi_date: date | None = None
    emi_amount: Decimal | None = Field(default=None, gt=0)
    baseline_outstanding: Decimal | None = Field(default=None, ge=0)
    baseline_date: date | None = None
    notes: str | None = Field(default=None, max_length=500)


class LoanUpdate(BaseModel):
    lender: str | None = Field(default=None, min_length=1, max_length=100)
    status: LoanStatus | None = None
    notes: str | None = Field(default=None, max_length=500)


class LoanOut(BaseModel):
    id: uuid.UUID
    type: LoanType
    lender: str
    original_principal: Decimal
    annual_rate: Decimal
    tenure_months: int
    start_date: date
    first_emi_date: date
    emi_amount: Decimal
    emi_overridden: bool
    baseline_outstanding: Decimal
    baseline_date: date
    current_outstanding: Decimal
    paid_principal: Decimal
    paid_interest: Decimal
    remaining_interest: Decimal
    remaining_installments: int
    next_emi_date: date | None
    next_emi_amount: Decimal | None
    end_date: date | None
    status: LoanStatus
    notes: str | None
    created_at: datetime
    updated_at: datetime


class LoanSummaryOut(BaseModel):
    total_outstanding: Decimal
    total_monthly_emi_commitment: Decimal
    active_loans_count: int


class InstallmentOut(BaseModel):
    installment_no: int
    due_date: date
    payment: Decimal
    principal: Decimal
    interest: Decimal
    closing_outstanding: Decimal
    is_paid: bool
    paid_date: date | None = None


class LoanScheduleOut(BaseModel):
    loan_id: uuid.UUID
    installments: list[InstallmentOut]
    total_interest: Decimal
    total_principal: Decimal
    emi: Decimal
    end_date: date | None


class LoanPaymentCreate(BaseModel):
    account_id: uuid.UUID
    payment_date: date
    payment_type: Literal["installment", "prepayment"] = "installment"
    amount: Decimal | None = Field(default=None, gt=0)
    principal_component: Decimal | None = Field(default=None, ge=0)
    interest_component: Decimal | None = Field(default=None, ge=0)
    installment_no: int | None = None
    strategy: Literal["reduce_tenure", "reduce_emi"] | None = None
    notes: str | None = Field(default=None, max_length=255)


class LoanPaymentOut(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    transaction_id: uuid.UUID
    account_id: uuid.UUID
    installment_no: int | None
    payment_date: date
    principal: Decimal
    interest: Decimal
    total_amount: Decimal
    current_outstanding: Decimal
    created_at: datetime


class LoanEventCreate(BaseModel):
    kind: LoanEventKind
    effective_date: date
    payload: dict[str, Any] = Field(default_factory=dict)


class LoanEventOut(BaseModel):
    id: uuid.UUID
    loan_id: uuid.UUID
    kind: LoanEventKind
    effective_date: date
    payload: dict[str, Any]
    created_at: datetime


class LoanSimulateRequest(BaseModel):
    kind: Literal["one_time_prepayment", "extra_monthly_payment", "rate_change"]
    effective_date: date
    amount: Decimal | None = None
    annual_rate: Decimal | None = None
    strategy: Literal["reduce_tenure", "reduce_emi", "keep_emi", "keep_tenure"] | None = None


class LoanSimulateOut(BaseModel):
    current_total_interest: Decimal
    current_emi: Decimal
    current_tenure_months: int
    current_end_date: date | None
    simulated_total_interest: Decimal
    simulated_emi: Decimal
    simulated_tenure_months: int
    simulated_end_date: date | None
    interest_saved: Decimal
    tenure_months_saved: int

