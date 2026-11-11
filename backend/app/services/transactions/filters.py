"""Filter/sort translation for transaction queries (always parameterized)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.models.transaction import Transaction
from app.schemas.transactions import TransactionFilters
from app.services.categories import subtree_ids

SORTS = {
    "date": Transaction.txn_date,
    "amount": Transaction.amount,
    "created_at": Transaction.created_at,
}
DEFAULT_SORT = [Transaction.txn_date.desc(), Transaction.created_at.desc()]


def escape_like(term: str) -> str:
    return term.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def build_conditions(db: Session, user_id: uuid.UUID, f: TransactionFilters) -> list[Any]:
    conds: list[Any] = [Transaction.user_id == user_id]
    if f.date_from is not None:
        conds.append(Transaction.txn_date >= f.date_from)
    if f.date_to is not None:
        conds.append(Transaction.txn_date <= f.date_to)
    if f.types:
        conds.append(Transaction.type.in_(f.types))
    if f.account_id is not None:
        conds.append(
            or_(
                Transaction.account_id == f.account_id,
                Transaction.counter_account_id == f.account_id,
            )
        )
    if f.category_id is not None:
        conds.append(Transaction.category_id.in_(subtree_ids(db, user_id, f.category_id)))
    if f.payment_method is not None:
        conds.append(Transaction.payment_method == f.payment_method)
    if f.amount_min is not None:
        conds.append(Transaction.amount >= f.amount_min)
    if f.amount_max is not None:
        conds.append(Transaction.amount <= f.amount_max)
    if f.tag:
        conds.append(Transaction.tags.contains([f.tag.strip().lower()]))
    if f.income_source_id is not None:
        conds.append(Transaction.income_source_id == f.income_source_id)
    if f.import_batch_id is not None:
        conds.append(Transaction.import_batch_id == f.import_batch_id)
    if f.q and f.q.strip():
        pattern = f"%{escape_like(f.q.strip())}%"
        conds.append(
            or_(
                Transaction.payee.ilike(pattern, escape="\\"),
                Transaction.description.ilike(pattern, escape="\\"),
                Transaction.notes.ilike(pattern, escape="\\"),
            )
        )
    return conds
