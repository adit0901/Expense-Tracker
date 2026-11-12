"""Net worth calculation engine (spec: net-worth, financial-calculations)."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any

from app.core.money import ZERO, round_money, round_pct

HUNDRED = Decimal(100)


def default_investment_value_provider(user_id: Any, as_of: date) -> Decimal:
    """Registered no-op hook for P1. P2 plugs in market-valued investments."""
    return ZERO


@dataclass(frozen=True)
class BreakdownItem:
    category: str
    amount: Decimal
    share_pct: Decimal  # Share of total assets or total liabilities (0.00 to 100.00)


@dataclass(frozen=True)
class NetWorthResult:
    as_of: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    liquid_assets: Decimal
    asset_breakdown: list[BreakdownItem]
    liability_breakdown: list[BreakdownItem]


def compute_net_worth_figures(
    as_of: date,
    *,
    bank_and_cash_balances: list[tuple[str, Decimal]],  # (name/type, balance)
    asset_valuations: list[tuple[str, str, Decimal, bool]],  # (name, type, value, is_liquid)
    loan_outstandings: list[tuple[str, Decimal]],  # (name/type, outstanding)
    other_liabilities: list[tuple[str, Decimal]],  # (name, amount)
    credit_card_outstandings: list[tuple[str, Decimal]],  # (name, outstanding)
    investment_provider: Callable[[Any, date], Decimal] = default_investment_value_provider,
    user_id: Any = None,
) -> NetWorthResult:
    """Compute net worth = total assets - total liabilities as of a date.

    Overdraft (negative bank balances) is counted as a liability, not negative asset.
    Bank/cash/wallet balances >= 0 are assets.
    """
    asset_by_cat: dict[str, Decimal] = {}
    liability_by_cat: dict[str, Decimal] = {}
    liquid_total = ZERO

    # 1. Bank and cash accounts
    bank_asset_sum = ZERO
    overdraft_sum = ZERO
    for _, balance in bank_and_cash_balances:
        if balance >= ZERO:
            bank_asset_sum += balance
            liquid_total += balance
        else:
            # Overdraft: counted as liability
            overdraft_sum += abs(balance)

    if bank_asset_sum > ZERO:
        asset_by_cat["bank_cash"] = bank_asset_sum
    if overdraft_sum > ZERO:
        liability_by_cat["overdraft"] = overdraft_sum

    # 2. Manual assets
    for _, atype, value, is_liquid in asset_valuations:
        if value > ZERO:
            asset_by_cat[atype] = asset_by_cat.get(atype, ZERO) + value
            if is_liquid:
                liquid_total += value

    # 3. Investment hook (P2)
    inv_value = investment_provider(user_id, as_of)
    if inv_value > ZERO:
        asset_by_cat["investments"] = asset_by_cat.get("investments", ZERO) + inv_value

    # 4. Credit cards (positive outstanding is liability)
    card_sum = ZERO
    for _, bal in credit_card_outstandings:
        if bal > ZERO:
            card_sum += bal
    if card_sum > ZERO:
        liability_by_cat["credit_cards"] = card_sum

    # 5. Loans
    loan_sum = ZERO
    for _, out in loan_outstandings:
        if out > ZERO:
            loan_sum += out
    if loan_sum > ZERO:
        liability_by_cat["loans"] = loan_sum

    # 6. Other liabilities
    other_sum = ZERO
    for _, bal in other_liabilities:
        if bal > ZERO:
            other_sum += bal
    if other_sum > ZERO:
        liability_by_cat["other_liabilities"] = other_sum

    total_assets = round_money(sum(asset_by_cat.values(), ZERO))
    total_liabilities = round_money(sum(liability_by_cat.values(), ZERO))
    net_worth = round_money(total_assets - total_liabilities)

    # Build breakdowns with shares summing to 100%
    asset_items: list[BreakdownItem] = []
    if total_assets > ZERO:
        for cat, val in asset_by_cat.items():
            share = round_pct((val / total_assets) * HUNDRED)
            asset_items.append(
                BreakdownItem(category=cat, amount=round_money(val), share_pct=share)
            )
        # Ensure exact 100% sum on the last item if rounding difference
        if asset_items:
            tot_share = sum((item.share_pct for item in asset_items[:-1]), ZERO)
            last = asset_items[-1]
            asset_items[-1] = BreakdownItem(
                category=last.category,
                amount=last.amount,
                share_pct=round_pct(HUNDRED - tot_share),
            )

    liability_items: list[BreakdownItem] = []
    if total_liabilities > ZERO:
        for cat, val in liability_by_cat.items():
            share = round_pct((val / total_liabilities) * HUNDRED)
            liability_items.append(
                BreakdownItem(category=cat, amount=round_money(val), share_pct=share)
            )
        if liability_items:
            tot_share = sum((item.share_pct for item in liability_items[:-1]), ZERO)
            last = liability_items[-1]
            liability_items[-1] = BreakdownItem(
                category=last.category,
                amount=last.amount,
                share_pct=round_pct(HUNDRED - tot_share),
            )

    return NetWorthResult(
        as_of=as_of,
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=net_worth,
        liquid_assets=round_money(liquid_total),
        asset_breakdown=asset_items,
        liability_breakdown=liability_items,
    )


def compute_growth(
    current: Decimal,
    previous: Decimal | None,
) -> tuple[Decimal | None, Decimal | None]:
    """Compute change in amount and percent versus a previous period.

    Percent change is null when base is zero or base is missing.
    Computed on absolute base when base is negative.
    """
    if previous is None:
        return None, None
    amount_change = round_money(current - previous)
    if previous == ZERO:
        return amount_change, None
    pct = round_pct((amount_change / abs(previous)) * HUNDRED)
    return amount_change, pct
