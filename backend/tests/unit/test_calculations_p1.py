from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from app.core.errors import AppError
from app.services.calculations import (
    LoanBaseline,
    LoanEvent,
    budget_remaining,
    budget_utilization,
    build_schedule,
    compute_emi,
    compute_growth,
    compute_net_worth_figures,
    emergency_fund_coverage,
    goal_estimated_completion_date,
    goal_progress_pct,
    goal_required_monthly_contribution,
    savings_target_achievement,
    simulate_loan,
)

# -----------------------------------------------------------------------------
# 2.1 EMI & Amortization
# -----------------------------------------------------------------------------

def test_emi_spec_examples() -> None:
    # Standard EMI: P = 1000000, 12%, 12 months -> 88848.79
    emi_12m = compute_emi(Decimal("1000000.00"), Decimal("12.0"), 12)
    assert emi_12m == Decimal("88848.79")

    # Zero-interest: P = 100000, 0%, 12 months -> 8333.33
    emi_zero = compute_emi(Decimal("100000.00"), Decimal("0.0"), 12)
    assert emi_zero == Decimal("8333.33")

    # Home loan: P = 5000000, 8.5%, 240 months -> 43391.16
    emi_home = compute_emi(Decimal("5000000.00"), Decimal("8.5"), 240)
    assert emi_home == Decimal("43391.16")


def test_amortization_schedule_spec_example() -> None:
    baseline = LoanBaseline(
        original_principal=Decimal("1000000.00"),
        annual_rate=Decimal("12.0"),
        tenure_months=12,
        start_date=date(2026, 1, 1),
        first_emi_date=date(2026, 2, 1),
    )
    res = build_schedule(baseline)
    assert len(res.installments) == 12

    inst1 = res.installments[0]
    assert inst1.payment == Decimal("88848.79")
    assert inst1.interest == Decimal("10000.00")
    assert inst1.principal == Decimal("78848.79")
    assert inst1.closing_outstanding == Decimal("921151.21")

    inst12 = res.installments[11]
    assert inst12.payment == Decimal("88848.76")
    assert inst12.closing_outstanding == Decimal("0.00")

    assert res.total_interest == Decimal("66185.45")
    assert res.total_principal == Decimal("1000000.00")


def test_zero_rate_amortization_schedule() -> None:
    baseline = LoanBaseline(
        original_principal=Decimal("100000.00"),
        annual_rate=Decimal("0.0"),
        tenure_months=12,
        start_date=date(2026, 1, 1),
        first_emi_date=date(2026, 2, 1),
    )
    res = build_schedule(baseline)
    assert len(res.installments) == 12
    for i in range(11):
        assert res.installments[i].payment == Decimal("8333.33")
        assert res.installments[i].interest == Decimal("0.00")
        assert res.installments[i].principal == Decimal("8333.33")

    assert res.installments[11].payment == Decimal("8333.37")
    assert res.installments[11].interest == Decimal("0.00")
    assert res.installments[11].principal == Decimal("8333.37")
    assert res.installments[11].closing_outstanding == Decimal("0.00")
    assert res.total_principal == Decimal("100000.00")


@pytest.mark.parametrize("p,rate,n", [
    (Decimal("500000.00"), Decimal("9.5"), 36),
    (Decimal("2500000.00"), Decimal("7.8"), 180),
    (Decimal("75000.00"), Decimal("14.0"), 24),
])
def test_amortization_property_closing_and_sum(p: Decimal, rate: Decimal, n: int) -> None:
    baseline = LoanBaseline(
        original_principal=p,
        annual_rate=rate,
        tenure_months=n,
        start_date=date(2026, 1, 1),
        first_emi_date=date(2026, 2, 1),
    )
    res = build_schedule(baseline)
    assert res.installments[-1].closing_outstanding == Decimal("0.00")
    assert res.total_principal == p


# -----------------------------------------------------------------------------
# 2.2 Prepayment, Rate Change, Simulation
# -----------------------------------------------------------------------------

