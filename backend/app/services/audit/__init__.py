"""Audit service: the only write path to audit_log is `record` (append-only)."""

from __future__ import annotations

import uuid
from collections.abc import Iterable
from typing import Literal

from sqlalchemy.orm import Session

from app.core.request_context import get_request_id
from app.models.audit import AuditLog

AuditAction = Literal["create", "update", "delete", "archive", "unarchive", "import", "undo_import"]


def record(
    db: Session,
    *,
    actor_user_id: uuid.UUID | None,
    action: AuditAction,
    entity_type: str,
    entity_id: uuid.UUID | None,
    changed_fields: Iterable[str] = (),
) -> AuditLog:
    """Add an audit entry to the current DB transaction (committed with the change itself)."""
    entry = AuditLog(
        actor_user_id=actor_user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        changed_fields=sorted(set(changed_fields)),
        request_id=get_request_id(),
    )
    db.add(entry)
    return entry
