"""Aggregate queries feeding the calculation functions (all scoped by user, posted only)."""

from __future__ import annotations

import uuid
from collections import defaultdict
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import String, case, extract, func, literal, select
from sqlalchemy.orm import Session, aliased

from app.models.category import Category
from app.models.enums import SalaryComponentKind, TransactionStatus, TransactionType
from app.models.income_source import IncomeSource
from app.models.transaction import SalaryComponent, Transaction

T = Transaction


def _scope(user_id: uuid.UUID, start: date, end: date) -> list[Any]:
    return [
        T.user_id == user_id,
        T.status == TransactionStatus.posted,
        T.txn_date >= start,
        T.txn_date <= end,
    ]


def totals_by_type(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[TransactionType, Decimal]:
    rows = db.execute(
        select(T.type, func.sum(T.amount)).where(*_scope(user_id, start, end)).group_by(T.type)
    )
    return {r[0]: Decimal(r[1]) for r in rows}


def monthly_by_type(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[tuple[int, int], dict[TransactionType, Decimal]]:
    y, m = extract("year", T.txn_date), extract("month", T.txn_date)
    rows = db.execute(
        select(y, m, T.type, func.sum(T.amount))
        .where(*_scope(user_id, start, end))
        .group_by(y, m, T.type)
    )
    out: dict[tuple[int, int], dict[TransactionType, Decimal]] = defaultdict(dict)
    for yy, mm, t, amt in rows:
        out[(int(yy), int(mm))][t] = Decimal(amt)
    return out


def _net_expense_amount() -> Any:
    return case((T.type == TransactionType.refund, -T.amount), else_=T.amount)


_EXPENSE_TYPES = (TransactionType.expense, TransactionType.refund)


def expense_net_by_category(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> list[tuple[uuid.UUID, uuid.UUID, Decimal]]:
    """(top_level_category_id, category_id, net expense) rows."""
    top = func.coalesce(Category.parent_id, Category.id)
    rows = db.execute(
        select(top, Category.id, func.sum(_net_expense_amount()))
        .join(Category, Category.id == T.category_id)
        .where(*_scope(user_id, start, end), T.type.in_(_EXPENSE_TYPES))
        .group_by(top, Category.id)
    )
    return [(r[0], r[1], Decimal(r[2])) for r in rows]


def expense_net_by_method(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[str, Decimal]:
    """Net expense per payment method. A refund counts against its own method, else the
    original expense's method, else 'other' — so methods always sum to total expenses."""
    orig = aliased(Transaction)
    method = func.coalesce(
        T.payment_method.cast(String), orig.payment_method.cast(String), literal("other")
    )
    rows = db.execute(
        select(method, func.sum(_net_expense_amount()))
        .outerjoin(orig, orig.id == T.refund_of_id)
        .where(*_scope(user_id, start, end), T.type.in_(_EXPENSE_TYPES))
        .group_by(method)
    )
    return {str(r[0]): Decimal(r[1]) for r in rows}


def income_by_source(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> list[tuple[uuid.UUID | None, str | None, str | None, Decimal]]:
    rows = db.execute(
        select(IncomeSource.id, IncomeSource.name, IncomeSource.type, func.sum(T.amount))
        .outerjoin(IncomeSource, IncomeSource.id == T.income_source_id)
        .where(*_scope(user_id, start, end), T.type == TransactionType.income)
        .group_by(IncomeSource.id, IncomeSource.name, IncomeSource.type)
    )
    return [(r[0], r[1], r[2].value if r[2] else None, Decimal(r[3])) for r in rows]


def income_by_category(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[uuid.UUID, Decimal]:
    top = func.coalesce(Category.parent_id, Category.id)
    rows = db.execute(
        select(top, func.sum(T.amount))
        .join(Category, Category.id == T.category_id)
        .where(*_scope(user_id, start, end), T.type == TransactionType.income)
        .group_by(top)
    )
    return {r[0]: Decimal(r[1]) for r in rows}


def salary_components(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> list[tuple[int, int, SalaryComponentKind, str, Decimal]]:
    """(year, month, kind, name, amount) for salary breakdowns of income in the period."""
    y, m = extract("year", T.txn_date), extract("month", T.txn_date)
    rows = db.execute(
        select(y, m, SalaryComponent.kind, SalaryComponent.name, func.sum(SalaryComponent.amount))
        .join(T, T.id == SalaryComponent.transaction_id)
        .where(*_scope(user_id, start, end), T.type == TransactionType.income)
        .group_by(y, m, SalaryComponent.kind, SalaryComponent.name)
    )
    return [(int(r[0]), int(r[1]), r[2], r[3], Decimal(r[4])) for r in rows]


def categories_by_id(db: Session, user_id: uuid.UUID) -> dict[uuid.UUID, Category]:
    return {c.id: c for c in db.scalars(select(Category).where(Category.user_id == user_id))}
