"""Transactions: validation, CRUD, search, duplicates, salary breakdowns."""

from __future__ import annotations

import uuid
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.core.money import ZERO
from app.core.pagination import PageParams, build_meta, parse_sort
from app.models.account import Account
from app.models.category import Category
from app.models.enums import (
    AccountType,
    PaymentMethod,
    SalaryComponentKind,
    TransactionType,
)
from app.models.income_source import IncomeSource
from app.models.transaction import Attachment, SalaryComponent, Transaction
from app.repositories.base import OwnedRepository
from app.schemas.transactions import (
    AttachmentOut,
    DeductionIn,
    DuplicateCandidate,
    DuplicateCheckOut,
    SalaryBreakdownIn,
    SalaryBreakdownOut,
    SalaryComponentOut,
    TransactionCreate,
    TransactionFilters,
    TransactionOut,
    TransactionPageMeta,
    TransactionTotals,
    TransactionUpdate,
)
from app.services import audit
from app.services.accounts import AccountRepository, require_active_account
from app.services.categories import require_category_for
from app.services.transactions.duplicates import find_duplicates
from app.services.transactions.filters import DEFAULT_SORT, SORTS, build_conditions

EDITABLE_FIELDS = (
    "type",
    "account_id",
    "counter_account_id",
    "category_id",
    "income_source_id",
    "amount",
    "txn_date",
    "payment_method",
    "payee",
    "description",
    "notes",
    "tags",
    "refund_of_id",
)


class TransactionRepository(OwnedRepository[Transaction]):
    model = Transaction
    entity_name = "Transaction"


def _err(message: str, code: str, field: str, detail: str = "invalid") -> ValidationAppError:
    return ValidationAppError(message, code=code, details=[{"field": field, "message": detail}])


# ---- validation ----------------------------------------------------------------------------


def validate_salary_breakdown(breakdown: SalaryBreakdownIn, net_amount: Decimal) -> None:
    """Net salary = gross - total deductions, and must equal the credited amount."""
    total_deductions = sum((d.amount for d in breakdown.deductions), ZERO)
    net = breakdown.gross - total_deductions
    if net != net_amount:
        raise ValidationAppError(
            f"Gross minus deductions ({net}) does not equal the credited amount ({net_amount})",
            code="salary_breakdown_mismatch",
            details=[
                {
                    "field": "salary_breakdown",
                    "message": "mismatch",
                    "expected_net": f"{net:.2f}",
                    "amount": f"{net_amount:.2f}",
                }
            ],
        )


