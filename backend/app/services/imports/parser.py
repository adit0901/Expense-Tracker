"""CSV parsing for imports: encoding detection, column mapping, row parsing."""

from __future__ import annotations

import csv
import hashlib
import io
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal, InvalidOperation

import filetype
from charset_normalizer import from_bytes
from pydantic import BaseModel, model_validator

from app.core.errors import ValidationAppError
from app.models.enums import PaymentMethod, TransactionType

MAX_ROWS = 5000
DATE_FORMATS: dict[str, str] = {
    "DD/MM/YYYY": "%d/%m/%Y",
    "MM/DD/YYYY": "%m/%d/%Y",
    "YYYY-MM-DD": "%Y-%m-%d",
    "DD-MM-YYYY": "%d-%m-%Y",
    "DD-MMM-YYYY": "%d-%b-%Y",
    "DD/MM/YY": "%d/%m/%y",
}


class ColumnMapping(BaseModel):
    date: str
    amount: str | None = None
    type: str | None = None
    debit: str | None = None
    credit: str | None = None
    description: str | None = None
    payee: str | None = None
    category: str | None = None
    payment_method: str | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def _needs_amount(self) -> ColumnMapping:
        if not self.amount and not (self.debit or self.credit):
            raise ValueError("map either an amount column or debit/credit columns")
        return self

    def columns(self) -> list[str]:
        return [v for v in self.model_dump().values() if v]


_SUGGEST: dict[str, tuple[str, ...]] = {
    "date": ("date", "txn date", "transaction date", "value date", "posting date"),
    "amount": ("amount", "amt", "transaction amount"),
    "type": ("type", "transaction type", "dr/cr", "cr/dr"),
    "debit": ("debit", "withdrawal", "withdrawal amt", "withdrawal amount", "dr"),
    "credit": ("credit", "deposit", "deposit amt", "deposit amount", "cr"),
    "description": ("description", "narration", "details", "particulars", "remarks"),
    "payee": ("payee", "merchant", "beneficiary"),
    "category": ("category",),
    "payment_method": ("payment method", "method", "mode", "payment mode"),
    "notes": ("notes", "note", "memo"),
}


def suggest_mapping(headers: list[str]) -> dict[str, str]:
    norm = {h.strip().lower().replace(".", ""): h for h in headers}
    out: dict[str, str] = {}
    for target, names in _SUGGEST.items():
        for n in names:
            if n in norm and norm[n] not in out.values():
                out[target] = norm[n]
                break
    return out


def decode(data: bytes) -> tuple[str, str]:
    """Return (text, encoding). Rejects binary content masquerading as CSV."""
    if b"\x00" in data[:8192] or filetype.guess(data[:8192]) is not None:
        raise ValidationAppError(
            "The file is not a CSV text file",
            code="unsupported_file_type",
            details=[{"field": "file", "message": "unsupported_type"}],
        )
    for enc in ("utf-8-sig",):
        try:
            return data.decode(enc), "utf-8"
        except UnicodeDecodeError:
            pass
    best = from_bytes(data).best()
    encoding = (best.encoding if best else "cp1252") or "cp1252"
    if encoding.lower().replace("-", "_") not in {"cp1252", "windows_1252", "latin_1", "iso8859_1"}:
        encoding = "cp1252"
    try:
        return data.decode("cp1252"), "windows-1252"
    except UnicodeDecodeError as exc:
        raise ValidationAppError("Unsupported text encoding", code="unsupported_encoding") from exc


def read_table(text: str) -> tuple[list[str], list[dict[str, str]]]:
    sample = text[:4096]
    try:
        dialect: type[csv.Dialect] | csv.Dialect = csv.Sniffer().sniff(sample, delimiters=",;\t")
    except csv.Error:
        dialect = csv.excel
    reader = csv.reader(io.StringIO(text), dialect)
    rows = [r for r in reader if any(c.strip() for c in r)]
    if not rows:
        raise ValidationAppError("The CSV file is empty", code="empty_file")
    headers = [h.strip() for h in rows[0]]
    if len(set(headers)) != len(headers) or not all(headers):
        raise ValidationAppError(
            "CSV header row must have unique, non-empty column names", code="invalid_csv_header"
        )
    body = rows[1:]
    if len(body) > MAX_ROWS:
        raise ValidationAppError(
            f"CSV files can contain at most {MAX_ROWS} rows", code="too_many_rows"
        )
    return headers, [dict(zip(headers, (c.strip() for c in r), strict=False)) for r in body]


_AMOUNT_CLEAN = re.compile(r"[₹,\s]|INR|Rs\.?", re.IGNORECASE)


