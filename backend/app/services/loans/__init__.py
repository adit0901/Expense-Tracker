"""Loan and EMI service: schedules, payments, prepayments, simulations, summaries."""

from __future__ import annotations

import uuid
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.errors import NotFoundError, ValidationAppError
from app.core.money import ZERO, round_money
from app.models.category import Category
from app.models.enums import (
    CategoryKind,
    LoanEventKind,
    LoanStatus,
    TransactionStatus,
    TransactionType,
)
from app.models.loan import Loan, LoanEventModel, LoanPayment
from app.models.transaction import Transaction
from app.repositories.base import OwnedRepository
from app.schemas.loan import (
    InstallmentOut,
    LoanCreate,
    LoanEventCreate,
    LoanEventOut,
    LoanOut,
    LoanPaymentCreate,
    LoanPaymentOut,
    LoanScheduleOut,
    LoanSimulateOut,
    LoanSimulateRequest,
    LoanSummaryOut,
    LoanUpdate,
)
from app.services import audit
from app.services.accounts import require_active_account
from app.services.calculations.loans import (
    LoanBaseline,
    LoanEvent,
    build_schedule,
    compute_emi,
    installment_date,
    simulate_loan,
)


class LoanRepository(OwnedRepository[Loan]):
    model = Loan
    entity_name = "Loan"


def _get_loan_with_relations(
    db: Session, user_id: uuid.UUID, loan_id: uuid.UUID
) -> Loan:
    stmt = (
        select(Loan)
        .where(Loan.id == loan_id, Loan.user_id == user_id)
        .options(
            selectinload(Loan.events),
            selectinload(Loan.payments),
        )
    )
    loan = db.scalar(stmt)
    if not loan:
        raise NotFoundError("Loan")
    return loan


def _to_baseline(loan: Loan) -> LoanBaseline:
    return LoanBaseline(
        original_principal=loan.original_principal,
        annual_rate=loan.annual_rate,
        tenure_months=loan.tenure_months,
        start_date=loan.start_date,
        first_emi_date=loan.first_emi_date,
        emi_amount=loan.emi_amount if loan.emi_overridden else None,
        baseline_outstanding=loan.baseline_outstanding,
        baseline_date=loan.baseline_date,
    )


def _to_calc_events(events: list[LoanEventModel]) -> list[LoanEvent]:
    return [
        LoanEvent(
            kind=e.kind.value,
            effective_date=e.effective_date,
            payload=e.payload,
        )
        for e in events
    ]


to_baseline = _to_baseline
to_calc_events = _to_calc_events


def _to_loan_out(loan: Loan) -> LoanOut:
    baseline = _to_baseline(loan)
    calc_events = _to_calc_events(loan.events)
    schedule = build_schedule(baseline, calc_events)

    starting_principal = (
        loan.baseline_outstanding
        if loan.baseline_outstanding is not None
        else loan.original_principal
    )
    paid_principal = round_money(sum((p.principal for p in loan.payments), ZERO))
    paid_interest = round_money(sum((p.interest for p in loan.payments), ZERO))
    current_outstanding = round_money(max(ZERO, starting_principal - paid_principal))

    paid_inst_nos = {
        p.installment_no for p in loan.payments if p.installment_no is not None
    }
    unpaid_installments = [
        i for i in schedule.installments if i.installment_no not in paid_inst_nos
    ]

    remaining_interest = round_money(
        sum((i.interest for i in unpaid_installments), ZERO)
    )
    remaining_count = len(unpaid_installments)
    next_inst = unpaid_installments[0] if unpaid_installments else None

    next_date = next_inst.due_date if next_inst else None
    next_amount = next_inst.payment if next_inst else None

    effective_emi = loan.emi_amount or schedule.emi

    return LoanOut(
        id=loan.id,
        type=loan.type,
        lender=loan.lender,
        original_principal=round_money(loan.original_principal),
        annual_rate=loan.annual_rate,
        tenure_months=loan.tenure_months,
        start_date=loan.start_date,
        first_emi_date=loan.first_emi_date,
        emi_amount=round_money(effective_emi),
        emi_overridden=loan.emi_overridden,
        baseline_outstanding=round_money(
            loan.baseline_outstanding or loan.original_principal
        ),
        baseline_date=loan.baseline_date or loan.start_date,
        current_outstanding=current_outstanding,
        paid_principal=paid_principal,
        paid_interest=paid_interest,
        remaining_interest=remaining_interest,
        remaining_installments=remaining_count,
        next_emi_date=next_date,
        next_emi_amount=round_money(next_amount) if next_amount else None,
        end_date=schedule.end_date,
        status=loan.status,
        notes=loan.notes,
        created_at=loan.created_at,
        updated_at=loan.updated_at,
    )