def test_prepayment_reduce_tenure() -> None:
    baseline = LoanBaseline(
        original_principal=Decimal("5000000.00"),
        annual_rate=Decimal("8.5"),
        tenure_months=240,
        start_date=date(2026, 1, 1),
        first_emi_date=date(2026, 2, 1),
    )
    base_res = build_schedule(baseline)

    # Prepay 500,000 on month 2 with reduce_tenure
    event = LoanEvent(
        kind="prepayment",
        effective_date=date(2026, 2, 15),
        payload={"amount": Decimal("500000.00"), "strategy": "reduce_tenure"},
    )
    prep_res = build_schedule(baseline, events=[event])

    assert len(prep_res.installments) < len(base_res.installments)
    assert prep_res.total_interest < base_res.total_interest
    assert prep_res.emi == base_res.emi


def test_rate_change_scenarios() -> None:
    baseline = LoanBaseline(
        original_principal=Decimal("5000000.00"),
        annual_rate=Decimal("8.5"),
        tenure_months=240,
        start_date=date(2026, 1, 1),
        first_emi_date=date(2026, 2, 1),
    )
    # Rate hike from 8.5% to 9.0% with keep_emi
    event = LoanEvent(
        kind="rate_change",
        effective_date=date(2026, 2, 1),
        payload={"annual_rate": Decimal("9.0"), "strategy": "keep_emi"},
    )
    res_hike = build_schedule(baseline, events=[event])
    assert len(res_hike.installments) > 240
    assert res_hike.emi == Decimal("43391.16")

    # Negative amortization test: huge rate hike making monthly interest > emi
    bad_event = LoanEvent(
        kind="rate_change",
        effective_date=date(2026, 2, 1),
        payload={"annual_rate": Decimal("25.0"), "strategy": "keep_emi"},
    )
    with pytest.raises(AppError) as exc_info:
        build_schedule(baseline, events=[bad_event])
    assert exc_info.value.status_code == 422
    assert exc_info.value.code == "negative_amortization"


def test_loan_simulation() -> None:
    baseline = LoanBaseline(
        original_principal=Decimal("5000000.00"),
        annual_rate=Decimal("8.5"),
        tenure_months=240,
        start_date=date(2026, 1, 1),
        first_emi_date=date(2026, 2, 1),
    )
    sim = simulate_loan(baseline, extra_monthly_payment=Decimal("5000.00"))
    assert sim.simulated_tenure < sim.original_tenure
    assert sim.interest_saved > Decimal("0.00")
    assert sim.simulated_total_interest < sim.original_total_interest


# -----------------------------------------------------------------------------
# 2.3 Planning Formulas (Budgets, Goals, Emergency Fund)
# -----------------------------------------------------------------------------

def test_budget_utilization_and_remaining() -> None:
    # 45000 on 60000 -> 75.00
    assert budget_utilization(Decimal("45000.00"), Decimal("60000.00")) == Decimal("75.00")
    # 13500 on 12000 -> 112.50, remaining -1500.00
    assert budget_utilization(Decimal("13500.00"), Decimal("12000.00")) == Decimal("112.50")
    assert budget_remaining(Decimal("12000.00"), Decimal("13500.00")) == Decimal("-1500.00")

    with pytest.raises(ValueError):
        budget_utilization(Decimal("100.00"), Decimal("0.00"))


def test_savings_target_achievement() -> None:
    # 36000 on 30000 -> 120.00
    ach, shortfall = savings_target_achievement(Decimal("36000.00"), Decimal("30000.00"))
    assert ach == Decimal("120.00")
    assert shortfall == Decimal("0.00")

    # Negative savings: -5000 on 30000 -> 0.00, shortfall 35000
    ach_neg, shortfall_neg = savings_target_achievement(Decimal("-5000.00"), Decimal("30000.00"))
    assert ach_neg == Decimal("0.00")
    assert shortfall_neg == Decimal("35000.00")