def parse_amount(raw: str) -> Decimal:
    text = _AMOUNT_CLEAN.sub("", raw)
    negative = False
    if text.startswith("(") and text.endswith(")"):
        text, negative = text[1:-1], True
    if text.endswith(("DR", "Dr", "dr")):
        text, negative = text[:-2], True
    elif text.endswith(("CR", "Cr", "cr")):
        text = text[:-2]
    try:
        value = Decimal(text)
    except InvalidOperation as exc:
        raise ValueError(f"invalid amount '{raw}'") from exc
    if not value.is_finite():
        raise ValueError(f"invalid amount '{raw}'")
    if value.as_tuple().exponent < -2:  # type: ignore[operator]
        raise ValueError(f"amount '{raw}' has more than 2 decimal places")
    return -value if negative else value


def parse_date(raw: str, date_format: str) -> date:
    try:
        return datetime.strptime(raw.strip(), DATE_FORMATS[date_format]).date()
    except (ValueError, KeyError) as exc:
        raise ValueError(f"invalid date '{raw}' (expected {date_format})") from exc


_TYPE_WORDS = {
    "income": TransactionType.income,
    "credit": TransactionType.income,
    "cr": TransactionType.income,
    "deposit": TransactionType.income,
    "expense": TransactionType.expense,
    "debit": TransactionType.expense,
    "dr": TransactionType.expense,
    "withdrawal": TransactionType.expense,
    "refund": TransactionType.refund,
}

_METHOD_WORDS = {
    "upi": PaymentMethod.upi,
    "gpay": PaymentMethod.upi,
    "phonepe": PaymentMethod.upi,
    "paytm": PaymentMethod.upi,
    "cash": PaymentMethod.cash,
    "atm": PaymentMethod.cash,
    "debit card": PaymentMethod.debit_card,
    "debit_card": PaymentMethod.debit_card,
    "dc": PaymentMethod.debit_card,
    "credit card": PaymentMethod.credit_card,
    "credit_card": PaymentMethod.credit_card,
    "cc": PaymentMethod.credit_card,
    "neft": PaymentMethod.bank_transfer,
    "imps": PaymentMethod.bank_transfer,
    "rtgs": PaymentMethod.bank_transfer,
    "bank transfer": PaymentMethod.bank_transfer,
    "bank_transfer": PaymentMethod.bank_transfer,
    "other": PaymentMethod.other,
}


def parse_method(raw: str | None) -> PaymentMethod | None:
    if not raw:
        return None
    return _METHOD_WORDS.get(raw.strip().lower())


@dataclass
class ParsedRow:
    row: int
    txn_date: date | None = None
    type: TransactionType | None = None
    amount: Decimal | None = None
    description: str | None = None
    payee: str | None = None
    category: str | None = None
    payment_method_raw: str | None = None
    notes: str | None = None
    errors: list[str] = field(default_factory=list)


def _get(rec: dict[str, str], col: str | None) -> str | None:
    if not col:
        return None
    v = rec.get(col)
    return v.strip() if v and v.strip() else None


def parse_row(n: int, rec: dict[str, str], m: ColumnMapping, date_format: str) -> ParsedRow:
    p = ParsedRow(
        row=n,
        description=_get(rec, m.description),
        payee=_get(rec, m.payee),
        category=_get(rec, m.category),
        payment_method_raw=_get(rec, m.payment_method),
        notes=_get(rec, m.notes),
    )
    raw_date = _get(rec, m.date)
    if raw_date is None:
        p.errors.append("missing date")
    else:
        try:
            p.txn_date = parse_date(raw_date, date_format)
        except ValueError as e:
            p.errors.append(str(e))
    try:
        if m.amount:
            raw = _get(rec, m.amount)
            if raw is None:
                raise ValueError("missing amount")
            value = parse_amount(raw)
            type_word = (_get(rec, m.type) or "").lower()
            if type_word:
                if type_word not in _TYPE_WORDS:
                    raise ValueError(f"unknown type '{type_word}'")
                p.type = _TYPE_WORDS[type_word]
            else:
                p.type = TransactionType.expense if value < 0 else TransactionType.income
            p.amount = abs(value)
        else:
            debit, credit = _get(rec, m.debit), _get(rec, m.credit)
            d = abs(parse_amount(debit)) if debit else Decimal(0)
            c = abs(parse_amount(credit)) if credit else Decimal(0)
            if d and c:
                raise ValueError("both debit and credit are set")
            p.type = TransactionType.expense if d else TransactionType.income
            p.amount = d or c
        if not p.amount:
            raise ValueError("amount must be greater than 0")
    except ValueError as e:
        p.errors.append(str(e))
    if p.description and len(p.description) > 255:
        p.description = p.description[:255]
    if p.payee and len(p.payee) > 120:
        p.payee = p.payee[:120]
    return p


def fingerprint(txn_date: date, amount: Decimal, description: str | None) -> str:
    raw = f"{txn_date.isoformat()}|{amount:.2f}|{(description or '').strip().lower()}"
    return hashlib.sha256(raw.encode()).hexdigest()
