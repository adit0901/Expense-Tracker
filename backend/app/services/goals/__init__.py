from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError, ValidationAppError
from app.core.money import ZERO, round_money
from app.models.enums import (
    GoalContributionKind,
    GoalStatus,
    TransactionStatus,
    TransactionType,
)
from app.models.goal import Goal, GoalContribution, SavingsTarget
from app.models.transaction import Transaction
from app.repositories import aggregates
from app.repositories.base import OwnedRepository
from app.schemas.goal import (
    GoalContributionCreate,
    GoalContributionOut,
    GoalCreate,
    GoalOut,
    GoalUpdate,
    SavingsTargetIn,
    SavingsTargetOut,
)
from app.services import audit
from app.services.calculations.periods import add_months, month_end
from app.services.calculations.planning import (
    goal_estimated_completion_date,
    goal_progress_pct,
    goal_remaining,
    goal_required_monthly_contribution,
    savings_target_achievement,
)


class GoalRepository(OwnedRepository[Goal]):
    model = Goal
    entity_name = "Goal"


def parse_month_string(val: str | None) -> tuple[int, int, date, date, str]:
    if val is None:
        today = date.today()
        y, m = today.year, today.month
    else:
        parts = val.split("-")
        y, m = int(parts[0]), int(parts[1])
    month_str = f"{y:04d}-{m:02d}"
    start_date = date(y, m, 1)
    end_date = month_end(y, m)
    return y, m, start_date, end_date, month_str


def get_savings_target(
    db: Session, user_id: uuid.UUID, month_str: str | None = None
) -> SavingsTargetOut:
    _y, _m, start_date, end_date, formatted_month = parse_month_string(month_str)

    # Find the target effective for this month (latest effective_from <= end_date)
    target = db.scalar(
        select(SavingsTarget)
        .where(SavingsTarget.user_id == user_id, SavingsTarget.effective_from <= end_date)
        .order_by(SavingsTarget.effective_from.desc())
        .limit(1)
    )
    if not target:
        raise NotFoundError("Savings target")

    # Compute actual savings for this month: Income - Net Expenses
    totals = aggregates.totals_by_type(db, user_id, start_date, end_date)
    income = totals.get(TransactionType.income, ZERO)
    expense = totals.get(TransactionType.expense, ZERO)
    refund = totals.get(TransactionType.refund, ZERO)

    loan_interest = db.scalar(
        select(func.coalesce(func.sum(Transaction.interest_component), ZERO)).where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.posted,
            Transaction.type == TransactionType.loan_payment,
            Transaction.txn_date >= start_date,
            Transaction.txn_date <= end_date,
        )
    ) or ZERO

    net_expense = expense - refund + loan_interest
    actual_savings = income - net_expense

    achievement_pct, shortfall = savings_target_achievement(actual_savings, target.amount)
    is_achieved = actual_savings >= target.amount

    return SavingsTargetOut(
        id=target.id,
        month=formatted_month,
        effective_from=target.effective_from,
        target_amount=round_money(target.amount),
        actual_savings=round_money(actual_savings),
        achievement_pct=achievement_pct,
        shortfall=shortfall,
        is_achieved=is_achieved,
    )


def set_savings_target(
    db: Session, user_id: uuid.UUID, effective_from_str: str, payload: SavingsTargetIn
) -> SavingsTargetOut:
    effective_from_str = effective_from_str.strip()
    if len(effective_from_str) == 7 and effective_from_str[4] == "-":
        y, m = int(effective_from_str[:4]), int(effective_from_str[5:7])
        effective_from = date(y, m, 1)
    else:
        effective_from = date.fromisoformat(effective_from_str)

    target = db.scalar(
        select(SavingsTarget).where(
            SavingsTarget.user_id == user_id,
            SavingsTarget.effective_from == effective_from,
        )
    )
    before = {"amount": str(target.amount)} if target else None
    if target:
        target.amount = payload.amount
    else:
        target = SavingsTarget(
            user_id=user_id,
            effective_from=effective_from,
            amount=payload.amount,
        )
        db.add(target)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="update" if before else "create",
        entity_type="savings_target",
        entity_id=target.id,
        changed_fields=["amount", "effective_from"],
    )
    db.commit()

    month_str = f"{effective_from.year:04d}-{effective_from.month:02d}"
    return get_savings_target(db, user_id, month_str)


