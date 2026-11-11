"""Financial accounts: CRUD, archive, derived balances and summary."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import exists, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationAppError
from app.core.money import SUPPORTED_CURRENCIES, ZERO
from app.core.pagination import PageParams, paginate, parse_sort
from app.core.responses import PageMeta
from app.core.timeutil import today_in
from app.models.account import Account
from app.models.enums import AccountType
from app.models.transaction import Transaction
from app.repositories.balances import account_balances
from app.repositories.base import OwnedRepository
from app.schemas.accounts import AccountCreate, AccountOut, AccountsSummary, AccountUpdate
from app.services import audit
from app.services.calculations.balances import LIABILITY_ACCOUNT_TYPES

SORTS = {"name": Account.name, "type": Account.type, "created_at": Account.created_at}


class AccountRepository(OwnedRepository[Account]):
    model = Account
    entity_name = "Account"


def to_out(account: Account, balance: Decimal) -> AccountOut:
    is_liability = account.type in LIABILITY_ACCOUNT_TYPES
    return AccountOut.model_validate(
        {
            **{
                c: getattr(account, c)
                for c in (
                    "id",
                    "name",
                    "type",
                    "institution",
                    "last4",
                    "currency",
                    "opening_balance",
                    "opening_date",
                    "archived_at",
                    "created_at",
                )
            },
            "current_balance": balance,
            "is_liability": is_liability,
            "balance_label": "Outstanding" if is_liability else "Balance",
        }
    )


def has_transactions(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> bool:
    return bool(
        db.scalar(
            select(
                exists().where(
                    Transaction.user_id == user_id,
                    or_(
                        Transaction.account_id == account_id,
                        Transaction.counter_account_id == account_id,
                    ),
                )
            )
        )
    )


def _name_conflict() -> ConflictError:
    return ConflictError(
        "You already have an account with this name",
        code="account_name_taken",
        details=[{"field": "name", "message": "duplicate"}],
    )


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise _name_conflict() from exc


def list_accounts(
    db: Session,
    user_id: uuid.UUID,
    params: PageParams,
    *,
    include_archived: bool,
    account_type: AccountType | None,
    sort: str | None,
) -> tuple[list[AccountOut], PageMeta]:
    repo = AccountRepository(db, user_id)
    stmt = repo.select()
    if not include_archived:
        stmt = stmt.where(Account.archived_at.is_(None))
    if account_type is not None:
        stmt = stmt.where(Account.type == account_type)
    stmt = stmt.order_by(*parse_sort(sort, SORTS, [Account.name.asc()]), Account.id)
    rows, meta = paginate(db, stmt, params)
    balances = account_balances(db, user_id, [a.id for a in rows])
    return [to_out(a, balances.get(a.id, a.opening_balance)) for a in rows], meta


def get_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> AccountOut:
    account = AccountRepository(db, user_id).get_or_404(account_id)
    return to_out(account, account_balances(db, user_id, [account.id])[account.id])


def create_account(db: Session, user_id: uuid.UUID, data: AccountCreate) -> AccountOut:
    currency = data.currency.upper()
    if currency not in SUPPORTED_CURRENCIES:
        raise ValidationAppError(
            "Only INR accounts are supported",
            code="unsupported_currency",
            details=[{"field": "currency", "message": "unsupported"}],
        )
    account = Account(
        user_id=user_id,
        name=data.name,
        type=data.type,
        institution=data.institution,
        last4=data.last4,
        currency=currency,
        opening_balance=data.opening_balance,
        opening_date=data.opening_date or today_in(),
    )
    db.add(account)
    _flush(db)
    audit.record(
        db, actor_user_id=user_id, action="create", entity_type="account", entity_id=account.id
    )
    db.commit()
    return to_out(account, account.opening_balance)


def update_account(
    db: Session, user_id: uuid.UUID, account_id: uuid.UUID, data: AccountUpdate
) -> AccountOut:
    account = AccountRepository(db, user_id).get_or_404(account_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    for required in ("name", "type", "opening_balance", "opening_date"):
        if required in changes and changes[required] is None:
            raise ValidationAppError(
                f"{required} cannot be null", details=[{"field": required, "message": "required"}]
            )
    if (
        "type" in changes
        and changes["type"] != account.type
        and has_transactions(db, user_id, account.id)
    ):
        raise ConflictError(
            "Account type cannot change once transactions exist", code="account_has_transactions"
        )
    changed = [k for k, v in changes.items() if getattr(account, k) != v]
    for key in changed:
        setattr(account, key, changes[key])
    _flush(db)
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="account",
            entity_id=account.id,
            changed_fields=changed,
        )
    db.commit()
    return get_account(db, user_id, account.id)


def archive_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> AccountOut:
    account = AccountRepository(db, user_id).get_or_404(account_id, for_update=True)
    if account.archived_at is None:
        account.archived_at = datetime.now(UTC)
        audit.record(
            db,
            actor_user_id=user_id,
            action="archive",
            entity_type="account",
            entity_id=account.id,
            changed_fields=["archived_at"],
        )
        db.commit()
    return get_account(db, user_id, account.id)


def delete_account(db: Session, user_id: uuid.UUID, account_id: uuid.UUID) -> None:
    account = AccountRepository(db, user_id).get_or_404(account_id, for_update=True)
    if has_transactions(db, user_id, account.id):
        raise ConflictError(
            "This account has transactions and cannot be deleted. Archive it instead.",
            code="account_has_transactions",
            details=[
                {
                    "suggested_action": "archive",
                    "endpoint": f"/api/v1/accounts/{account.id}/archive",
                }
            ],
        )
    db.delete(account)
    audit.record(
        db, actor_user_id=user_id, action="delete", entity_type="account", entity_id=account_id
    )
    db.commit()


def require_active_account(
    db: Session, user_id: uuid.UUID, account_id: uuid.UUID, field: str = "account_id"
) -> Account:
    """Used by other services: an owned, non-archived account or a field-level 422."""
    account = AccountRepository(db, user_id).get(account_id)
    if account is None:
        raise ValidationAppError(
            "Account not found",
            code="account_not_found",
            details=[{"field": field, "message": "not_found"}],
        )
    if account.archived_at is not None:
        raise ValidationAppError(
            "Account is archived",
            code="account_archived",
            details=[{"field": field, "message": "archived"}],
        )
    return account


def summary(db: Session, user_id: uuid.UUID) -> AccountsSummary:
    accounts = list(
        db.scalars(select(Account).where(Account.user_id == user_id, Account.archived_at.is_(None)))
    )
    balances = account_balances(db, user_id, [a.id for a in accounts])
    totals: dict[AccountType, Decimal] = dict.fromkeys(AccountType, ZERO)
    for a in accounts:
        totals[a.type] += balances.get(a.id, a.opening_balance)
    return AccountsSummary(
        liquid_funds=totals[AccountType.bank] + totals[AccountType.cash],
        bank_balance=totals[AccountType.bank],
        cash_balance=totals[AccountType.cash],
        wallet_balance=totals[AccountType.wallet],
        credit_card_outstanding=totals[AccountType.credit_card],
    )
