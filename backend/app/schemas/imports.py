from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ImportRowOut(BaseModel):
    row: int
    date: str | None
    type: str | None
    amount: str | None
    description: str | None
    payee: str | None
    category_id: str | None
    category_name: str | None
    payment_method: str | None
    errors: list[str]
    warnings: list[str]
    duplicate: bool
    duplicate_of: list[str]
    selected: bool


class ImportBatchOut(BaseModel):
    id: uuid.UUID
    status: str
    file_name: str
    account_id: uuid.UUID
    encoding: str
    date_format: str
    headers: list[str]
    column_mapping: dict[str, Any]
    row_count: int
    valid_count: int
    invalid_count: int
    duplicate_count: int
    imported_count: int
    rows: list[ImportRowOut]
    created_at: datetime
    confirmed_at: datetime | None
    undone_at: datetime | None
    undo_available_until: datetime | None


class ImportConfirmIn(BaseModel):
    selected_rows: list[int] | None = Field(
        default=None,
        description="Row numbers to import. Defaults to rows selected in the preview "
        "(valid, non-duplicate).",
    )
