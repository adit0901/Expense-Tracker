"""Calendar periods in the user's time zone (financial-calculations: period boundaries).

Transactions belong to a period by their transaction date (not entry time).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum


class PeriodKind(StrEnum):
    this_month = "this_month"
    last_month = "last_month"
    this_quarter = "this_quarter"
    this_year = "this_year"
    this_fy = "this_fy"
    custom = "custom"


@dataclass(frozen=True)
class Period:
    start: date
    end: date  # inclusive
    granularity: str  # month | quarter | year | fy | custom
    label: str

    @property
    def days(self) -> int:
        return (self.end - self.start).days + 1


_MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]


def add_months(year: int, month: int, delta: int) -> tuple[int, int]:
    idx = year * 12 + (month - 1) + delta
    return idx // 12, idx % 12 + 1


def month_end(year: int, month: int) -> date:
    ny, nm = add_months(year, month, 1)
    return date(ny, nm, 1) - timedelta(days=1)


def month_period(year: int, month: int) -> Period:
    return Period(
        date(year, month, 1), month_end(year, month), "month", f"{_MONTHS[month - 1]} {year}"
    )


def quarter_period(year: int, quarter: int) -> Period:
    first = 3 * (quarter - 1) + 1
    return Period(date(year, first, 1), month_end(year, first + 2), "quarter", f"Q{quarter} {year}")


def year_period(year: int) -> Period:
    return Period(date(year, 1, 1), date(year, 12, 31), "year", str(year))


def fy_period(start_year: int) -> Period:
    """Indian financial year: 1 April start_year .. 31 March start_year+1."""
    return Period(
        date(start_year, 4, 1),
        date(start_year + 1, 3, 31),
        "fy",
        f"FY {start_year}-{str(start_year + 1)[-2:]}",
    )


def fy_start_year(d: date) -> int:
    return d.year if d.month >= 4 else d.year - 1


def custom_period(start: date, end: date) -> Period:
    if end < start:
        raise ValueError("end date must not be before start date")
    return Period(start, end, "custom", f"{start.isoformat()} to {end.isoformat()}")


def resolve_period(
    kind: PeriodKind, today: date, start: date | None = None, end: date | None = None
) -> Period:
    match kind:
        case PeriodKind.this_month:
            return month_period(today.year, today.month)
        case PeriodKind.last_month:
            return month_period(*add_months(today.year, today.month, -1))
        case PeriodKind.this_quarter:
            return quarter_period(today.year, (today.month - 1) // 3 + 1)
        case PeriodKind.this_year:
            return year_period(today.year)
        case PeriodKind.this_fy:
            return fy_period(fy_start_year(today))
        case PeriodKind.custom:
            if start is None or end is None:
                raise ValueError("custom periods need start and end dates")
            return custom_period(start, end)


def previous_period(p: Period) -> Period:
    """The previous equivalent period (same granularity, immediately preceding)."""
    match p.granularity:
        case "month":
            return month_period(*add_months(p.start.year, p.start.month, -1))
        case "quarter":
            y, m = add_months(p.start.year, p.start.month, -3)
            return quarter_period(y, (m - 1) // 3 + 1)
        case "year":
            return year_period(p.start.year - 1)
        case "fy":
            return fy_period(p.start.year - 1)
        case _:
            new_end = p.start - timedelta(days=1)
            return custom_period(new_end - timedelta(days=p.days - 1), new_end)


def months_in(p: Period) -> list[tuple[int, int]]:
    """(year, month) pairs touched by the period, in order."""
    out: list[tuple[int, int]] = []
    y, m = p.start.year, p.start.month
    while (y, m) <= (p.end.year, p.end.month):
        out.append((y, m))
        y, m = add_months(y, m, 1)
    return out


def trailing_months(end: date, count: int) -> list[tuple[int, int]]:
    """The `count` calendar months ending with the month containing `end`."""
    return [add_months(end.year, end.month, -i) for i in range(count - 1, -1, -1)]


def month_label(year: int, month: int) -> str:
    return f"{_MONTHS[month - 1]} {year}"
