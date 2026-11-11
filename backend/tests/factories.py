"""Direct-DB factories for tests that need data before the corresponding API exists."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.enums import CategoryKind, PaymentMethod, TransactionType
from app.models.transaction import Transaction
from tests.helpers import AuthedUser, data


def create_account(
    u: AuthedUser,
    name: str = "HDFC Savings",
    type: str = "bank",
    opening_balance: str = "0.00",
    opening_date: str = "2026-01-01",
    **extra: object,
) -> dict[str, object]:
    body = {
        "name": name,
        "type": type,
        "opening_balance": opening_balance,
        "opening_date": opening_date,
        **extra,
    }
    result: dict[str, object] = data(u.post("/api/v1/accounts", json=body))
    return result


def category_id(
    db: Session, user_id: uuid.UUID, name: str, kind: CategoryKind = CategoryKind.expense
) -> uuid.UUID:
    return db.scalars(
        select(Category.id).where(
            Category.user_id == user_id, Category.kind == kind, Category.name == name
        )
    ).one()


def insert_txn(
    db: Session,
    user_id: uuid.UUID,
    *,
    type: TransactionType,
    account_id: object,
    amount: str,
    txn_date: date = date(2026, 10, 15),
    category_id: uuid.UUID | None = None,
    counter_account_id: object = None,
    payment_method: PaymentMethod | None = None,
) -> Transaction:
    if type == TransactionType.expense and payment_method is None:
        payment_method = PaymentMethod.upi
    txn = Transaction(
        user_id=user_id,
        type=type,
        account_id=uuid.UUID(str(account_id)),
        counter_account_id=uuid.UUID(str(counter_account_id)) if counter_account_id else None,
        category_id=category_id,
        amount=Decimal(amount),
        txn_date=txn_date,
        payment_method=payment_method,
    )
    db.add(txn)
    db.commit()
    return txn
