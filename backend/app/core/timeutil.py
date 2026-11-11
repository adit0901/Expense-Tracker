"""Date helpers in the reporting time zone (Asia/Kolkata by default)."""

from __future__ import annotations

from datetime import date, datetime
from zoneinfo import ZoneInfo

DEFAULT_TZ = "Asia/Kolkata"


def today_in(tz: str = DEFAULT_TZ) -> date:
    return datetime.now(ZoneInfo(tz)).date()