def test_goal_projections() -> None:
    # Required contribution: 225000.00 remains and 9 full months
    rem = Decimal("225000.00")
    as_of = date(2026, 1, 15)
    target_date = date(2026, 10, 15)
    req = goal_required_monthly_contribution(rem, target_date, as_of)
    assert req == Decimal("25000.00")

    # Overdue goal
    overdue_req = goal_required_monthly_contribution(rem, date(2025, 12, 31), as_of)
    assert overdue_req is None

    # Estimated completion date with zero / negative 3m average
    assert goal_estimated_completion_date(rem, Decimal("0.00"), as_of) is None
    assert goal_estimated_completion_date(rem, Decimal("-500.00"), as_of) is None

    # Estimated completion date with positive contribution
    est_date = goal_estimated_completion_date(
        Decimal("75000.00"), Decimal("25000.00"), date(2026, 1, 15)
    )
    assert est_date == date(2026, 4, 15)

    assert goal_progress_pct(Decimal("100000.00"), Decimal("75000.00")) == Decimal("75.00")
    assert goal_progress_pct(Decimal("100000.00"), Decimal("120000.00")) == Decimal("100.00")


def test_emergency_fund_coverage() -> None:
    # 300000 liquid / 50000 essential -> 6.00 months
    cov = emergency_fund_coverage(Decimal("300000.00"), Decimal("50000.00"))
    assert cov == Decimal("6.00")

    # Denominator zero -> None
    assert emergency_fund_coverage(Decimal("300000.00"), Decimal("0.00")) is None


# -----------------------------------------------------------------------------
# 2.4 Net Worth Engine
# -----------------------------------------------------------------------------

def test_compute_net_worth_spec_example() -> None:
    # bank 300000, FD 205000, gold 165000, card 25000, home loan 4800000
    res = compute_net_worth_figures(
        as_of=date(2026, 11, 1),
        bank_and_cash_balances=[("HDFC Bank", Decimal("300000.00"))],
        asset_valuations=[
            ("FD 1", "fixed_deposit", Decimal("205000.00"), True),
            ("Gold", "gold", Decimal("165000.00"), False),
        ],
        loan_outstandings=[("Home Loan", Decimal("4800000.00"))],
        other_liabilities=[],
        credit_card_outstandings=[("ICICI Card", Decimal("25000.00"))],
    )
    assert res.total_assets == Decimal("670000.00")
    assert res.total_liabilities == Decimal("4825000.00")
    assert res.net_worth == Decimal("-4155000.00")
    assert res.liquid_assets == Decimal("505000.00")

    # Check shares sum to 100%
    asset_shares = sum((item.share_pct for item in res.asset_breakdown), Decimal("0"))
    assert asset_shares == Decimal("100.00")

    liab_shares = sum((item.share_pct for item in res.liability_breakdown), Decimal("0"))
    assert liab_shares == Decimal("100.00")


def test_compute_net_worth_overdraft() -> None:
    # Bank account balance -2000.00 -> 2000.00 counted as liability, not negative asset
    res = compute_net_worth_figures(
        as_of=date(2026, 11, 1),
        bank_and_cash_balances=[("Overdrawn Account", Decimal("-2000.00"))],
        asset_valuations=[],
        loan_outstandings=[],
        other_liabilities=[],
        credit_card_outstandings=[],
    )
    assert res.total_assets == Decimal("0.00")
    assert res.total_liabilities == Decimal("2000.00")
    assert res.net_worth == Decimal("-2000.00")


def test_growth_computation() -> None:
    # MoM: 1000000 to 1050000 -> 50000.00 (5.00%)
    amt, pct = compute_growth(Decimal("1050000.00"), Decimal("1000000.00"))
    assert amt == Decimal("50000.00")
    assert pct == Decimal("5.00")

    # Missing previous
    amt_none, pct_none = compute_growth(Decimal("1050000.00"), None)
    assert amt_none is None
    assert pct_none is None

    # Negative base
    amt_neg, pct_neg = compute_growth(Decimal("-100000.00"), Decimal("-200000.00"))
    assert amt_neg == Decimal("100000.00")
    assert pct_neg == Decimal("50.00")
