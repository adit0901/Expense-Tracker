"""SQL aggregation of derived account balances (mirrors services.calculations.balances)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable, Mapping
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import Numeric, and_, case, func, literal, select, union_all
from sqlalchemy.orm import Session

from app.models.account import Account
from app.models.enums import TransactionStatus, TransactionType
from app.models.transaction import Transaction
from app.services.calculations.balances import (
    COUNTER_SIGN,
    LIABILITY_ACCOUNT_TYPES,
    SOURCE_SIGN,
)


def _sign_case(table: Mapping[TransactionType, int]) -> Any:
    return case(
        *((Transaction.type == t, literal(sign)) for t, sign in table.items()), else_=literal(0)
    )


def account_balances(
    db: Session,
    user_id: uuid.UUID,
    account_ids: Iterable[uuid.UUID] | None = None,
    as_of: date | None = None,
) -> dict[uuid.UUID, Decimal]:
    """Current balance per account: opening + signed sum of posted txns on/after opening date."""
    posted = Transaction.status == TransactionStatus.posted
    source_side = select(
        Transaction.account_id.label("acct"),
        Transaction.txn_date.label("d"),
        (Transaction.amount * _sign_case(SOURCE_SIGN)).label("delta"),
    ).where(Transaction.user_id == user_id, posted)
    counter_side = select(
        Transaction.counter_account_id.label("acct"),
        Transaction.txn_date.label("d"),
        (Transaction.amount * _sign_case(COUNTER_SIGN)).label("delta"),
    ).where(Transaction.user_id == user_id, posted, Transaction.counter_account_id.is_not(None))
    moves = union_all(source_side, counter_side).subquery()

    polarity = case((Account.type.in_(list(LIABILITY_ACCOUNT_TYPES)), -1), else_=1)
    in_range = moves.c.d >= Account.opening_date
    if as_of is not None:
        in_range = and_(in_range, moves.c.d <= as_of)
    delta_sum = func.coalesce(func.sum(moves.c.delta).filter(in_range), literal(0))
    stmt = (
        select(Account.id, (Account.opening_balance + polarity * delta_sum).cast(Numeric(19, 4)))
        .outerjoin(moves, moves.c.acct == Account.id)
        .where(Account.user_id == user_id)
        .group_by(Account.id)
    )
    if account_ids is not None:
        stmt = stmt.where(Account.id.in_(list(account_ids)))
    return {row[0]: Decimal(row[1]) for row in db.execute(stmt)}
