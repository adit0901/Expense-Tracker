"""CSV import pipeline (design D10): upload -> preview -> atomic confirm -> 24 h undo."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import structlog
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationAppError
from app.models.account import Account
from app.models.category import Category
from app.models.enums import (
    AccountType,
    CategoryKind,
    ImportStatus,
    PaymentMethod,
    TransactionType,
)
from app.models.transaction import ImportBatch, Transaction
from app.repositories.base import OwnedRepository
from app.schemas.imports import ImportBatchOut, ImportRowOut
from app.schemas.transactions import TransactionCreate
from app.services import audit
from app.services import transactions as txn_service
from app.services.accounts import require_active_account
from app.services.imports.parser import (
    DATE_FORMATS,
    ColumnMapping,
    decode,
    fingerprint,
    parse_method,
    parse_row,
    read_table,
    suggest_mapping,
)
from app.services.transactions.duplicates import find_duplicates

log = structlog.get_logger("app.imports")
UNDO_WINDOW = timedelta(hours=24)
FALLBACK_CATEGORY = {CategoryKind.expense: "Others", CategoryKind.income: "Other Income"}


class ImportRepository(OwnedRepository[ImportBatch]):
    model = ImportBatch
    entity_name = "Import"


def _category_index(db: Session, user_id: uuid.UUID) -> dict[tuple[CategoryKind, str], Category]:
    cats = db.scalars(select(Category).where(Category.user_id == user_id))
    index: dict[tuple[CategoryKind, str], Category] = {}
    for c in sorted(cats, key=lambda c: c.parent_id is not None):  # top-level wins on clash
        index.setdefault((c.kind, c.name.lower()), c)
    return index


def _resolve_mapping(headers: list[str], raw: dict[str, Any] | None) -> ColumnMapping:
    candidate = raw if raw else suggest_mapping(headers)
    try:
        mapping = ColumnMapping.model_validate(candidate)
    except ValidationError as exc:
        raise ValidationAppError(
            "Column mapping is incomplete: map a date column and an amount "
            "(or debit/credit) column",
            code="invalid_mapping",
            details=[
                {
                    "field": "column_mapping",
                    "message": "incomplete",
                    "headers": headers,
                    "suggested": suggest_mapping(headers),
                }
            ],
        ) from exc
    missing = [c for c in mapping.columns() if c not in headers]
    if missing:
        raise ValidationAppError(
            "Mapped columns not found in the file: " + ", ".join(missing),
            code="invalid_mapping",
            details=[{"field": "column_mapping", "message": "unknown_column", "headers": headers}],
        )
    return mapping


def create_import(
    db: Session,
    user_id: uuid.UUID,
    *,
    file_name: str,
    data: bytes,
    account_id: uuid.UUID,
    date_format: str,
    mapping: dict[str, Any] | None,
) -> ImportBatchOut:
    account = require_active_account(db, user_id, account_id)
    if date_format not in DATE_FORMATS:
        raise ValidationAppError(
            "Unsupported date format",
            code="validation_error",
            details=[
                {"field": "date_format", "message": "unsupported", "allowed": list(DATE_FORMATS)}
            ],
        )
    text, encoding = decode(data)
    headers, records = read_table(text)
    col_map = _resolve_mapping(headers, mapping)
    cats = _category_index(db, user_id)
    existing_fps: set[str] = {
        fp
        for fp in db.scalars(
            select(Transaction.import_fingerprint).where(
                Transaction.user_id == user_id,
                Transaction.account_id == account.id,
                Transaction.import_fingerprint.is_not(None),
            )
        )
        if fp
    }
    seen_in_file: set[str] = set()
    rows: list[dict[str, Any]] = []
    for i, rec in enumerate(records, start=2):  # row 1 is the header
        rows.append(
            _preview_row(
                db, user_id, account, i, rec, col_map, date_format, cats, existing_fps, seen_in_file
            )
        )
    batch = ImportBatch(
        user_id=user_id,
        account_id=account.id,
        file_name=file_name[:255],
        encoding=encoding,
        date_format=date_format,
        column_mapping={"mapping": col_map.model_dump(exclude_none=True), "headers": headers},
        row_count=len(rows),
        preview=rows,
    )
    db.add(batch)
    db.commit()
    return to_out(batch)


def _preview_row(
    db: Session,
    user_id: uuid.UUID,
    account: Account,
    n: int,
    rec: dict[str, str],
    m: ColumnMapping,
    date_format: str,
    cats: dict[tuple[CategoryKind, str], Category],
    existing_fps: set[str],
    seen: set[str],
) -> dict[str, Any]:
    p = parse_row(n, rec, m, date_format)
    warnings: list[str] = []
    category: Category | None = None
    method: PaymentMethod | None = None
    if p.type is not None:
        kind = CategoryKind.income if p.type == TransactionType.income else CategoryKind.expense
        if p.category:
            category = cats.get((kind, p.category.lower()))
        if category is None:
            category = cats.get((kind, FALLBACK_CATEGORY[kind].lower()))
            if p.category:
                warnings.append(
                    f"unknown category '{p.category}', using '{FALLBACK_CATEGORY[kind]}'"
                )
        if category is None:
            p.errors.append("no matching category")
        if p.type == TransactionType.expense:
            method = parse_method(p.payment_method_raw)
            if account.type == AccountType.credit_card:
                method = PaymentMethod.credit_card
            elif method in (None, PaymentMethod.credit_card):
                if p.payment_method_raw:
                    warnings.append(
                        f"payment method '{p.payment_method_raw}' not usable for "
                        "this account, using 'other'"
                    )
                method = PaymentMethod.other
    duplicate_of: list[str] = []
    fp: str | None = None
    if not p.errors and p.txn_date and p.amount is not None and p.type is not None:
        fp = fingerprint(p.txn_date, p.amount, p.description)
        if fp in existing_fps or fp in seen:
            duplicate_of.append("previous import" if fp in existing_fps else "earlier row")
        seen.add(fp)
        for c in find_duplicates(
            db,
            user_id,
            account_id=account.id,
            txn_type=p.type,
            amount=p.amount,
            txn_date=p.txn_date,
            payee=p.payee,
            description=p.description,
        ):
            duplicate_of.append(str(c.id))
    valid = not p.errors
    return {
        "row": n,
        "date": p.txn_date.isoformat() if p.txn_date else None,
        "type": p.type.value if p.type else None,
        "amount": f"{p.amount:.2f}" if p.amount is not None else None,
        "description": p.description,
        "payee": p.payee,
        "notes": p.notes,
        "category_id": str(category.id) if category else None,
        "category_name": category.name if category else None,
        "payment_method": method.value if method else None,
        "errors": p.errors,
        "warnings": warnings,
        "duplicate": bool(duplicate_of),
        "duplicate_of": sorted(set(duplicate_of)),
        "selected": valid and not duplicate_of,
        "fingerprint": fp,
    }


def to_out(b: ImportBatch) -> ImportBatchOut:
    rows = b.preview or []
    undo_until = (
        b.confirmed_at + UNDO_WINDOW
        if b.confirmed_at and b.status == ImportStatus.confirmed
        else None
    )
    return ImportBatchOut(
        id=b.id,
        status=b.status.value,
        file_name=b.file_name,
        account_id=b.account_id,
        encoding=b.encoding,
        date_format=b.date_format,
        headers=list(b.column_mapping.get("headers", [])),
        column_mapping=dict(b.column_mapping.get("mapping", {})),
        row_count=b.row_count,
        valid_count=sum(1 for r in rows if not r["errors"]),
        invalid_count=sum(1 for r in rows if r["errors"]),
        duplicate_count=sum(1 for r in rows if r["duplicate"]),
        imported_count=b.imported_count,
        rows=[
            ImportRowOut.model_validate(
                {k: v for k, v in r.items() if k not in ("fingerprint", "notes")}
            )
            for r in rows
        ],
        created_at=b.created_at,
        confirmed_at=b.confirmed_at,
        undone_at=b.undone_at,
        undo_available_until=undo_until,
    )


def get_import(db: Session, user_id: uuid.UUID, batch_id: uuid.UUID) -> ImportBatchOut:
    return to_out(ImportRepository(db, user_id).get_or_404(batch_id))


def confirm_import(
    db: Session, user_id: uuid.UUID, batch_id: uuid.UUID, selected_rows: list[int] | None
) -> ImportBatchOut:
    batch = ImportRepository(db, user_id).get_or_404(batch_id, for_update=True)
    if batch.status != ImportStatus.preview:
        raise ConflictError(
            "This import has already been confirmed or undone", code="import_not_pending"
        )
    rows = {r["row"]: r for r in batch.preview}
    chosen = (
        [r for r in batch.preview if r["selected"]]
        if selected_rows is None
        else [rows[n] for n in selected_rows if n in rows]
    )
    if selected_rows is not None and len(chosen) != len(set(selected_rows)):
        raise ValidationAppError(
            "Unknown row numbers selected",
            code="validation_error",
            details=[{"field": "selected_rows", "message": "unknown_rows"}],
        )
    invalid = [r["row"] for r in chosen if r["errors"]]
    if invalid:
        raise ValidationAppError(
            "Rows with errors cannot be imported",
            code="validation_error",
            details=[{"field": "selected_rows", "message": "invalid_rows", "rows": invalid}],
        )
    if not chosen:
        raise ValidationAppError(
            "Select at least one row to import",
            code="validation_error",
            details=[{"field": "selected_rows", "message": "empty"}],
        )
    try:
        for r in chosen:
            data = TransactionCreate(
                type=TransactionType(r["type"]),
                account_id=batch.account_id,
                amount=Decimal(r["amount"]),
                txn_date=r["date"],
                category_id=uuid.UUID(r["category_id"]),
                payment_method=PaymentMethod(r["payment_method"]) if r["payment_method"] else None,
                payee=r["payee"],
                description=r["description"],
                notes=r.get("notes"),
                confirm_duplicate=True,
            )
            txn_service.build_transaction(
                db, user_id, data, import_batch_id=batch.id, import_fingerprint=r["fingerprint"]
            )
        batch.status = ImportStatus.confirmed
        batch.imported_count = len(chosen)
        batch.confirmed_at = datetime.now(UTC)
        audit.record(
            db,
            actor_user_id=user_id,
            action="import",
            entity_type="import_batch",
            entity_id=batch.id,
        )
        db.commit()
    except Exception:
        db.rollback()  # all-or-nothing
        log.warning("import_confirm_failed", batch_id=str(batch_id))
        raise
    return to_out(batch)


def undo_import(db: Session, user_id: uuid.UUID, batch_id: uuid.UUID) -> ImportBatchOut:
    batch = ImportRepository(db, user_id).get_or_404(batch_id, for_update=True)
    if batch.status != ImportStatus.confirmed or batch.confirmed_at is None:
        raise ConflictError("Only confirmed imports can be undone", code="import_not_confirmed")
    if datetime.now(UTC) - batch.confirmed_at > UNDO_WINDOW:
        raise ConflictError(
            "Imports can only be undone within 24 hours", code="import_undo_expired"
        )
    txns = list(
        db.scalars(
            select(Transaction).where(
                Transaction.user_id == user_id, Transaction.import_batch_id == batch.id
            )
        )
    )
    txn_service.delete_transactions(db, user_id, txns)
    batch.status = ImportStatus.undone
    batch.undone_at = datetime.now(UTC)
    audit.record(
        db,
        actor_user_id=user_id,
        action="undo_import",
        entity_type="import_batch",
        entity_id=batch.id,
    )
    db.commit()
    txn_service.run_post_commit(db)
    return to_out(batch)
