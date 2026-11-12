"""Import all models so Alembic and SQLAlchemy see the full metadata."""

from app.models.account import Account
from app.models.asset import Asset, AssetValuation, Liability, LiabilityBalance
from app.models.audit import AuditLog
from app.models.budget import Budget, BudgetAlert, BudgetLine
from app.models.category import Category
from app.models.goal import Goal, GoalContribution, SavingsTarget
from app.models.income_source import IncomeSource
from app.models.loan import Loan, LoanEventModel, LoanPayment
from app.models.net_worth import NetWorthSnapshot
from app.models.transaction import (
    Attachment,
    IdempotencyKey,
    ImportBatch,
    SalaryComponent,
    Transaction,
)
from app.models.user import PasswordResetToken, RefreshToken, User, UserPreferences

__all__ = [
    "Account",
    "Asset",
    "AssetValuation",
    "Attachment",
    "AuditLog",
    "Budget",
    "BudgetAlert",
    "BudgetLine",
    "Category",
    "Goal",
    "GoalContribution",
    "IdempotencyKey",
    "ImportBatch",
    "IncomeSource",
    "Liability",
    "LiabilityBalance",
    "Loan",
    "LoanEventModel",
    "LoanPayment",
    "NetWorthSnapshot",
    "PasswordResetToken",
    "RefreshToken",
    "SalaryComponent",
    "SavingsTarget",
    "Transaction",
    "User",
    "UserPreferences",
]
