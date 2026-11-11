"""DB-level CHECK constraints on transactions (task 5.1)."""

import uuid
from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.enums import PaymentMethod, TransactionType
from app.models.transaction import Transaction
from tests.factories import category_id, create_account
from tests.helpers import AuthedUser


def _try(db: Session, **kw: object) -> None:
    base: dict[str, object] = {"txn_date": date(2026, 10, 1), "amount": Decimal("10")}
    base.update(kw)
    with pytest.raises(IntegrityError), db.begin_nested():
        db.add(Transaction(**base))
        db.flush()


def test_constraints(user: AuthedUser, db: Session) -> None:
    a = uuid.UUID(str(create_account(user, "A")["id"]))
    b = uuid.UUID(str(create_account(user, "B")["id"]))
    food = category_id(db, user.id, "Food")
    common = {"user_id": user.id, "account_id": a}
    # Transfer with a category is rejected.
    _try(db, **common, type=TransactionType.transfer, counter_account_id=b, category_id=food)
    # Transfer without destination / to the same account.
    _try(db, **common, type=TransactionType.transfer)
    _try(db, **common, type=TransactionType.transfer, counter_account_id=a)
    # Expense without category or without payment method.
    _try(db, **common, type=TransactionType.expense, payment_method=PaymentMethod.upi)
    _try(db, **common, type=TransactionType.expense, category_id=food)
    # Non-positive amount.
    _try(
        db,
        **common,
        type=TransactionType.expense,
        category_id=food,
        payment_method=PaymentMethod.upi,
        amount=Decimal("0"),
    )
    # Counter account on a non-transfer.
    _try(
        db,
        **common,
        type=TransactionType.expense,
        category_id=food,
        payment_method=PaymentMethod.upi,
        counter_account_id=b,
    )
    # A valid transfer is accepted.
    db.add(
        Transaction(
            **common,
            type=TransactionType.transfer,
            counter_account_id=b,
            amount=Decimal("5"),
            txn_date=date(2026, 10, 1),
        )
    )
    db.flush()
