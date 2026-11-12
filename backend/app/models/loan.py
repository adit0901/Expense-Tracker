from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import LoanEventKind, LoanStatus, LoanType, pg_enum


class Loan(IdMixin, TimestampMixin, Base):
    __tablename__ = "loans"
    __table_args__ = (
        Index("ix_loans_user_id", "user_id"),
        CheckConstraint("original_principal > 0", name="loan_principal_positive"),
        CheckConstraint("annual_rate >= 0", name="loan_rate_non_negative"),
        CheckConstraint("tenure_months > 0", name="loan_tenure_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[LoanType] = mapped_column(pg_enum(LoanType, "loan_type"))
    lender: Mapped[str] = mapped_column(String(100))
    original_principal: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    annual_rate: Mapped[Decimal] = mapped_column(Numeric(7, 4))
    tenure_months: Mapped[int] = mapped_column(Integer)
    start_date: Mapped[date] = mapped_column(Date)
    first_emi_date: Mapped[date] = mapped_column(Date)
    emi_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    emi_overridden: Mapped[bool] = mapped_column(Boolean, default=False)
    baseline_outstanding: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))
    baseline_date: Mapped[date | None] = mapped_column(Date)
    status: Mapped[LoanStatus] = mapped_column(
        pg_enum(LoanStatus, "loan_status"), default=LoanStatus.active
    )
    notes: Mapped[str | None] = mapped_column(Text)

    events: Mapped[list[LoanEventModel]] = relationship(
        "LoanEventModel", back_populates="loan", cascade="all, delete-orphan"
    )
    payments: Mapped[list[LoanPayment]] = relationship(
        "LoanPayment", back_populates="loan", cascade="all, delete-orphan"
    )


class LoanEventModel(IdMixin, TimestampMixin, Base):
    __tablename__ = "loan_events"
    __table_args__ = (
        Index("ix_loan_events_loan_date", "loan_id", "effective_date"),
    )

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[LoanEventKind] = mapped_column(pg_enum(LoanEventKind, "loan_event_kind"))
    effective_date: Mapped[date] = mapped_column(Date)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)

    loan: Mapped[Loan] = relationship("Loan", back_populates="events")


class LoanPayment(IdMixin, TimestampMixin, Base):
    __tablename__ = "loan_payments"
    __table_args__ = (
        Index("uq_loan_payments_transaction", "transaction_id", unique=True),
        Index("ix_loan_payments_loan_id", "loan_id"),
    )

    loan_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("loans.id", ondelete="CASCADE"), index=True
    )
    installment_no: Mapped[int | None] = mapped_column(Integer)
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE")
    )
    principal: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    interest: Mapped[Decimal] = mapped_column(Numeric(19, 4))

    loan: Mapped[Loan] = relationship("Loan", back_populates="payments")

