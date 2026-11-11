"""Transaction categories: defaults, custom categories/subcategories, safe deletion."""

from __future__ import annotations

import uuid

from sqlalchemy import exists, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, ValidationAppError
from app.core.pagination import PageParams, paginate, parse_sort
from app.core.responses import PageMeta
from app.models.category import Category
from app.models.enums import CategoryKind, TransactionType
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.base import OwnedRepository
from app.schemas.categories import (
    CategoryCreate,
    CategoryDeleteResult,
    CategoryUpdate,
)
from app.services import audit
from app.services.categories.defaults import DEFAULT_CATEGORIES
from app.services.users.registration import on_user_registered

SORTS = {"name": Category.name, "kind": Category.kind, "created_at": Category.created_at}

# Which category kind each transaction type must use.
KIND_FOR_TXN_TYPE: dict[TransactionType, CategoryKind] = {
    TransactionType.income: CategoryKind.income,
    TransactionType.expense: CategoryKind.expense,
    TransactionType.refund: CategoryKind.expense,
}


class CategoryRepository(OwnedRepository[Category]):
    model = Category
    entity_name = "Category"


@on_user_registered
def seed_default_categories(db: Session, user: User) -> None:
    for d in DEFAULT_CATEGORIES:
        db.add(
            Category(
                user_id=user.id,
                kind=d.kind,
                name=d.name,
                color=d.color,
                icon=d.icon,
                is_essential=d.is_essential,
                is_system=d.is_system,
            )
        )
    db.flush()


def _conflict() -> ConflictError:
    return ConflictError(
        "A category with this name already exists here",
        code="category_name_taken",
        details=[{"field": "name", "message": "duplicate"}],
    )


def _flush(db: Session) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if "uq_categories" in str(exc.orig):
            raise _conflict() from exc
        raise ValidationAppError(
            "Invalid category hierarchy", code="category_depth_exceeded"
        ) from exc


def list_categories(
    db: Session,
    user_id: uuid.UUID,
    params: PageParams,
    *,
    kind: CategoryKind | None,
    parent_id: uuid.UUID | None,
    top_level_only: bool,
    sort: str | None,
) -> tuple[list[Category], PageMeta]:
    stmt = CategoryRepository(db, user_id).select()
    if kind is not None:
        stmt = stmt.where(Category.kind == kind)
    if parent_id is not None:
        stmt = stmt.where(Category.parent_id == parent_id)
    if top_level_only:
        stmt = stmt.where(Category.parent_id.is_(None))
    stmt = stmt.order_by(
        *parse_sort(sort, SORTS, [Category.kind.asc(), Category.name.asc()]), Category.id
    )
    return paginate(db, stmt, params)


def create_category(db: Session, user_id: uuid.UUID, data: CategoryCreate) -> Category:
    if data.parent_id is not None:
        parent = CategoryRepository(db, user_id).get(data.parent_id)
        if parent is None:
            raise ValidationAppError(
                "Parent category not found",
                code="category_not_found",
                details=[{"field": "parent_id", "message": "not_found"}],
            )
        if parent.parent_id is not None:
            raise ValidationAppError(
                "Subcategories can only be one level deep",
                code="category_depth_exceeded",
                details=[{"field": "parent_id", "message": "depth_exceeded"}],
            )
        if parent.kind != data.kind:
            raise ValidationAppError(
                "Subcategory kind must match its parent",
                code="category_kind_mismatch",
                details=[{"field": "kind", "message": "mismatch"}],
            )
    category = Category(
        user_id=user_id,
        kind=data.kind,
        name=data.name,
        parent_id=data.parent_id,
        color=data.color,
        icon=data.icon,
        is_essential=data.is_essential and data.kind == CategoryKind.expense,
    )
    db.add(category)
    _flush(db)
    audit.record(
        db, actor_user_id=user_id, action="create", entity_type="category", entity_id=category.id
    )
    db.commit()
    return category


