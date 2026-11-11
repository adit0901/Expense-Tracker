from __future__ import annotations

import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field

Theme = Literal["light", "dark", "system"]
DateFormat = Literal["DD/MM/YYYY", "MM/DD/YYYY", "YYYY-MM-DD"]
NumberGrouping = Literal["indian", "international"]
WeekStart = Literal["monday", "sunday"]


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: str
    full_name: str
    created_at: datetime


class ProfileUpdate(BaseModel):
    full_name: str | None = Field(default=None, min_length=1, max_length=120)
    email: EmailStr | None = None
    current_password: str | None = Field(default=None, max_length=128)


class PreferencesOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    currency: str
    theme: Theme
    locale: str
    date_format: DateFormat
    number_grouping: NumberGrouping
    week_start: WeekStart
    timezone: str


class PreferencesUpdate(BaseModel):
    currency: str | None = Field(default=None, min_length=3, max_length=3)
    theme: Theme | None = None
    locale: Literal["en-IN", "en-US", "en-GB"] | None = None
    date_format: DateFormat | None = None
    number_grouping: NumberGrouping | None = None
    week_start: WeekStart | None = None
    timezone: str | None = Field(default=None, max_length=64)


class DeleteAccountIn(BaseModel):
    password: str = Field(max_length=128)
