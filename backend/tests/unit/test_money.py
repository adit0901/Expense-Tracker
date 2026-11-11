from decimal import Decimal

import pytest
from pydantic import BaseModel, ValidationError

from app.core.money import PositiveAmount, round_money


class _Txn(BaseModel):
    amount: PositiveAmount
    currency: str = "INR"


def test_decimal_sum_has_no_float_drift() -> None:
    total = sum((Decimal("0.10"), Decimal("0.20"), Decimal("0.30")), Decimal("0"))
    assert total == Decimal("0.60")
    assert str(round_money(total)) == "0.60"


def test_amount_serializes_as_string() -> None:
    assert _Txn(amount=Decimal("1250.5")).model_dump(mode="json") == {
        "amount": "1250.50",
        "currency": "INR",
    }


def test_round_half_up() -> None:
    assert round_money(Decimal("2.345")) == Decimal("2.35")
    assert round_money(Decimal("-2.345")) == Decimal("-2.35")


@pytest.mark.parametrize("bad", ["0", "-100", "10.555"])
def test_invalid_amounts_rejected(bad: str) -> None:
    with pytest.raises(ValidationError):
        _Txn(amount=Decimal(bad))
