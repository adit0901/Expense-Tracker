import uuid

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.services import audit


def test_audit_entry_created(db: Session) -> None:
    actor, entity = uuid.uuid4(), uuid.uuid4()
    audit.record(
        db,
        actor_user_id=actor,
        action="update",
        entity_type="transaction",
        entity_id=entity,
        changed_fields=["amount"],
    )
    db.commit()
    row = db.scalars(select(AuditLog).where(AuditLog.entity_id == entity)).one()
    assert row.action == "update" and row.changed_fields == ["amount"]
    assert row.actor_user_id == actor and row.occurred_at is not None


@pytest.mark.parametrize(
    "stmt",
    ["UPDATE audit_log SET action = 'x'", "DELETE FROM audit_log", "TRUNCATE audit_log"],
)
def test_audit_rows_cannot_be_modified_by_app_role(db: Session, stmt: str) -> None:
    audit.record(
        db,
        actor_user_id=uuid.uuid4(),
        action="create",
        entity_type="account",
        entity_id=uuid.uuid4(),
    )
    db.commit()
    with pytest.raises(ProgrammingError, match="permission denied"), db.begin_nested():
        db.execute(text(stmt))


def test_anonymize_function_available_to_app_role(db: Session) -> None:
    actor = uuid.uuid4()
    audit.record(
        db, actor_user_id=actor, action="create", entity_type="account", entity_id=uuid.uuid4()
    )
    db.commit()
    n = db.scalar(text("SELECT anonymize_audit_actor(:u)"), {"u": actor})
    assert n == 1
    assert db.scalar(select(AuditLog.id).where(AuditLog.actor_user_id == actor)) is None
