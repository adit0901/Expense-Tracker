"""Duplicate detection (design D9): same account/type/amount, date ±1 day, similar text."""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, func, literal, or_, select
from sqlalchemy.orm import Session

from app.models.enums import TransactionType
from app.models.transaction import Transaction

SIMILARITY_THRESHOLD = 0.6
DATE_WINDOW_DAYS = 1


def normalize_text(payee: str | None, description: str | None) -> str:
    return " ".join(f"{payee or ''} {description or ''}".lower().split())


def _norm_sql() -> Any:
    return func.lower(
        func.trim(
            func.concat_ws(
                " ",
                func.coalesce(Transaction.payee, ""),
                func.coalesce(Transaction.description, ""),
            )
        )
    )


def find_duplicates(
    db: Session,
    user_id: uuid.UUID,
    *,
    account_id: uuid.UUID,
    txn_type: TransactionType,
    amount: Decimal,
    txn_date: date,
    payee: str | None,
    description: str | None,
    exclude_id: uuid.UUID | None = None,
    limit: int = 5,
) -> list[Transaction]:
    text = normalize_text(payee, description)
    norm = _norm_sql()
    similar = (
        norm == literal("")
        if not text
        else or_(func.similarity(norm, literal(text)) >= SIMILARITY_THRESHOLD, norm == text)
    )
    stmt = (
        select(Transaction)
        .where(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.type == txn_type,
            Transaction.amount == amount,
            and_(
                Transaction.txn_date >= txn_date - timedelta(days=DATE_WINDOW_DAYS),
                Transaction.txn_date <= txn_date + timedelta(days=DATE_WINDOW_DAYS),
            ),
            similar,
        )
        .order_by(Transaction.txn_date.desc())
        .limit(limit)
    )
    if exclude_id is not None:
        stmt = stmt.where(Transaction.id != exclude_id)
    return list(db.scalars(stmt))
