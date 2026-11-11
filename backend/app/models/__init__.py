"""Import all models so Alembic and SQLAlchemy see the full metadata."""

from app.models.account import Account
from app.models.audit import AuditLog
from app.models.category import Category
from app.models.income_source import IncomeSource
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
    "Attachment",
    "AuditLog",
    "Category",
    "IdempotencyKey",
    "ImportBatch",
    "IncomeSource",
    "PasswordResetToken",
    "RefreshToken",
    "SalaryComponent",
    "Transaction",
    "User",
    "UserPreferences",
]
