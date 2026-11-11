"""Income sources (salary, freelance, ...) with default category/account."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.errors import ValidationAppError
from app.core.pagination import PageParams, paginate, parse_sort
from app.core.responses import PageMeta
from app.models.enums import TransactionType
from app.models.income_source import IncomeSource
from app.repositories.base import OwnedRepository
from app.schemas.income import IncomeSourceCreate, IncomeSourceUpdate
from app.services import audit
from app.services.accounts import AccountRepository
from app.services.categories import require_category_for

SORTS = {"name": IncomeSource.name, "created_at": IncomeSource.created_at}


class IncomeSourceRepository(OwnedRepository[IncomeSource]):
    model = IncomeSource
    entity_name = "Income source"


def _check_defaults(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID | None, account_id: uuid.UUID | None
) -> None:
    if category_id is not None:
        require_category_for(db, user_id, category_id, TransactionType.income)
    if account_id is not None and AccountRepository(db, user_id).get(account_id) is None:
        raise ValidationAppError(
            "Account not found",
            code="account_not_found",
            details=[{"field": "default_account_id", "message": "not_found"}],
        )


def list_sources(
    db: Session, user_id: uuid.UUID, params: PageParams, *, include_inactive: bool, sort: str | None
) -> tuple[list[IncomeSource], PageMeta]:
    stmt = IncomeSourceRepository(db, user_id).select()
    if not include_inactive:
        stmt = stmt.where(IncomeSource.is_active.is_(True))
    stmt = stmt.order_by(*parse_sort(sort, SORTS, [IncomeSource.name.asc()]), IncomeSource.id)
    return paginate(db, stmt, params)


def create_source(db: Session, user_id: uuid.UUID, data: IncomeSourceCreate) -> IncomeSource:
    _check_defaults(db, user_id, data.default_category_id, data.default_account_id)
    src = IncomeSource(
        user_id=user_id,
        name=data.name.strip(),
        type=data.type,
        default_category_id=data.default_category_id,
        default_account_id=data.default_account_id,
    )
    db.add(src)
    db.flush()
    audit.record(
        db, actor_user_id=user_id, action="create", entity_type="income_source", entity_id=src.id
    )
    db.commit()
    return src


def update_source(
    db: Session, user_id: uuid.UUID, source_id: uuid.UUID, data: IncomeSourceUpdate
) -> IncomeSource:
    src = IncomeSourceRepository(db, user_id).get_or_404(source_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    for required in ("name", "type", "is_active"):
        if required in changes and changes[required] is None:
            changes.pop(required)
    _check_defaults(
        db, user_id, changes.get("default_category_id"), changes.get("default_account_id")
    )
    changed = [k for k, v in changes.items() if getattr(src, k) != v]
    for k in changed:
        setattr(src, k, changes[k].strip() if k == "name" else changes[k])
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="income_source",
            entity_id=src.id,
            changed_fields=changed,
        )
    db.commit()
    return src
