"""Money handling: exact Decimal arithmetic, 2-dp final rounding, string serialization."""

from __future__ import annotations

import decimal
from decimal import ROUND_HALF_UP, Decimal
from typing import Annotated

from pydantic import Field, PlainSerializer

# Project-wide context. DefaultContext is copied into every new thread (FastAPI threadpool).
decimal.DefaultContext.prec = 28
decimal.DefaultContext.rounding = ROUND_HALF_UP
decimal.setcontext(decimal.Context(prec=28, rounding=ROUND_HALF_UP))

CENT = Decimal("0.01")
ZERO = Decimal("0")
SUPPORTED_CURRENCIES = frozenset({"INR"})


def round_money(value: Decimal) -> Decimal:
    """Round a final monetary figure half-up to 2 decimal places."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def round_pct(value: Decimal) -> Decimal:
    """Round a percentage half-up to 2 decimal places."""
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def money_str(value: Decimal) -> str:
    return format(round_money(value), "f")


def _opt_money_str(value: Decimal | None) -> str | None:
    return None if value is None else money_str(value)


# Input: positive amount, at most 2 decimal places. Output: "1250.50".
PositiveAmount = Annotated[
    Decimal,
    Field(gt=0, max_digits=15, decimal_places=2),
    PlainSerializer(money_str, return_type=str, when_used="json"),
]
# Input: any signed amount with at most 2 dp (e.g. opening balances).
SignedAmount = Annotated[
    Decimal,
    Field(max_digits=15, decimal_places=2),
    PlainSerializer(money_str, return_type=str, when_used="json"),
]
# Output-only money/percentage values (computed figures).
MoneyOut = Annotated[Decimal, PlainSerializer(money_str, return_type=str, when_used="json")]
OptionalMoneyOut = Annotated[
    Decimal | None, PlainSerializer(_opt_money_str, return_type=str | None, when_used="json")
]
