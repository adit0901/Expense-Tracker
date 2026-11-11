"""Receipt attachments: content-sniffed allow-list, size and count limits, owner-only access."""

from __future__ import annotations

import hashlib
import uuid
from collections.abc import Callable
from pathlib import PurePath

import filetype
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, ValidationAppError
from app.integrations.storage import StorageBackend, get_storage
from app.models.transaction import Attachment
from app.repositories.base import OwnedRepository
from app.services import audit
from app.services.transactions import TransactionRepository, on_transactions_deleted
from app.services.users.deletion import on_user_deleted

MAX_BYTES = 10 * 1024 * 1024
MAX_PER_TRANSACTION = 5
ALLOWED_MIME = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


class AttachmentRepository(OwnedRepository[Attachment]):
    model = Attachment
    entity_name = "Attachment"


def too_large() -> AppError:
    return AppError("File exceeds the 10 MB limit", code="file_too_large", status_code=413)


def sniff_mime(data: bytes) -> str | None:
    kind = filetype.guess(data[:8192])
    return kind.mime if kind is not None else None


def safe_name(name: str | None) -> str:
    base = PurePath(name or "receipt").name.replace("\x00", "")
    return (base or "receipt")[:255]


def add_attachment(
    db: Session,
    user_id: uuid.UUID,
    txn_id: uuid.UUID,
    original_name: str | None,
    data: bytes,
    storage: StorageBackend,
) -> Attachment:
    txn = TransactionRepository(db, user_id).get_or_404(txn_id, for_update=True)
    if len(data) > MAX_BYTES:
        raise too_large()
    if not data:
        raise ValidationAppError("File is empty", code="unsupported_file_type")
    mime = sniff_mime(data)
    if mime not in ALLOWED_MIME:
        raise ValidationAppError(
            "Only PDF, JPEG, PNG and WebP receipts are allowed",
            code="unsupported_file_type",
            details=[{"field": "file", "message": "unsupported_type"}],
        )
    count = (
        db.scalar(
            select(func.count())
            .select_from(Attachment)
            .where(Attachment.user_id == user_id, Attachment.transaction_id == txn.id)
        )
        or 0
    )
    if count >= MAX_PER_TRANSACTION:
        raise ConflictError(
            f"A transaction can have at most {MAX_PER_TRANSACTION} receipts",
            code="attachment_limit",
        )
    key = storage.save(data)
    att = Attachment(
        user_id=user_id,
        transaction_id=txn.id,
        storage_key=key,
        original_name=safe_name(original_name),
        mime_type=mime,
        size_bytes=len(data),
        sha256=hashlib.sha256(data).hexdigest(),
    )
    db.add(att)
    try:
        db.flush()
        audit.record(
            db, actor_user_id=user_id, action="create", entity_type="attachment", entity_id=att.id
        )
        db.commit()
    except Exception:
        db.rollback()
        storage.delete(key)
        raise
    return att


def get_attachment(db: Session, user_id: uuid.UUID, att_id: uuid.UUID) -> Attachment:
    return AttachmentRepository(db, user_id).get_or_404(att_id)


def delete_attachment(
    db: Session, user_id: uuid.UUID, att_id: uuid.UUID, storage: StorageBackend
) -> None:
    att = AttachmentRepository(db, user_id).get_or_404(att_id, for_update=True)
    key = att.storage_key
    db.delete(att)
    audit.record(
        db, actor_user_id=user_id, action="delete", entity_type="attachment", entity_id=att_id
    )
    db.commit()
    storage.delete(key)


def _keys_for(db: Session, user_id: uuid.UUID, txn_ids: list[uuid.UUID] | None) -> list[str]:
    stmt = select(Attachment.storage_key).where(Attachment.user_id == user_id)
    if txn_ids is not None:
        stmt = stmt.where(Attachment.transaction_id.in_(txn_ids))
    return list(db.scalars(stmt))


def _deleter(keys: list[str]) -> Callable[[], None] | None:
    if not keys:
        return None

    def _run() -> None:
        storage = get_storage()
        for k in keys:
            storage.delete(k)

    return _run


@on_transactions_deleted
def _remove_files_for_transactions(
    db: Session, user_id: uuid.UUID, txn_ids: list[uuid.UUID]
) -> Callable[[], None] | None:
    return _deleter(_keys_for(db, user_id, txn_ids))


@on_user_deleted
def _remove_files_for_user(db: Session, user_id: uuid.UUID) -> Callable[[], None] | None:
    return _deleter(_keys_for(db, user_id, None))
