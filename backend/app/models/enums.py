"""Enumerations shared by models, schemas and services (PostgreSQL native enums)."""

from __future__ import annotations

from enum import StrEnum

import sqlalchemy as sa


class AccountType(StrEnum):
    bank = "bank"
    cash = "cash"
    credit_card = "credit_card"
    wallet = "wallet"


class CategoryKind(StrEnum):
    income = "income"
    expense = "expense"


class TransactionType(StrEnum):
    income = "income"
    expense = "expense"
    transfer = "transfer"
    refund = "refund"


class PaymentMethod(StrEnum):
    upi = "upi"
    cash = "cash"
    debit_card = "debit_card"
    credit_card = "credit_card"
    bank_transfer = "bank_transfer"
    other = "other"


class TransactionStatus(StrEnum):
    posted = "posted"


class IncomeSourceType(StrEnum):
    salary = "salary"
    bonus = "bonus"
    freelance = "freelance"
    business = "business"
    rental = "rental"
    dividend = "dividend"
    interest = "interest"
    other = "other"


class SalaryComponentKind(StrEnum):
    gross = "gross"
    deduction = "deduction"


class ImportStatus(StrEnum):
    preview = "preview"
    confirmed = "confirmed"
    undone = "undone"


def pg_enum(enum_cls: type[StrEnum], name: str) -> sa.Enum:
    return sa.Enum(enum_cls, name=name, values_callable=lambda e: [m.value for m in e])
