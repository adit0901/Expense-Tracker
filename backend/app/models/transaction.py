from __future__ import annotations

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    CHAR,
    BigInteger,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import IdMixin, TimestampMixin
from app.models.enums import (
    ImportStatus,
    PaymentMethod,
    SalaryComponentKind,
    TransactionStatus,
    TransactionType,
    pg_enum,
)


class Transaction(IdMixin, TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "type <> 'transfer' OR (counter_account_id IS NOT NULL "
            "AND counter_account_id <> account_id AND category_id IS NULL)",
            name="transfer_shape",
        ),
        CheckConstraint(
            "type = 'transfer' OR counter_account_id IS NULL", name="counter_only_for_transfer"
        ),
        CheckConstraint(
            "type NOT IN ('income', 'expense', 'refund') OR category_id IS NOT NULL",
            name="category_required",
        ),
        CheckConstraint(
            "type <> 'expense' OR payment_method IS NOT NULL", name="expense_payment_method"
        ),
        CheckConstraint("type = 'income' OR income_source_id IS NULL", name="source_only_income"),
        CheckConstraint("type = 'refund' OR refund_of_id IS NULL", name="refund_of_only_refund"),
        Index("ix_txn_user_date", "user_id", "txn_date"),
        Index("ix_txn_user_account_date", "user_id", "account_id", "txn_date"),
        Index("ix_txn_user_counter_date", "user_id", "counter_account_id", "txn_date"),
        Index("ix_txn_user_category_date", "user_id", "category_id", "txn_date"),
        Index("ix_txn_import_batch", "import_batch_id"),
        Index(
            "ix_txn_payee_trgm",
            "payee",
            postgresql_using="gin",
            postgresql_ops={"payee": "gin_trgm_ops"},
        ),
        Index(
            "ix_txn_description_trgm",
            "description",
            postgresql_using="gin",
            postgresql_ops={"description": "gin_trgm_ops"},
        ),
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE")
    )
    type: Mapped[TransactionType] = mapped_column(pg_enum(TransactionType, "transaction_type"))
    status: Mapped[TransactionStatus] = mapped_column(
        pg_enum(TransactionStatus, "transaction_status"), default=TransactionStatus.posted
    )
    account_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("accounts.id"))
    counter_account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id")
    )
    category_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id")
    )
    income_source_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("income_sources.id", ondelete="SET NULL")
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    currency: Mapped[str] = mapped_column(CHAR(3), default="INR")
    txn_date: Mapped[date] = mapped_column(Date)
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        pg_enum(PaymentMethod, "payment_method")
    )
    payee: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(String(255))
    notes: Mapped[str | None] = mapped_column(Text)
    tags: Mapped[list[str]] = mapped_column(ARRAY(String(40)), default=list)
    refund_of_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="SET NULL")
    )
    import_batch_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("import_batches.id", ondelete="SET NULL")
    )
    import_fingerprint: Mapped[str | None] = mapped_column(CHAR(64))

    salary_components: Mapped[list[SalaryComponent]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True, order_by="SalaryComponent.position"
    )


class SalaryComponent(IdMixin, Base):
    __tablename__ = "salary_components"
    __table_args__ = (CheckConstraint("amount >= 0", name="amount_non_negative"),)

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    kind: Mapped[SalaryComponentKind] = mapped_column(
        pg_enum(SalaryComponentKind, "salary_component_kind")
    )
    name: Mapped[str] = mapped_column(String(60))
    amount: Mapped[Decimal] = mapped_column(Numeric(19, 4))
    position: Mapped[int] = mapped_column(Integer, default=0)


class Attachment(IdMixin, TimestampMixin, Base):
    __tablename__ = "attachments"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    transaction_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("transactions.id", ondelete="CASCADE"), index=True
    )
    storage_key: Mapped[str] = mapped_column(String(100), unique=True)
    original_name: Mapped[str] = mapped_column(String(255))
    mime_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(BigInteger)
    sha256: Mapped[str] = mapped_column(CHAR(64))


class ImportBatch(IdMixin, TimestampMixin, Base):
    __tablename__ = "import_batches"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("accounts.id", ondelete="CASCADE")
    )
    status: Mapped[ImportStatus] = mapped_column(
        pg_enum(ImportStatus, "import_status"), default=ImportStatus.preview
    )
    file_name: Mapped[str] = mapped_column(String(255))
    encoding: Mapped[str] = mapped_column(String(30))
    date_format: Mapped[str] = mapped_column(String(20))
    column_mapping: Mapped[dict[str, Any]] = mapped_column(JSONB)
    row_count: Mapped[int] = mapped_column(Integer, default=0)
    imported_count: Mapped[int] = mapped_column(Integer, default=0)
    preview: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    undone_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class IdempotencyKey(Base):
    """Remembers POST results so retried requests with the same key don't duplicate work."""

    __tablename__ = "idempotency_keys"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    key: Mapped[str] = mapped_column(String(100), primary_key=True)
    endpoint: Mapped[str] = mapped_column(String(100))
    request_hash: Mapped[str] = mapped_column(CHAR(64))
    response_status: Mapped[int] = mapped_column(Integer)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