def _compute_goal_out(db: Session, goal: Goal, as_of: date) -> GoalOut:
    contributions = db.scalars(
        select(GoalContribution)
        .where(GoalContribution.goal_id == goal.id)
        .order_by(GoalContribution.date.asc(), GoalContribution.created_at.asc())
    ).all()

    total_contrib = sum(
        (c.amount for c in contributions if c.kind == GoalContributionKind.contribution),
        ZERO,
    )
    total_withdr = sum(
        (c.amount for c in contributions if c.kind == GoalContributionKind.withdrawal),
        ZERO,
    )
    current_amount = round_money(goal.starting_amount + total_contrib - total_withdr)
    progress_pct = goal_progress_pct(goal.target_amount, current_amount)
    remaining_amount = goal_remaining(goal.target_amount, current_amount)
    is_achieved = remaining_amount == ZERO
    is_overdue = (
        goal.target_date is not None
        and as_of > goal.target_date
        and not is_achieved
    )

    req_monthly = (
        None
        if is_overdue
        else goal_required_monthly_contribution(remaining_amount, goal.target_date, as_of)
    )

    # 3-month average net contribution
    # Start of 3 months prior to as_of
    y_start, m_start = add_months(as_of.year, as_of.month, -3)
    start_3m = date(y_start, m_start, 1)

    contrib_3m = sum(
        (
            c.amount
            for c in contributions
            if c.kind == GoalContributionKind.contribution and start_3m <= c.date <= as_of
        ),
        ZERO,
    )
    withdr_3m = sum(
        (
            c.amount
            for c in contributions
            if c.kind == GoalContributionKind.withdrawal and start_3m <= c.date <= as_of
        ),
        ZERO,
    )
    avg_3m = round_money((contrib_3m - withdr_3m) / Decimal(3))

    est_date = goal_estimated_completion_date(remaining_amount, avg_3m, as_of)
    if is_achieved:
        est_label = "Achieved"
    elif est_date is not None:
        est_label = f"{est_date.isoformat()} (estimate)"
    else:
        est_label = "Cannot estimate"

    return GoalOut(
        id=goal.id,
        name=goal.name,
        type=goal.type,
        target_amount=round_money(goal.target_amount),
        target_date=goal.target_date,
        starting_amount=round_money(goal.starting_amount),
        status=goal.status,
        notes=goal.notes,
        current_amount=current_amount,
        progress_pct=progress_pct,
        remaining_amount=remaining_amount,
        required_monthly_contribution=req_monthly,
        estimated_completion_date=est_date,
        estimated_completion_label=est_label,
        is_overdue=is_overdue,
        is_achieved=is_achieved,
        created_at=goal.created_at,
        updated_at=goal.updated_at,
    )


def create_goal(db: Session, user_id: uuid.UUID, payload: GoalCreate) -> GoalOut:
    goal = Goal(
        user_id=user_id,
        name=payload.name,
        type=payload.type,
        target_amount=payload.target_amount,
        target_date=payload.target_date,
        starting_amount=payload.starting_amount,
        notes=payload.notes,
    )
    db.add(goal)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="goal",
        entity_id=goal.id,
        changed_fields=["name", "type", "target_amount"],
    )
    db.commit()
    return _compute_goal_out(db, goal, as_of=date.today())


def get_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> GoalOut:
    goal = GoalRepository(db, user_id).get_or_404(goal_id)
    return _compute_goal_out(db, goal, as_of=date.today())


def list_goals(
    db: Session, user_id: uuid.UUID, status: GoalStatus | None = None
) -> list[GoalOut]:
    stmt = select(Goal).where(Goal.user_id == user_id)
    if status is not None:
        stmt = stmt.where(Goal.status == status)
    stmt = stmt.order_by(Goal.created_at.desc())
    goals = db.scalars(stmt).all()
    today = date.today()
    return [_compute_goal_out(db, g, as_of=today) for g in goals]


