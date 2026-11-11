"""CSV export of a filtered transaction list (UTF-8, ISO dates, plain decimals)."""

from __future__ import annotations

import csv
import io
from collections.abc import Iterable, Sequence

from app.core.money import money_str
from app.schemas.transactions import TransactionOut

FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")

HEADER = [
    "date",
    "type",
    "account",
    "to_account",
    "category",
    "subcategory",
    "amount",
    "currency",
    "payment_method",
    "payee",
    "description",
    "notes",
    "tags",
]


def escape_cell(value: object) -> str:
    """Neutralize spreadsheet formula injection by prefixing a single quote."""
    text = "" if value is None else str(value)
    if text.startswith(FORMULA_PREFIXES):
        return "'" + text
    return text


def write_csv(header: Sequence[str], rows: Iterable[Sequence[object]]) -> str:
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(header)
    for row in rows:
        writer.writerow([escape_cell(v) for v in row])
    return buf.getvalue()


def transactions_csv(items: Iterable[TransactionOut]) -> str:
    def row(t: TransactionOut) -> list[object]:
        top = t.parent_category_name or t.category_name
        sub = t.category_name if t.parent_category_name else None
        return [
            t.txn_date.isoformat(),
            t.type.value,
            t.account_name,
            t.counter_account_name,
            top,
            sub,
            money_str(t.amount),
            t.currency,
            t.payment_method.value if t.payment_method else None,
            t.payee,
            t.description,
            t.notes,
            ";".join(t.tags),
        ]

    return write_csv(HEADER, (row(t) for t in items))