def _validate(
    db: Session,
    user_id: uuid.UUID,
    s: dict[str, Any],
    *,
    account_changed: bool,
    counter_changed: bool,
) -> None:
    t: TransactionType = s["type"]
    if t == TransactionType.loan_payment and s.get("loan_id") is None:
        raise _err(
            "loan_payment transactions cannot be created directly",
            "validation_error",
            "type",
            "not_allowed",
        )
    account = (
        require_active_account(db, user_id, s["account_id"])
        if account_changed
        else AccountRepository(db, user_id).get_or_404(s["account_id"])
    )

    if t == TransactionType.transfer:
        if s.get("counter_account_id") is None:
            raise _err(
                "A transfer needs a destination account",
                "validation_error",
                "counter_account_id",
                "required",
            )
        if s["counter_account_id"] == s["account_id"]:
            raise _err(
                "Source and destination accounts must differ",
                "same_account_transfer",
                "counter_account_id",
                "same_as_source",
            )
        if counter_changed:
            require_active_account(db, user_id, s["counter_account_id"], "counter_account_id")
        else:
            AccountRepository(db, user_id).get_or_404(s["counter_account_id"])
        if s.get("category_id") is not None:
            raise _err(
                "Transfers do not have a category", "validation_error", "category_id", "not_allowed"
            )
    else:
        if s.get("counter_account_id") is not None:
            raise _err(
                "Only transfers have a destination account",
                "validation_error",
                "counter_account_id",
                "not_allowed",
            )
        if s.get("category_id") is None:
            raise _err("Category is required", "validation_error", "category_id", "required")
        require_category_for(db, user_id, s["category_id"], t)

    if t == TransactionType.expense and s.get("payment_method") is None:
        raise _err(
            "Payment method is required for expenses",
            "validation_error",
            "payment_method",
            "required",
        )
    if t == TransactionType.income and s.get("payment_method") is not None:
        raise _err(
            "Income does not take a payment method",
            "validation_error",
            "payment_method",
            "not_allowed",
        )
    if (
        s.get("payment_method") == PaymentMethod.credit_card
        and account.type != AccountType.credit_card
    ):
        raise _err(
            "Credit card payments must use a credit card account",
            "payment_method_account_mismatch",
            "payment_method",
            "account_mismatch",
        )

    if s.get("income_source_id") is not None:
        if t != TransactionType.income:
            raise _err(
                "Only income can reference an income source",
                "validation_error",
                "income_source_id",
                "not_allowed",
            )
        src = db.scalar(
            select(IncomeSource).where(
                IncomeSource.user_id == user_id, IncomeSource.id == s["income_source_id"]
            )
        )
        if src is None:
            raise _err(
                "Income source not found",
                "income_source_not_found",
                "income_source_id",
                "not_found",
            )

    if s.get("refund_of_id") is not None:
        if t != TransactionType.refund:
            raise _err(
                "Only refunds can reference an original expense",
                "validation_error",
                "refund_of_id",
                "not_allowed",
            )
        original = TransactionRepository(db, user_id).get(s["refund_of_id"])
        if original is None or original.type != TransactionType.expense:
            raise _err(
                "Original expense not found",
                "refund_original_not_found",
                "refund_of_id",
                "not_found",
            )

    breakdown = s.get("salary_breakdown")
    if breakdown is not None:
        if t != TransactionType.income:
            raise _err(
                "Only income can have a salary breakdown",
                "validation_error",
                "salary_breakdown",
                "not_allowed",
            )
        validate_salary_breakdown(breakdown, s["amount"])


# ---- presentation --------------------------------------------------------------------------


@dataclass
class _Lookup:
    accounts: dict[uuid.UUID, Account]
    categories: dict[uuid.UUID, Category]
    attachments: dict[uuid.UUID, list[Attachment]]


def _lookup(db: Session, user_id: uuid.UUID, txns: Iterable[Transaction]) -> _Lookup:
    txns = list(txns)
    acct_ids = {t.account_id for t in txns} | {
        t.counter_account_id for t in txns if t.counter_account_id
    }
    cat_ids = {t.category_id for t in txns if t.category_id}
    accounts = (
        {
            a.id: a
            for a in db.scalars(
                select(Account).where(Account.user_id == user_id, Account.id.in_(acct_ids))
            )
        }
        if acct_ids
        else {}
    )
    categories: dict[uuid.UUID, Category] = {}
    if cat_ids:
        cats = list(
            db.scalars(
                select(Category).where(Category.user_id == user_id, Category.id.in_(cat_ids))
            )
        )
        parent_ids = {c.parent_id for c in cats if c.parent_id} - cat_ids
        if parent_ids:
            cats += list(db.scalars(select(Category).where(Category.id.in_(parent_ids))))
        categories = {c.id: c for c in cats}
    attachments: dict[uuid.UUID, list[Attachment]] = {}
    if txns:
        for a in db.scalars(
            select(Attachment)
            .where(
                Attachment.user_id == user_id, Attachment.transaction_id.in_([t.id for t in txns])
            )
            .order_by(Attachment.created_at)
        ):
            attachments.setdefault(a.transaction_id, []).append(a)
    return _Lookup(accounts, categories, attachments)


def _breakdown_out(components: list[SalaryComponent]) -> SalaryBreakdownOut | None:
    gross = next((c for c in components if c.kind == SalaryComponentKind.gross), None)
    if gross is None:
        return None
    deductions = [c for c in components if c.kind == SalaryComponentKind.deduction]
    total = sum((d.amount for d in deductions), ZERO)
    return SalaryBreakdownOut(
        gross=gross.amount,
        deductions=[
            SalaryComponentOut(kind=d.kind.value, name=d.name, amount=d.amount) for d in deductions
        ],
        total_deductions=total,
        net=gross.amount - total,
    )


