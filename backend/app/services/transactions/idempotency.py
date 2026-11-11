"""Idempotency-Key support for POST endpoints (safe client retries)."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import ValidationAppError
from app.models.transaction import IdempotencyKey

RETENTION = timedelta(hours=24)


def request_hash(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, default=str, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()


def lookup(
    db: Session, user_id: uuid.UUID, key: str, endpoint: str, body_hash: str
) -> IdempotencyKey | None:
    row = db.scalar(
        select(IdempotencyKey).where(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
    )
    if row is None:
        return None
    if row.created_at < datetime.now(UTC) - RETENTION:
        db.delete(row)
        db.commit()
        return None
    if row.endpoint != endpoint or row.request_hash != body_hash:
        raise ValidationAppError(
            "This Idempotency-Key was already used with a different request",
            code="idempotency_key_reused",
            details=[{"field": "Idempotency-Key", "message": "reused"}],
        )
    return row


def store(
    db: Session,
    user_id: uuid.UUID,
    key: str,
    endpoint: str,
    body_hash: str,
    status: int,
    body: dict[str, Any],
) -> None:
    db.execute(
        delete(IdempotencyKey).where(IdempotencyKey.user_id == user_id, IdempotencyKey.key == key)
    )
    db.add(
        IdempotencyKey(
            user_id=user_id,
            key=key,
            endpoint=endpoint,
            request_hash=body_hash,
            response_status=status,
            response_body=body,
            created_at=datetime.now(UTC),
        )
    )
    db.commit()
