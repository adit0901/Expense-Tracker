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
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import AssetType, pg_enum


class Asset(IdMixin, TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        Index("ix_assets_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[AssetType] = mapped_column(pg_enum(AssetType, "asset_type"))
    name: Mapped[str] = mapped_column(String(100))
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    is_liquid: Mapped[bool] = mapped_column(Boolean, default=False)
    closed_at: Mapped[date | None] = mapped_column(Date)

    valuations: Mapped[list[AssetValuation]] = relationship(
        "AssetValuation", back_populates="asset", cascade="all, delete-orphan"
    )


class AssetValuation(IdMixin, TimestampMixin, Base):
    __tablename__ = "asset_valuations"
    __table_args__ = (
        Index("uq_asset_valuations_asset_as_of", "asset_id", "as_of", unique=True),
        CheckConstraint("value >= 0", name="asset_valuation_non_negative"),
    )

    asset_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    as_of: Mapped[date] = mapped_column(Date)
    value: Mapped[Decimal] = mapped_column(Numeric(19, 4))

    asset: Mapped[Asset] = relationship("Asset", back_populates="valuations")


class Liability(IdMixin, TimestampMixin, Base):
    __tablename__ = "liabilities"
    __table_args__ = (
        Index("ix_liabilities_user_id", "user_id"),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    notes: Mapped[str | None] = mapped_column(Text)
    closed_at: Mapped[date | None] = mapped_column(Date)

    balances: Mapped[list[LiabilityBalance]] = relationship(
        "LiabilityBalance", back_populates="liability", cascade="all, delete-orphan"
    )


class LiabilityBalance(IdMixin, TimestampMixin, Base):
    __tablename__ = "liability_balances"
    __table_args__ = (
        Index("uq_liability_balances_liability_as_of", "liability_id", "as_of", unique=True),
        CheckConstraint("balance >= 0", name="liability_balance_non_negative"),
    )

    liability_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("liabilities.id", ondelete="CASCADE"), index=True
    )
    as_of: Mapped[date] = mapped_column(Date)
    balance: Mapped[Decimal] = mapped_column(Numeric(19, 4))

    liability: Mapped[Liability] = relationship("Liability", back_populates="balances")