# --- Loan CRUD ---


def create_loan(db: Session, user_id: uuid.UUID, payload: LoanCreate) -> LoanOut:
    first_emi = payload.first_emi_date or installment_date(payload.start_date, 1)

    if payload.emi_amount is not None:
        emi = payload.emi_amount
        overridden = True
    else:
        starting_p = payload.baseline_outstanding or payload.original_principal
        emi = compute_emi(starting_p, payload.annual_rate, payload.tenure_months)
        overridden = False

    loan = Loan(
        user_id=user_id,
        type=payload.type,
        lender=payload.lender,
        original_principal=payload.original_principal,
        annual_rate=payload.annual_rate,
        tenure_months=payload.tenure_months,
        start_date=payload.start_date,
        first_emi_date=first_emi,
        emi_amount=emi,
        emi_overridden=overridden,
        baseline_outstanding=payload.baseline_outstanding,
        baseline_date=payload.baseline_date,
        notes=payload.notes,
    )
    db.add(loan)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="loan",
        entity_id=loan.id,
        changed_fields=[
            "type",
            "lender",
            "original_principal",
            "annual_rate",
            "tenure_months",
        ],
    )
    db.commit()

    loan.events = []
    loan.payments = []
    return _to_loan_out(loan)


def get_loan(db: Session, user_id: uuid.UUID, loan_id: uuid.UUID) -> LoanOut:
    loan = _get_loan_with_relations(db, user_id, loan_id)
    return _to_loan_out(loan)


def list_loans(
    db: Session, user_id: uuid.UUID, status: LoanStatus | None = None
) -> list[LoanOut]:
    stmt = (
        select(Loan)
        .where(Loan.user_id == user_id)
        .options(selectinload(Loan.events), selectinload(Loan.payments))
        .order_by(Loan.created_at.desc())
    )
    if status is not None:
        stmt = stmt.where(Loan.status == status)
    loans = db.scalars(stmt).all()
    return [_to_loan_out(loan_item) for loan_item in loans]


def update_loan(
    db: Session, user_id: uuid.UUID, loan_id: uuid.UUID, payload: LoanUpdate
) -> LoanOut:
    loan = LoanRepository(db, user_id).get_or_404(loan_id)
    changed: list[str] = []

    if payload.lender is not None:
        loan.lender = payload.lender
        changed.append("lender")
    if payload.status is not None:
        loan.status = payload.status
        changed.append("status")
    if payload.notes is not None or "notes" in payload.model_fields_set:
        loan.notes = payload.notes
        changed.append("notes")

    db.flush()
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="loan",
            entity_id=loan.id,
            changed_fields=changed,
        )
    db.commit()

    return get_loan(db, user_id, loan_id)


def delete_loan(db: Session, user_id: uuid.UUID, loan_id: uuid.UUID) -> None:
    loan = LoanRepository(db, user_id).get_or_404(loan_id)
    db.delete(loan)
    db.flush()
    audit.record(
        db,
        actor_user_id=user_id,
        action="delete",
        entity_type="loan",
        entity_id=loan_id,
    )
    db.commit()


# --- Loan Summary ---


def get_loans_summary(db: Session, user_id: uuid.UUID) -> LoanSummaryOut:
    active_loans = list_loans(db, user_id, status=LoanStatus.active)
    tot_outstanding = sum((loan_item.current_outstanding for loan_item in active_loans), ZERO)
    tot_emi = sum((loan_item.emi_amount for loan_item in active_loans), ZERO)

    return LoanSummaryOut(
        total_outstanding=round_money(tot_outstanding),
        total_monthly_emi_commitment=round_money(tot_emi),
        active_loans_count=len(active_loans),
    )


