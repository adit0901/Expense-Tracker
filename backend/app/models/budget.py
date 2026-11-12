from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin


class Budget(IdMixin, TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        Index("uq_budgets_user_month", "user_id", "month", unique=True),
        CheckConstraint(
            "overall_amount IS NULL OR overall_amount > 0",
            name="budget_overall_positive",
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[date] = mapped_column(Date)
    overall_amount: Mapped[Decimal | None] = mapped_column(Numeric(19, 4))

    lines: Mapped[list[BudgetLine]] = relationship(
        "BudgetLine", back_populates="budget", cascade="all, delete-orphan"
    )


class BudgetLine(IdMixin, TimestampMixin, Base):
    __tablename__ = "budget_lines"
    __table_args__ = (
        Index("uq_budget_lines_budget_category", "budget_id", "category_id", unique=True),
        CheckConstraint("amount > 0", name="budget_line_amount_positive"),
    )

    budget_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budgets.id", ondelete="CASCADE"), index=True
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    alert_thresholds: Mapped[list[int]] = mapped_column(
        ARRAY(Integer), default=lambda: [80, 100]
    )

    budget: Mapped[Budget] = relationship("Budget", back_populates="lines")
    alerts: Mapped[list[BudgetAlert]] = relationship(
        "BudgetAlert", back_populates="budget_line", cascade="all, delete-orphan"
    )


class BudgetAlert(IdMixin, Base):
    __tablename__ = "budget_alerts"
    __table_args__ = (
        Index(
            "uq_budget_alerts_line_month_threshold",
            "user_id",
            "budget_line_id",
            "month",
            "threshold",
            unique=True,
            postgresql_nulls_not_distinct=True,
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    budget_line_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("budget_lines.id", ondelete="CASCADE"), index=True
    )
    month: Mapped[date] = mapped_column(Date)
    threshold: Mapped[int] = mapped_column(Integer)
    triggered_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    budget_line: Mapped[BudgetLine | None] = relationship("BudgetLine", back_populates="alerts")

