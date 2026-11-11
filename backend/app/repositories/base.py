"""Base repository: every query is scoped to the owning user."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError


class OwnedRepository[M]:
    """Query helper for a user-owned model. `user_id` is mandatory and always applied."""

    model: type[M]
    entity_name: str = "Resource"

    def __init__(self, db: Session, user_id: uuid.UUID) -> None:
        if user_id is None:
            raise ValueError("user_id is required")
        self.db = db
        self.user_id = user_id

    @property
    def _user_col(self) -> Any:
        return self.model.__table__.c.user_id  # type: ignore[attr-defined]

    @property
    def _id_col(self) -> Any:
        return self.model.__table__.c.id  # type: ignore[attr-defined]

    def select(self) -> Select[Any]:
        return select(self.model).where(self._user_col == self.user_id)

    def get(self, entity_id: uuid.UUID, *, for_update: bool = False) -> M | None:
        stmt = self.select().where(self._id_col == entity_id)
        if for_update:
            stmt = stmt.with_for_update()
        result: M | None = self.db.scalars(stmt).one_or_none()
        return result

    def get_or_404(self, entity_id: uuid.UUID, *, for_update: bool = False) -> M:
        obj = self.get(entity_id, for_update=for_update)
        if obj is None:
            raise NotFoundError(self.entity_name)
        return obj
