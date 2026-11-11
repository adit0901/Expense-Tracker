from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import IncomeSourceType


class IncomeSourceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    type: IncomeSourceType
    default_category_id: uuid.UUID | None = None
    default_account_id: uuid.UUID | None = None


class IncomeSourceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    type: IncomeSourceType | None = None
    default_category_id: uuid.UUID | None = None
    default_account_id: uuid.UUID | None = None
    is_active: bool | None = None


class IncomeSourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    type: IncomeSourceType
    default_category_id: uuid.UUID | None
    default_account_id: uuid.UUID | None
    is_active: bool
    created_at: datetime