def to_out(t: Transaction, lk: _Lookup) -> TransactionOut:
    cat = lk.categories.get(t.category_id) if t.category_id else None
    parent = lk.categories.get(cat.parent_id) if cat and cat.parent_id else None
    acct = lk.accounts.get(t.account_id)
    counter = lk.accounts.get(t.counter_account_id) if t.counter_account_id else None
    return TransactionOut(
        id=t.id,
        type=t.type,
        status=t.status.value,
        account_id=t.account_id,
        account_name=acct.name if acct else None,
        counter_account_id=t.counter_account_id,
        counter_account_name=counter.name if counter else None,
        category_id=t.category_id,
        category_name=cat.name if cat else None,
        parent_category_id=parent.id if parent else None,
        parent_category_name=parent.name if parent else None,
        income_source_id=t.income_source_id,
        amount=t.amount,
        currency=t.currency,
        txn_date=t.txn_date,
        payment_method=t.payment_method,
        payee=t.payee,
        description=t.description,
        notes=t.notes,
        tags=list(t.tags or []),
        refund_of_id=t.refund_of_id,
        import_batch_id=t.import_batch_id,
        salary_breakdown=_breakdown_out(list(t.salary_components)),
        attachments=[
            AttachmentOut(
                id=a.id,
                original_name=a.original_name,
                mime_type=a.mime_type,
                size_bytes=a.size_bytes,
                created_at=a.created_at,
            )
            for a in lk.attachments.get(t.id, [])
        ],
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def present(db: Session, user_id: uuid.UUID, t: Transaction) -> TransactionOut:
    return to_out(t, _lookup(db, user_id, [t]))


# ---- duplicates ----------------------------------------------------------------------------


def duplicate_check(
    db: Session, user_id: uuid.UUID, data: TransactionCreate, exclude_id: uuid.UUID | None = None
) -> DuplicateCheckOut:
    AccountRepository(db, user_id).get_or_404(data.account_id)
    found = find_duplicates(
        db,
        user_id,
        account_id=data.account_id,
        txn_type=data.type,
        amount=data.amount,
        txn_date=data.txn_date,
        payee=data.payee,
        description=data.description,
        exclude_id=exclude_id,
    )
    return DuplicateCheckOut(
        is_possible_duplicate=bool(found),
        candidates=[
            DuplicateCandidate(
                id=c.id,
                txn_date=c.txn_date,
                amount=c.amount,
                type=c.type,
                payee=c.payee,
                description=c.description,
            )
            for c in found
        ],
    )


def _raise_if_duplicate(db: Session, user_id: uuid.UUID, data: TransactionCreate) -> None:
    if data.confirm_duplicate:
        return
    check = duplicate_check(db, user_id, data)
    if check.is_possible_duplicate:
        raise ConflictError(
            "This looks like a possible duplicate. Confirm to save it anyway.",
            code="possible_duplicate",
            details=[{"candidate": c.model_dump(mode="json")} for c in check.candidates],
        )


# ---- writes --------------------------------------------------------------------------------


def _set_breakdown(t: Transaction, user_id: uuid.UUID, b: SalaryBreakdownIn | None) -> None:
    t.salary_components.clear()
    if b is None:
        return
    t.salary_components.append(
        SalaryComponent(
            user_id=user_id,
            kind=SalaryComponentKind.gross,
            name="Gross salary",
            amount=b.gross,
            position=0,
        )
    )
    for i, d in enumerate(b.deductions, start=1):
        t.salary_components.append(
            SalaryComponent(
                user_id=user_id,
                kind=SalaryComponentKind.deduction,
                name=d.name.strip(),
                amount=d.amount,
                position=i,
            )
        )


def _state_of(data: TransactionCreate) -> dict[str, Any]:
    state = data.model_dump()
    state["salary_breakdown"] = data.salary_breakdown  # keep the model, not a dict
    return state


def build_transaction(
    db: Session,
    user_id: uuid.UUID,
    data: TransactionCreate,
    *,
    import_batch_id: uuid.UUID | None = None,
    import_fingerprint: str | None = None,
) -> Transaction:
    """Validate and add (flush) a transaction without committing. Used by create and imports."""
    state = _state_of(data)
    _validate(db, user_id, state, account_changed=True, counter_changed=True)
    t = Transaction(
        user_id=user_id,
        import_batch_id=import_batch_id,
        import_fingerprint=import_fingerprint,
        **{k: state[k] for k in EDITABLE_FIELDS},
    )
    t.tags = state["tags"] or []
    _set_breakdown(t, user_id, data.salary_breakdown)
    db.add(t)
    db.flush()
    audit.record(
        db, actor_user_id=user_id, action="create", entity_type="transaction", entity_id=t.id
    )
    return t


def create_transaction(db: Session, user_id: uuid.UUID, data: TransactionCreate) -> TransactionOut:
    _validate(db, user_id, _state_of(data), account_changed=True, counter_changed=True)
    _raise_if_duplicate(db, user_id, data)
    t = build_transaction(db, user_id, data)
    from app.services.budgets import evaluate_budget_alerts
    from app.services.net_worth import mark_snapshots_stale

    evaluate_budget_alerts(db, user_id, date(t.txn_date.year, t.txn_date.month, 1))
    mark_snapshots_stale(db, user_id, t.txn_date)
    db.commit()
    return present(db, user_id, t)


def get_transaction(db: Session, user_id: uuid.UUID, txn_id: uuid.UUID) -> TransactionOut:
    return present(db, user_id, TransactionRepository(db, user_id).get_or_404(txn_id))


def update_transaction(
    db: Session, user_id: uuid.UUID, txn_id: uuid.UUID, data: TransactionUpdate
) -> TransactionOut:
    t = TransactionRepository(db, user_id).get_or_404(txn_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    changes.pop("confirm_duplicate", None)
    for required in ("type", "account_id", "amount", "txn_date"):
        if required in changes and changes[required] is None:
            raise _err(f"{required} cannot be null", "validation_error", required, "required")
    state = {k: getattr(t, k) for k in EDITABLE_FIELDS}
    state.update({k: v for k, v in changes.items() if k != "salary_breakdown"})
    if "salary_breakdown" in changes:
        state["salary_breakdown"] = data.salary_breakdown
    else:
        existing = _breakdown_out(list(t.salary_components))
        state["salary_breakdown"] = (
            SalaryBreakdownIn(
                gross=existing.gross,
                deductions=[DeductionIn(name=d.name, amount=d.amount) for d in existing.deductions],
            )
            if existing
            else None
        )
        if state["salary_breakdown"] is not None and state["type"] != TransactionType.income:
            state["salary_breakdown"] = None
            changes["salary_breakdown"] = None
    _validate(
        db,
        user_id,
        state,
        account_changed=state["account_id"] != t.account_id,
        counter_changed=state["counter_account_id"] != t.counter_account_id,
    )
    changed = [k for k in EDITABLE_FIELDS if k in changes and getattr(t, k) != state[k]]
    for k in changed:
        setattr(t, k, state[k] if k != "tags" else (state[k] or []))
    if "salary_breakdown" in changes:
        _set_breakdown(t, user_id, state["salary_breakdown"])
        changed.append("salary_breakdown")
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="transaction",
            entity_id=t.id,
            changed_fields=changed,
        )
    from app.services.budgets import evaluate_budget_alerts
    from app.services.net_worth import mark_snapshots_stale

    evaluate_budget_alerts(db, user_id, date(t.txn_date.year, t.txn_date.month, 1))
    mark_snapshots_stale(db, user_id, t.txn_date)
    db.commit()
    db.refresh(t)
    return present(db, user_id, t)


TransactionDeletionHook = Callable[[Session, uuid.UUID, list[uuid.UUID]], Callable[[], None] | None]
_DELETE_HOOKS: list[TransactionDeletionHook] = []


def on_transactions_deleted(hook: TransactionDeletionHook) -> TransactionDeletionHook:
    if hook not in _DELETE_HOOKS:
        _DELETE_HOOKS.append(hook)
    return hook


def delete_transactions(db: Session, user_id: uuid.UUID, txns: list[Transaction]) -> None:
    """Delete transactions (caller commits); runs hooks e.g. to remove receipt files."""
    ids = [t.id for t in txns]
    post: list[Callable[[], None]] = []
    for hook in _DELETE_HOOKS:
        action = hook(db, user_id, ids)
        if action is not None:
            post.append(action)
    for t in txns:
        audit.record(
            db, actor_user_id=user_id, action="delete", entity_type="transaction", entity_id=t.id
        )
        db.delete(t)
    db.flush()
    from app.services.budgets import evaluate_budget_alerts
    from app.services.net_worth import mark_snapshots_stale

    months = {date(t.txn_date.year, t.txn_date.month, 1) for t in txns}
    for m in months:
        evaluate_budget_alerts(db, user_id, m)
    if txns:
        min_date = min(t.txn_date for t in txns)
        mark_snapshots_stale(db, user_id, min_date)
    db.info.setdefault("post_commit", []).extend(post)


def run_post_commit(db: Session) -> None:
    for action in db.info.pop("post_commit", []):
        action()


def delete_transaction(db: Session, user_id: uuid.UUID, txn_id: uuid.UUID) -> None:
    t = TransactionRepository(db, user_id).get_or_404(txn_id, for_update=True)
    delete_transactions(db, user_id, [t])
    db.commit()
    run_post_commit(db)


# ---- queries -------------------------------------------------------------------------------


def _totals(db: Session, conds: list[Any]) -> TransactionTotals:
    rows = db.execute(
        select(Transaction.type, func.count(), func.sum(Transaction.amount))
        .where(*conds)
        .group_by(Transaction.type)
    ).all()
    by_type = {r[0]: (int(r[1]), Decimal(r[2] or 0)) for r in rows}

    def s(t: TransactionType) -> Decimal:
        return by_type.get(t, (0, ZERO))[1]

    return TransactionTotals(
        count=sum(c for c, _ in by_type.values()),
        total_amount=sum((v for _, v in by_type.values()), ZERO),
        income=s(TransactionType.income),
        expense=s(TransactionType.expense),
        refund=s(TransactionType.refund),
        transfer=s(TransactionType.transfer),
        net_expense=s(TransactionType.expense) - s(TransactionType.refund),
    )


def filtered_query(
    db: Session, user_id: uuid.UUID, filters: TransactionFilters, sort: str | None
) -> tuple[Any, list[Any]]:
    conds = build_conditions(db, user_id, filters)
    order = parse_sort(sort, SORTS, DEFAULT_SORT)
    return select(Transaction).where(*conds).order_by(*order, Transaction.id), conds


def list_transactions(
    db: Session,
    user_id: uuid.UUID,
    filters: TransactionFilters,
    params: PageParams,
    sort: str | None,
) -> tuple[list[TransactionOut], TransactionPageMeta]:
    stmt, conds = filtered_query(db, user_id, filters, sort)
    rows = list(db.scalars(stmt.limit(params.page_size).offset(params.offset)))
    totals = _totals(db, conds)
    base = build_meta(params, totals.count)
    lk = _lookup(db, user_id, rows)
    return ([to_out(t, lk) for t in rows], TransactionPageMeta(**base.model_dump(), totals=totals))


def iter_filtered(
    db: Session, user_id: uuid.UUID, filters: TransactionFilters, sort: str | None
) -> tuple[list[Transaction], _Lookup]:
    stmt, _ = filtered_query(db, user_id, filters, sort)
    rows = list(db.scalars(stmt))
    return rows, _lookup(db, user_id, rows)


def get_owned_or_404(db: Session, user_id: uuid.UUID, txn_id: uuid.UUID) -> Transaction:
    t = TransactionRepository(db, user_id).get(txn_id)
    if t is None:
        raise NotFoundError("Transaction")
    return t
