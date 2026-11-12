from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import GoalContributionKind, GoalStatus, GoalType, pg_enum


class SavingsTarget(IdMixin, TimestampMixin, Base):
    __tablename__ = "savings_targets"
    __table_args__ = (
        Index("uq_savings_targets_user_effective", "user_id", "effective_from", unique=True),
        CheckConstraint("amount > 0", name="savings_target_positive"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    effective_from: Mapped[date] = mapped_column(Date)
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))


class Goal(IdMixin, TimestampMixin, Base):
    __tablename__ = "goals"
    __table_args__ = (
        Index("ix_goals_user_id", "user_id"),
        CheckConstraint("target_amount > 0", name="goal_target_positive"),
        CheckConstraint("starting_amount >= 0", name="goal_starting_non_negative"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    type: Mapped[GoalType] = mapped_column(pg_enum(GoalType, "goal_type"))
    target_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    target_date: Mapped[date | None] = mapped_column(Date)
    starting_amount: Mapped[Decimal] = mapped_column(Numeric(19, 4), default=Decimal("0.00"))
    status: Mapped[GoalStatus] = mapped_column(
        pg_enum(GoalStatus, "goal_status"), default=GoalStatus.active
    )
    notes: Mapped[str | None] = mapped_column(Text)

    contributions: Mapped[list[GoalContribution]] = relationship(
        "GoalContribution", back_populates="goal", cascade="all, delete-orphan"
    )


class GoalContribution(IdMixin, TimestampMixin, Base):
    __tablename__ = "goal_contributions"
    __table_args__ = (
        Index("ix_goal_contributions_goal_date", "goal_id", "date"),
        CheckConstraint("amount > 0", name="goal_contribution_amount_positive"),
    )

    goal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("goals.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[GoalContributionKind] = mapped_column(
        pg_enum(GoalContributionKind, "goal_contribution_kind"),
        default=GoalContributionKind.contribution,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    date: Mapped[date] = mapped_column(Date)
    transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    notes: Mapped[str | None] = mapped_column(String(255))

    goal: Mapped[Goal] = relationship("Goal", back_populates="contributions")