def update_category(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID, data: CategoryUpdate
) -> Category:
    category = CategoryRepository(db, user_id).get_or_404(category_id, for_update=True)
    changes = data.model_dump(exclude_unset=True)
    if changes.get("name") is None:
        changes.pop("name", None)
    if "is_essential" in changes:
        if changes["is_essential"] is None:
            changes.pop("is_essential")
        elif category.kind != CategoryKind.expense and changes["is_essential"]:
            raise ValidationAppError(
                "Only expense categories can be essential",
                details=[{"field": "is_essential", "message": "invalid"}],
            )
    if category.is_system and "name" in changes and changes["name"] != category.name:
        raise ConflictError("System categories cannot be renamed", code="system_category")
    changed = [k for k, v in changes.items() if getattr(category, k) != v]
    for key in changed:
        setattr(category, key, changes[key])
    _flush(db)
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="category",
            entity_id=category.id,
            changed_fields=changed,
        )
    db.commit()
    return category


def delete_category(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID, replacement_id: uuid.UUID | None
) -> CategoryDeleteResult:
    repo = CategoryRepository(db, user_id)
    category = repo.get_or_404(category_id, for_update=True)
    if category.is_system:
        raise ConflictError("System categories cannot be deleted", code="system_category")
    child_ids = list(
        db.scalars(
            select(Category.id).where(
                Category.user_id == user_id, Category.parent_id == category.id
            )
        )
    )
    ids = [category.id, *child_ids]
    in_use = db.scalar(
        select(exists().where(Transaction.user_id == user_id, Transaction.category_id.in_(ids)))
    )
    reassigned = 0
    if in_use:
        if replacement_id is None:
            raise ConflictError(
                "This category has transactions. Choose a replacement category.",
                code="category_in_use",
                details=[{"field": "replacement_id", "message": "required"}],
            )
        replacement = repo.get(replacement_id)
        if replacement is None or replacement.id in ids:
            raise ValidationAppError(
                "Replacement category is invalid",
                code="invalid_replacement",
                details=[{"field": "replacement_id", "message": "invalid"}],
            )
        if replacement.kind != category.kind:
            raise ValidationAppError(
                "Replacement must be of the same kind",
                code="category_kind_mismatch",
                details=[{"field": "replacement_id", "message": "mismatch"}],
            )
        moved = list(
            db.scalars(
                update(Transaction)
                .where(Transaction.user_id == user_id, Transaction.category_id.in_(ids))
                .values(category_id=replacement.id)
                .returning(Transaction.id)
            )
        )
        reassigned = len(moved)
        for txn_id in moved:
            audit.record(
                db,
                actor_user_id=user_id,
                action="update",
                entity_type="transaction",
                entity_id=txn_id,
                changed_fields=["category_id"],
            )
    for cid in ids:
        audit.record(
            db, actor_user_id=user_id, action="delete", entity_type="category", entity_id=cid
        )
    db.delete(category)  # subcategories cascade
    db.commit()
    return CategoryDeleteResult(
        deleted_ids=ids,
        reassigned_transactions=reassigned,
        replacement_id=replacement_id if in_use else None,
    )


def require_category_for(
    db: Session, user_id: uuid.UUID, category_id: uuid.UUID, txn_type: TransactionType
) -> Category:
    """Used by transactions: owned category whose kind matches the transaction type."""
    category = CategoryRepository(db, user_id).get(category_id)
    if category is None:
        raise ValidationAppError(
            "Category not found",
            code="category_not_found",
            details=[{"field": "category_id", "message": "not_found"}],
        )
    expected = KIND_FOR_TXN_TYPE.get(txn_type)
    if expected is not None and category.kind != expected:
        raise ValidationAppError(
            f"A {txn_type.value} needs an {expected.value} category",
            code="category_kind_mismatch",
            details=[{"field": "category_id", "message": "kind_mismatch"}],
        )
    return category


def subtree_ids(db: Session, user_id: uuid.UUID, category_id: uuid.UUID) -> list[uuid.UUID]:
    """A category plus its subcategories (for filters and roll-ups)."""
    children = db.scalars(
        select(Category.id).where(Category.user_id == user_id, Category.parent_id == category_id)
    )
    return [category_id, *children]