# --- Schedule ---


def get_loan_schedule(
    db: Session, user_id: uuid.UUID, loan_id: uuid.UUID
) -> LoanScheduleOut:
    loan = _get_loan_with_relations(db, user_id, loan_id)
    baseline = _to_baseline(loan)
    calc_events = _to_calc_events(loan.events)
    schedule = build_schedule(baseline, calc_events)

    paid_map: dict[int, date] = {}
    for p in loan.payments:
        if p.installment_no is not None:
            # Query transaction date
            txn_date = db.scalar(
                select(Transaction.txn_date).where(Transaction.id == p.transaction_id)
            )
            paid_map[p.installment_no] = txn_date or date.today()

    inst_outs = [
        InstallmentOut(
            installment_no=i.installment_no,
            due_date=i.due_date,
            payment=round_money(i.payment),
            principal=round_money(i.principal),
            interest=round_money(i.interest),
            closing_outstanding=round_money(i.closing_outstanding),
            is_paid=(i.installment_no in paid_map),
            paid_date=paid_map.get(i.installment_no),
        )
        for i in schedule.installments
    ]

    return LoanScheduleOut(
        loan_id=loan.id,
        installments=inst_outs,
        total_interest=round_money(schedule.total_interest),
        total_principal=round_money(schedule.total_principal),
        emi=round_money(schedule.emi),
        end_date=schedule.end_date,
    )


# --- Payments & Prepayments ---


def record_payment(
    db: Session,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
    payload: LoanPaymentCreate,
) -> LoanPaymentOut:
    loan = _get_loan_with_relations(db, user_id, loan_id)
    account = require_active_account(db, user_id, payload.account_id)

    baseline = _to_baseline(loan)
    calc_events = _to_calc_events(loan.events)
    schedule = build_schedule(baseline, calc_events)

    paid_inst_nos = {
        p.installment_no for p in loan.payments if p.installment_no is not None
    }
    unpaid = [
        i for i in schedule.installments if i.installment_no not in paid_inst_nos
    ]

    if payload.payment_type == "prepayment":
        if payload.amount is None or payload.amount <= ZERO:
            raise ValidationAppError("Prepayment requires a positive amount")
        amount = payload.amount
        principal = amount
        interest = ZERO
        installment_no = None
        strategy = payload.strategy or "reduce_tenure"

        # Record prepayment event to adjust schedule
        event = LoanEventModel(
            loan_id=loan.id,
            kind=LoanEventKind.prepayment,
            effective_date=payload.payment_date,
            payload={"amount": str(amount), "strategy": strategy},
        )
        db.add(event)
        db.flush()
    else:  # installment
        if not unpaid:
            raise ValidationAppError("No unpaid installments remaining for this loan")
        target_inst = unpaid[0]
        installment_no = payload.installment_no or target_inst.installment_no

        interest = (
            payload.interest_component
            if payload.interest_component is not None
            else target_inst.interest
        )
        principal = (
            payload.principal_component
            if payload.principal_component is not None
            else target_inst.principal
        )
        amount = (
            payload.amount
            if payload.amount is not None
            else (principal + interest)
        )

        if principal + interest != amount:
            raise ValidationAppError(
                f"Principal ({principal}) and interest ({interest}) must sum to amount ({amount})"
            )

    # Find Loan Interest category for user
    loan_interest_cat = db.scalar(
        select(Category).where(
            Category.user_id == user_id,
            Category.kind == CategoryKind.expense,
            Category.name == "Loan Interest",
        )
    )
    if not loan_interest_cat:
        loan_interest_cat = db.scalar(
            select(Category).where(
                Category.user_id == user_id,
                Category.kind == CategoryKind.expense,
            )
        )

    # Insert transaction
    desc = f"Loan payment - {loan.lender}" + (
        f" (Installment {installment_no})" if installment_no else " (Prepayment)"
    )
    txn = Transaction(
        user_id=user_id,
        account_id=account.id,
        type=TransactionType.loan_payment,
        amount=amount,
        txn_date=payload.payment_date,
        category_id=loan_interest_cat.id if loan_interest_cat else None,
        status=TransactionStatus.posted,
        loan_id=loan.id,
        principal_component=principal,
        interest_component=interest,
        description=desc,
        notes=payload.notes,
    )
    db.add(txn)
    db.flush()

    # Insert loan payment
    payment = LoanPayment(
        loan_id=loan.id,
        installment_no=installment_no,
        transaction_id=txn.id,
        principal=principal,
        interest=interest,
    )
    db.add(payment)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="loan_payment",
        entity_id=payment.id,
        changed_fields=["loan_id", "principal", "interest", "amount"],
    )

    # Check if fully paid off
    starting_p = loan.baseline_outstanding or loan.original_principal
    total_paid = sum((p.principal for p in loan.payments), ZERO) + principal
    current_rem = max(ZERO, starting_p - total_paid)
    if current_rem == ZERO:
        loan.status = LoanStatus.closed

    from app.services.net_worth import mark_snapshots_stale

    mark_snapshots_stale(db, user_id, payload.payment_date)
    db.commit()

    return LoanPaymentOut(
        id=payment.id,
        loan_id=loan.id,
        transaction_id=txn.id,
        account_id=account.id,
        installment_no=installment_no,
        payment_date=payload.payment_date,
        principal=round_money(principal),
        interest=round_money(interest),
        total_amount=round_money(amount),
        current_outstanding=round_money(current_rem),
        created_at=payment.created_at,
    )


