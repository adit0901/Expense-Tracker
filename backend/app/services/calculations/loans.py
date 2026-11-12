"""Loan, EMI, amortization and simulation calculations (spec: loans-emi)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Any, Literal

from app.core.errors import AppError
from app.core.money import ZERO, round_money
from app.services.calculations.periods import add_months, month_end

HUNDRED = Decimal(100)
TWELVE_HUNDRED = Decimal(1200)


@dataclass(frozen=True)
class Installment:
    installment_no: int
    due_date: date
    payment: Decimal
    principal: Decimal
    interest: Decimal
    closing_outstanding: Decimal


@dataclass(frozen=True)
class ScheduleResult:
    installments: list[Installment]
    total_interest: Decimal
    total_principal: Decimal
    emi: Decimal
    end_date: date | None


@dataclass
class LoanBaseline:
    original_principal: Decimal
    annual_rate: Decimal
    tenure_months: int
    start_date: date
    first_emi_date: date
    emi_amount: Decimal | None = None
    baseline_outstanding: Decimal | None = None
    baseline_date: date | None = None


@dataclass
class LoanEvent:
    kind: Literal["rate_change", "prepayment", "emi_override"]
    effective_date: date
    payload: dict[str, Any]


@dataclass
class LoanPaymentRecord:
    payment_date: date
    principal: Decimal
    interest: Decimal
    installment_no: int | None = None


def compute_emi(principal: Decimal, annual_rate: Decimal, tenure_months: int) -> Decimal:
    """Compute reducing-balance monthly EMI rounded half-up to 2 decimals.

    Formula: P * r * (1+r)^n / ((1+r)^n - 1)
    When annual_rate == 0, EMI = P / n.
    """
    if tenure_months <= 0:
        raise ValueError("tenure_months must be positive")
    if principal <= ZERO:
        return ZERO
    if annual_rate == ZERO:
        return round_money(principal / Decimal(tenure_months))

    r = annual_rate / TWELVE_HUNDRED
    one_plus_r = Decimal(1) + r
    one_plus_r_n = one_plus_r**tenure_months
    emi = principal * r * one_plus_r_n / (one_plus_r_n - Decimal(1))
    return round_money(emi)


def installment_date(first_emi_date: date, month_offset: int) -> date:
    """Compute due date for month_offset from first_emi_date, clamping day of month."""
    y, m = add_months(first_emi_date.year, first_emi_date.month, month_offset)
    max_day = month_end(y, m).day
    return date(y, m, min(first_emi_date.day, max_day))


def build_schedule(
    baseline: LoanBaseline,
    events: list[LoanEvent] | None = None,
    payments: list[LoanPaymentRecord] | None = None,
) -> ScheduleResult:
    """Build the expected amortization schedule from baseline and events.

    Schedule is computed on read (pure function).
    Final installment absorbs any residual rounding so closing outstanding is exactly 0.00.
    """
    events = sorted(events or [], key=lambda e: e.effective_date)
    curr_principal = (
        baseline.baseline_outstanding
        if baseline.baseline_outstanding is not None
        else baseline.original_principal
    )
    curr_rate = baseline.annual_rate
    curr_tenure = baseline.tenure_months

    # Determine starting EMI
    if baseline.emi_amount is not None:
        curr_emi = baseline.emi_amount
    else:
        curr_emi = compute_emi(curr_principal, curr_rate, curr_tenure)

    installments: list[Installment] = []
    tot_interest = ZERO
    tot_principal = ZERO
    outstanding = curr_principal
    inst_no = 1
    month_offset = 0

    # Max safety limit: 600 months (50 years)
    max_months = 600
    has_flexible_tenure = False

    while outstanding > ZERO and inst_no <= max_months:
        due = installment_date(baseline.first_emi_date, month_offset)
        month_offset += 1

        # Apply any events taking effect at or before this due date that haven't been applied
        applicable_events = [e for e in events if e.effective_date <= due]
        for ev in list(applicable_events):
            if ev.kind == "rate_change":
                new_rate = Decimal(str(ev.payload.get("annual_rate", curr_rate)))
                strategy = ev.payload.get("strategy", "keep_emi")
                curr_rate = new_rate
                r_month = curr_rate / TWELVE_HUNDRED
                monthly_interest = round_money(outstanding * r_month)
                if strategy == "keep_emi":
                    if curr_emi <= monthly_interest and curr_rate > ZERO:
                        raise AppError(
                            "Negative amortization: EMI cannot be <= monthly interest",
                            code="negative_amortization",
                            status_code=422,
                        )
                    has_flexible_tenure = True
                elif strategy == "keep_tenure":
                    rem_tenure = max(1, curr_tenure - inst_no + 1)
                    curr_emi = compute_emi(outstanding, curr_rate, rem_tenure)
                events.remove(ev)
            elif ev.kind == "prepayment":
                prep_amount = Decimal(str(ev.payload.get("amount", ZERO)))
                strategy = ev.payload.get("strategy", "reduce_tenure")
                outstanding = max(ZERO, outstanding - prep_amount)
                if outstanding == ZERO:
                    break
                if strategy == "reduce_emi":
                    rem_tenure = max(1, curr_tenure - inst_no + 1)
                    curr_emi = compute_emi(outstanding, curr_rate, rem_tenure)
                elif strategy == "reduce_tenure":
                    has_flexible_tenure = True
                events.remove(ev)

        if outstanding <= ZERO:
            break

        # Calculate monthly interest
        r_month = curr_rate / TWELVE_HUNDRED if curr_rate > ZERO else ZERO
        interest = round_money(outstanding * r_month)

        # Check if final installment
        is_final = False
        remaining_months = curr_tenure - inst_no + 1
        if (not has_flexible_tenure and remaining_months <= 1) or (
            outstanding + interest <= curr_emi
        ):
            is_final = True

        if is_final:
            principal = outstanding
            payment = principal + interest
            closing = ZERO
        else:
            payment = curr_emi
            principal = payment - interest
            closing = round_money(outstanding - principal)

        installments.append(
            Installment(
                installment_no=inst_no,
                due_date=due,
                payment=round_money(payment),
                principal=round_money(principal),
                interest=round_money(interest),
                closing_outstanding=closing,
            )
        )

        tot_interest += interest
        tot_principal += principal
        outstanding = closing
        inst_no += 1

        if closing == ZERO:
            break

    end_date = installments[-1].due_date if installments else None

    return ScheduleResult(
        installments=installments,
        total_interest=round_money(tot_interest),
        total_principal=round_money(tot_principal),
        emi=curr_emi,
        end_date=end_date,
    )


@dataclass(frozen=True)
class SimulationResult:
    original_total_interest: Decimal
    simulated_total_interest: Decimal
    interest_saved: Decimal
    original_tenure: int
    simulated_tenure: int
    original_end_date: date | None
    simulated_end_date: date | None
    original_emi: Decimal
    simulated_emi: Decimal
    schedule: list[Installment]


def simulate_loan(
    baseline: LoanBaseline,
    *,
    events: list[LoanEvent] | None = None,
    one_time_prepayment: Decimal | None = None,
    prepayment_date: date | None = None,
    prepayment_strategy: Literal["reduce_tenure", "reduce_emi"] = "reduce_tenure",
    extra_monthly_payment: Decimal | None = None,
    rate_change: Decimal | None = None,
    rate_change_date: date | None = None,
    rate_change_strategy: Literal["keep_emi", "keep_tenure"] = "keep_emi",
) -> SimulationResult:
    """Simulate what-if prepayment, recurring extra payment or rate change without saving."""
    base_events = list(events or [])
    sim_events = [
        LoanEvent(kind=e.kind, effective_date=e.effective_date, payload=dict(e.payload))
        for e in base_events
    ]

    # Baseline schedule
    orig_sched = build_schedule(
        baseline,
        [
            LoanEvent(kind=e.kind, effective_date=e.effective_date, payload=dict(e.payload))
            for e in base_events
        ],
    )

    # Apply one-time prepayment if given
    if one_time_prepayment and one_time_prepayment > ZERO:
        prep_date = prepayment_date or baseline.first_emi_date
        sim_events.append(
            LoanEvent(
                kind="prepayment",
                effective_date=prep_date,
                payload={"amount": one_time_prepayment, "strategy": prepayment_strategy},
            )
        )

    # Apply rate change if given
    if rate_change is not None:
        rc_date = rate_change_date or baseline.first_emi_date
        sim_events.append(
            LoanEvent(
                kind="rate_change",
                effective_date=rc_date,
                payload={"annual_rate": rate_change, "strategy": rate_change_strategy},
            )
        )

    sim_baseline = LoanBaseline(
        original_principal=baseline.original_principal,
        annual_rate=baseline.annual_rate,
        tenure_months=baseline.tenure_months,
        start_date=baseline.start_date,
        first_emi_date=baseline.first_emi_date,
        emi_amount=(baseline.emi_amount or orig_sched.emi) + (extra_monthly_payment or ZERO),
        baseline_outstanding=baseline.baseline_outstanding,
        baseline_date=baseline.baseline_date,
    )

    sim_sched = build_schedule(sim_baseline, sim_events)
    interest_saved = round_money(max(ZERO, orig_sched.total_interest - sim_sched.total_interest))

    return SimulationResult(
        original_total_interest=orig_sched.total_interest,
        simulated_total_interest=sim_sched.total_interest,
        interest_saved=interest_saved,
        original_tenure=len(orig_sched.installments),
        simulated_tenure=len(sim_sched.installments),
        original_end_date=orig_sched.end_date,
        simulated_end_date=sim_sched.end_date,
        original_emi=orig_sched.emi,
        simulated_emi=sim_sched.emi,
        schedule=sim_sched.installments,
    )
