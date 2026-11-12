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
    loan_payment = "loan_payment"


class GoalType(StrEnum):
    emergency_fund = "emergency_fund"
    vacation = "vacation"
    house = "house"
    vehicle = "vehicle"
    education = "education"
    retirement = "retirement"
    other = "other"


class GoalStatus(StrEnum):
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class GoalContributionKind(StrEnum):
    contribution = "contribution"
    withdrawal = "withdrawal"


class AssetType(StrEnum):
    fixed_deposit = "fixed_deposit"
    gold = "gold"
    real_estate = "real_estate"
    ppf = "ppf"
    epf = "epf"
    nps = "nps"
    mutual_fund = "mutual_fund"
    vehicle = "vehicle"
    other = "other"


class LoanType(StrEnum):
    home = "home"
    car = "car"
    personal = "personal"
    education = "education"
    other = "other"


class LoanStatus(StrEnum):
    active = "active"
    closed = "closed"


class LoanEventKind(StrEnum):
    rate_change = "rate_change"
    prepayment = "prepayment"
    emi_override = "emi_override"


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