# --- Events ---


def add_loan_event(
    db: Session,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
    payload: LoanEventCreate,
) -> LoanEventOut:
    loan = _get_loan_with_relations(db, user_id, loan_id)

    # Check for negative amortization before saving
    baseline = _to_baseline(loan)
    curr_events = _to_calc_events(loan.events)
    test_event = LoanEvent(
        kind=payload.kind.value,
        effective_date=payload.effective_date,
        payload=payload.payload,
    )
    # This will raise 422 negative_amortization if invalid
    build_schedule(baseline, [*curr_events, test_event])

    event = LoanEventModel(
        loan_id=loan.id,
        kind=payload.kind,
        effective_date=payload.effective_date,
        payload=payload.payload,
    )
    db.add(event)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="loan_event",
        entity_id=event.id,
        changed_fields=["kind", "effective_date"],
    )
    from app.services.net_worth import mark_snapshots_stale

    mark_snapshots_stale(db, user_id, payload.effective_date)
    db.commit()

    return LoanEventOut(
        id=event.id,
        loan_id=event.loan_id,
        kind=event.kind,
        effective_date=event.effective_date,
        payload=event.payload,
        created_at=event.created_at,
    )


# --- Simulation ---


def simulate(
    db: Session,
    user_id: uuid.UUID,
    loan_id: uuid.UUID,
    payload: LoanSimulateRequest,
) -> LoanSimulateOut:
    loan = _get_loan_with_relations(db, user_id, loan_id)
    baseline = _to_baseline(loan)
    calc_events = _to_calc_events(loan.events)

    kwargs: dict[str, Any] = {"events": calc_events}
    if payload.kind == "one_time_prepayment":
        kwargs["one_time_prepayment"] = payload.amount
        kwargs["prepayment_date"] = payload.effective_date
        if payload.strategy in ("reduce_tenure", "reduce_emi"):
            kwargs["prepayment_strategy"] = payload.strategy
    elif payload.kind == "extra_monthly_payment":
        kwargs["extra_monthly_payment"] = payload.amount
    elif payload.kind == "rate_change":
        kwargs["rate_change"] = payload.annual_rate
        kwargs["rate_change_date"] = payload.effective_date
        if payload.strategy in ("keep_emi", "keep_tenure"):
            kwargs["rate_change_strategy"] = payload.strategy

    res = simulate_loan(baseline, **kwargs)

    return LoanSimulateOut(
        current_total_interest=round_money(res.original_total_interest),
        current_emi=round_money(res.original_emi),
        current_tenure_months=res.original_tenure,
        current_end_date=res.original_end_date,
        simulated_total_interest=round_money(res.simulated_total_interest),
        simulated_emi=round_money(res.simulated_emi),
        simulated_tenure_months=res.simulated_tenure,
        simulated_end_date=res.simulated_end_date,
        interest_saved=round_money(res.interest_saved),
        tenure_months_saved=res.original_tenure - res.simulated_tenure,
    )