def update_goal(
    db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, payload: GoalUpdate
) -> GoalOut:
    goal = GoalRepository(db, user_id).get_or_404(goal_id)

    if payload.name is not None:
        goal.name = payload.name
    if payload.type is not None:
        goal.type = payload.type
    if payload.target_amount is not None:
        goal.target_amount = payload.target_amount
    if payload.target_date is not None or "target_date" in payload.model_fields_set:
        goal.target_date = payload.target_date
    if payload.status is not None:
        goal.status = payload.status
    if payload.notes is not None or "notes" in payload.model_fields_set:
        goal.notes = payload.notes

    db.flush()
    audit.record(
        db,
        actor_user_id=user_id,
        action="update",
        entity_type="goal",
        entity_id=goal.id,
        changed_fields=["name", "type", "target_amount", "status"],
    )
    db.commit()
    return _compute_goal_out(db, goal, as_of=date.today())


def delete_goal(db: Session, user_id: uuid.UUID, goal_id: uuid.UUID) -> None:
    goal = GoalRepository(db, user_id).get_or_404(goal_id)
    db.delete(goal)
    db.flush()
    audit.record(
        db,
        actor_user_id=user_id,
        action="delete",
        entity_type="goal",
        entity_id=goal_id,
    )
    db.commit()


def add_contribution(
    db: Session,
    user_id: uuid.UUID,
    goal_id: uuid.UUID,
    payload: GoalContributionCreate,
) -> GoalContributionOut:
    goal = GoalRepository(db, user_id).get_or_404(goal_id)

    # If withdrawal, ensure current amount is sufficient
    if payload.kind == GoalContributionKind.withdrawal:
        contributions = db.scalars(
            select(GoalContribution).where(GoalContribution.goal_id == goal.id)
        ).all()
        total_contrib = sum(
            (c.amount for c in contributions if c.kind == GoalContributionKind.contribution),
            ZERO,
        )
        total_withdr = sum(
            (c.amount for c in contributions if c.kind == GoalContributionKind.withdrawal),
            ZERO,
        )
        current_amount = goal.starting_amount + total_contrib - total_withdr
        if payload.amount > current_amount:
            raise ValidationAppError(
                "Withdrawal amount exceeds current goal balance",
                code="insufficient_goal_balance",
                details=[{"field": "amount", "message": "Withdrawal exceeds current balance"}],
            )

    contrib = GoalContribution(
        goal_id=goal.id,
        kind=payload.kind,
        amount=payload.amount,
        date=payload.date,
        transaction_id=payload.transaction_id,
        notes=payload.notes,
    )
    db.add(contrib)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="goal_contribution",
        entity_id=contrib.id,
        changed_fields=["goal_id", "kind", "amount", "date"],
    )
    db.commit()

    return GoalContributionOut(
        id=contrib.id,
        goal_id=contrib.goal_id,
        kind=contrib.kind,
        amount=round_money(contrib.amount),
        date=contrib.date,
        transaction_id=contrib.transaction_id,
        notes=contrib.notes,
        created_at=contrib.created_at,
    )


def list_contributions(
    db: Session, user_id: uuid.UUID, goal_id: uuid.UUID
) -> list[GoalContributionOut]:
    goal = GoalRepository(db, user_id).get_or_404(goal_id)
    contribs = db.scalars(
        select(GoalContribution)
        .where(GoalContribution.goal_id == goal.id)
        .order_by(GoalContribution.date.desc(), GoalContribution.created_at.desc())
    ).all()
    return [
        GoalContributionOut(
            id=c.id,
            goal_id=c.goal_id,
            kind=c.kind,
            amount=round_money(c.amount),
            date=c.date,
            transaction_id=c.transaction_id,
            notes=c.notes,
            created_at=c.created_at,
        )
        for c in contribs
    ]


def delete_contribution(
    db: Session, user_id: uuid.UUID, goal_id: uuid.UUID, contribution_id: uuid.UUID
) -> None:
    goal = GoalRepository(db, user_id).get_or_404(goal_id)
    contrib = db.scalar(
        select(GoalContribution).where(
            GoalContribution.id == contribution_id, GoalContribution.goal_id == goal.id
        )
    )
    if not contrib:
        raise NotFoundError("Goal contribution")

    db.delete(contrib)
    db.flush()
    audit.record(
        db,
        actor_user_id=user_id,
        action="delete",
        entity_type="goal_contribution",
        entity_id=contribution_id,
    )
    db.commit()
