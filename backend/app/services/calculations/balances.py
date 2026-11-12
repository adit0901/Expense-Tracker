"""Sign rules: how each transaction type moves an account's balance.

This module is the single definition of transaction effects on balances; both the Python
fold (`signed_effect`) and the SQL aggregation in `repositories/balances.py` are built from
the same tables below.

Asset accounts (bank, cash, wallet): balance = money held.
Credit card accounts: balance = amount owed ("Outstanding"), so every effect is negated:
purchases increase it and bill payments (transfers into the card) decrease it.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import Decimal

from app.models.enums import AccountType, TransactionType

# Effect on the account in `account_id` (the source side), for asset accounts.
SOURCE_SIGN: dict[TransactionType, int] = {
    TransactionType.income: 1,
    TransactionType.expense: -1,
    TransactionType.refund: 1,
    TransactionType.transfer: -1,
    TransactionType.loan_payment: -1,
}
# Effect on `counter_account_id` (only transfers have one), for asset accounts.
COUNTER_SIGN: dict[TransactionType, int] = {TransactionType.transfer: 1}

LIABILITY_ACCOUNT_TYPES = frozenset({AccountType.credit_card})
LIQUID_ACCOUNT_TYPES = frozenset({AccountType.bank, AccountType.cash})


def account_polarity(account_type: AccountType) -> int:
    return -1 if account_type in LIABILITY_ACCOUNT_TYPES else 1


@dataclass(frozen=True)
class LedgerEntry:
    type: TransactionType
    amount: Decimal
    account_id: object
    counter_account_id: object | None = None


def signed_effect(txn: LedgerEntry, account_id: object, account_type: AccountType) -> Decimal:
    """Signed change a transaction makes to the given account's balance (0 if unrelated)."""
    polarity = account_polarity(account_type)
    if txn.account_id == account_id:
        return txn.amount * SOURCE_SIGN[txn.type] * polarity
    if txn.counter_account_id == account_id:
        return txn.amount * COUNTER_SIGN.get(txn.type, 0) * polarity
    return Decimal("0")


def account_balance(
    opening_balance: Decimal,
    account_id: object,
    account_type: AccountType,
    entries: Iterable[LedgerEntry],
) -> Decimal:
    """Opening balance plus the signed sum of the account's transactions."""
    total = opening_balance
    for e in entries:
        total += signed_effect(e, account_id, account_type)
    return total
