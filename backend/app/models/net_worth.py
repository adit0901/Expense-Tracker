from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin


class NetWorthSnapshot(IdMixin, TimestampMixin, Base):
    __tablename__ = "net_worth_snapshots"
    __table_args__ = (
        Index("uq_net_worth_snapshots_user_as_of", "user_id", "as_of", unique=True),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    as_of: Mapped[date] = mapped_column(Date)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    breakdown: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict)
    computed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    is_stale: Mapped[bool] = mapped_column(Boolean, default=False)

