"""Table-driven tests for transaction sign rules (signed_effect)."""

from decimal import Decimal

import pytest

from app.models.enums import AccountType, TransactionType
from app.services.calculations.balances import LedgerEntry, account_balance, signed_effect

A, B = "acct-a", "acct-b"
T = TransactionType
AT = AccountType
D = Decimal


@pytest.mark.parametrize(
    ("txn_type", "account_type", "side", "expected"),
    [
        (T.income, AT.bank, "source", D("100")),
        (T.expense, AT.bank, "source", D("-100")),
        (T.refund, AT.bank, "source", D("100")),
        (T.transfer, AT.bank, "source", D("-100")),
        (T.transfer, AT.wallet, "counter", D("100")),
        (T.expense, AT.cash, "source", D("-100")),
        # Credit card balances are amounts owed: purchases raise, payments/refunds lower.
        (T.expense, AT.credit_card, "source", D("100")),
        (T.refund, AT.credit_card, "source", D("-100")),
        (T.income, AT.credit_card, "source", D("-100")),
        (T.transfer, AT.credit_card, "counter", D("-100")),
        (T.transfer, AT.credit_card, "source", D("100")),
        (T.expense, AT.bank, "unrelated", D("0")),
    ],
)
def test_signed_effect(
    txn_type: TransactionType, account_type: AccountType, side: str, expected: Decimal
) -> None:
    entry = LedgerEntry(
        type=txn_type,
        amount=D("100"),
        account_id=A,
        counter_account_id=B if txn_type == T.transfer else None,
    )
    target = {"source": A, "counter": B, "unrelated": "other"}[side]
    assert signed_effect(entry, target, account_type) == expected


def test_bank_balance_scenario() -> None:
    entries = [LedgerEntry(T.income, D("80000.00"), A), LedgerEntry(T.expense, D("12000.00"), A)]
    assert account_balance(D("50000.00"), A, AT.bank, entries) == D("118000.00")


def test_card_purchase_and_bill_payment() -> None:
    card, bank = "card", "bank"
    entries = [
        LedgerEntry(T.expense, D("15000.00"), card),
        LedgerEntry(T.transfer, D("10000.00"), bank, card),
    ]
    assert account_balance(D("0"), card, AT.credit_card, entries) == D("5000.00")
    assert account_balance(D("20000"), bank, AT.bank, entries) == D("10000.00")
