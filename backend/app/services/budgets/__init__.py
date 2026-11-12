"""Monthly budgets, category roll-ups, alerts and copy forward (spec: budgets)."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.errors import ConflictError, NotFoundError, ValidationAppError
from app.core.money import ZERO, round_money
from app.models.budget import Budget, BudgetAlert, BudgetLine
from app.repositories import aggregates
from app.repositories.base import OwnedRepository
from app.schemas.budget import (
    BudgetAlertResponse,
    BudgetComparisonResponse,
    BudgetLineResponse,
    BudgetMonthComparisonItem,
    BudgetResponse,
    SetBudgetRequest,
)
from app.services import audit
from app.services.calculations import (
    budget_remaining,
    budget_utilization,
    total_expenses,
)
from app.services.calculations.periods import month_end, month_label, trailing_months
from app.services.categories import CategoryRepository


class BudgetRepository(OwnedRepository[Budget]):
    model = Budget
    entity_name = "Budget"


def parse_month(month_str: str) -> date:
    """Parse 'YYYY-MM' or 'YYYY-MM-DD' into date(YYYY, MM, 1)."""
    parts = month_str.split("-")
    if len(parts) < 2:
        raise ValidationAppError("Invalid month format, expected YYYY-MM", code="invalid_month")
    try:
        y, m = int(parts[0]), int(parts[1])
        return date(y, m, 1)
    except ValueError as exc:
        raise ValidationAppError(
            "Invalid month format, expected YYYY-MM", code="invalid_month"
        ) from exc


def _get_category_actuals(
    db: Session, user_id: uuid.UUID, start: date, end: date
) -> dict[uuid.UUID, Decimal]:
    """Calculate net expense actuals per category for a period.

    Includes roll-up of subcategories into top-level parent.
    """
    rows = aggregates.expense_net_by_category(db, user_id, start, end)
    # rows is list of (top_level_id, category_id, net_amount)
    actuals: dict[uuid.UUID, Decimal] = {}
    for top_id, cat_id, amt in rows:
        # direct subcategory actual
        actuals[cat_id] = actuals.get(cat_id, ZERO) + amt
        # top-level parent roll-up
        if top_id != cat_id:
            actuals[top_id] = actuals.get(top_id, ZERO) + amt
    return actuals


def _format_budget_response(
    db: Session,
    budget: Budget,
    warning: str | None = None,
) -> BudgetResponse:
    user_id = budget.user_id
    start = budget.month
    end = month_end(start.year, start.month)

    # Calculate overall actuals
    by_type = aggregates.totals_by_type(db, user_id, start, end)
    overall_actual = round_money(total_expenses(by_type))

    overall_util = None
    overall_rem = None
    overall_over = False
    if budget.overall_amount is not None and budget.overall_amount > ZERO:
        overall_util = budget_utilization(overall_actual, budget.overall_amount)
        overall_rem = budget_remaining(budget.overall_amount, overall_actual)
        overall_over = overall_actual > budget.overall_amount

    # Calculate category actuals
    cat_actuals = _get_category_actuals(db, user_id, start, end)
    cats_by_id = aggregates.categories_by_id(db, user_id)

    line_responses: list[BudgetLineResponse] = []
    cat_budget_sum = ZERO

    # Reload lines with category info
    lines = db.scalars(
        select(BudgetLine).where(BudgetLine.budget_id == budget.id).order_by(BudgetLine.created_at)
    ).all()

    for line in lines:
        cat_budget_sum += line.amount
        cat = cats_by_id.get(line.category_id)
        cat_name = cat.name if cat else "Unknown"
        parent_id = cat.parent_id if cat else None

        actual = round_money(cat_actuals.get(line.category_id, ZERO))
        util = budget_utilization(actual, line.amount)
        rem = budget_remaining(line.amount, actual)
        is_over = actual > line.amount

        line_responses.append(
            BudgetLineResponse(
                id=line.id,
                category_id=line.category_id,
                category_name=cat_name,
                parent_id=parent_id,
                amount=line.amount,
                alert_thresholds=line.alert_thresholds,
                actual=actual,
                utilization=util,
                remaining=rem,
                is_over_budget=is_over,
            )
        )

    # Check warning if not already set
    if (
        warning is None
        and budget.overall_amount is not None
        and cat_budget_sum > budget.overall_amount
    ):
        warning = "Category budgets exceed overall budget"

    return BudgetResponse(
        id=budget.id,
        month=f"{budget.month.year:04d}-{budget.month.month:02d}",
        overall_amount=budget.overall_amount,
        overall_actual=overall_actual,
        overall_utilization=overall_util,
        overall_remaining=overall_rem,
        overall_is_over_budget=overall_over,
        lines=line_responses,
        warning=warning,
    )


def get_budget(db: Session, user_id: uuid.UUID, month_str: str) -> BudgetResponse:
    month = parse_month(month_str)
    budget = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == month)
    ).one_or_none()
    if budget is None:
        raise NotFoundError("Budget")
    return _format_budget_response(db, budget)


def set_budget(
    db: Session, user_id: uuid.UUID, month_str: str, req: SetBudgetRequest
) -> BudgetResponse:
    month = parse_month(month_str)
    budget = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == month)
    ).one_or_none()

    action: audit.AuditAction = "update"
    if budget is None:
        budget = Budget(user_id=user_id, month=month, overall_amount=req.overall_amount)
        db.add(budget)
        db.flush()
        action = "create"
    else:
        budget.overall_amount = req.overall_amount

    # Clear existing lines and replace
    db.execute(delete(BudgetLine).where(BudgetLine.budget_id == budget.id))
    db.flush()

    cat_budget_sum = ZERO
    cat_repo = CategoryRepository(db, user_id)
    for line_in in req.lines:
        cat = cat_repo.get_or_404(line_in.category_id)
        cat_budget_sum += line_in.amount
        db.add(
            BudgetLine(
                budget_id=budget.id,
                category_id=cat.id,
                amount=line_in.amount,
                alert_thresholds=line_in.alert_thresholds,
            )
        )
    db.flush()

    warning = None
    if req.overall_amount is not None and cat_budget_sum > req.overall_amount:
        warning = "Category budgets exceed overall budget"

    audit.record(
        db,
        actor_user_id=user_id,
        action=action,
        entity_type="budget",
        entity_id=budget.id,
        changed_fields=["overall_amount", "lines"],
    )

    evaluate_budget_alerts(db, user_id, month)
    db.commit()
    return _format_budget_response(db, budget, warning)


def copy_budget(
    db: Session, user_id: uuid.UUID, target_month_str: str, source_month_str: str
) -> BudgetResponse:
    target_month = parse_month(target_month_str)
    source_month = parse_month(source_month_str)

    existing = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == target_month)
    ).one_or_none()
    if existing is not None:
        raise ConflictError("Budget already exists for target month")

    source = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == source_month)
    ).one_or_none()
    if source is None:
        raise NotFoundError("Source budget")

    target_budget = Budget(
        user_id=user_id, month=target_month, overall_amount=source.overall_amount
    )
    db.add(target_budget)
    db.flush()

    source_lines = db.scalars(
        select(BudgetLine).where(BudgetLine.budget_id == source.id)
    ).all()
    for s_line in source_lines:
        db.add(
            BudgetLine(
                budget_id=target_budget.id,
                category_id=s_line.category_id,
                amount=s_line.amount,
                alert_thresholds=s_line.alert_thresholds,
            )
        )
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="budget",
        entity_id=target_budget.id,
        changed_fields=["copied_from"],
    )

    evaluate_budget_alerts(db, user_id, target_month)
    db.commit()
    return _format_budget_response(db, target_budget)


def get_budget_comparison(
    db: Session,
    user_id: uuid.UUID,
    category_id: uuid.UUID | None = None,
    months_count: int = 6,
) -> BudgetComparisonResponse:
    today = date.today()
    trailing = trailing_months(today, months_count)
    items: list[BudgetMonthComparisonItem] = []

    cat_name = None
    if category_id is not None:
        cat = CategoryRepository(db, user_id).get_or_404(category_id)
        cat_name = cat.name

    for yr, mo in trailing:
        m_start = date(yr, mo, 1)
        m_end = month_end(yr, mo)
        m_str = f"{yr:04d}-{mo:02d}"
        lbl = month_label(yr, mo)

        budget = db.scalars(
            select(Budget).where(Budget.user_id == user_id, Budget.month == m_start)
        ).one_or_none()

        budget_amt = None
        if category_id is None:
            # Overall
            if budget and budget.overall_amount is not None:
                budget_amt = budget.overall_amount
            by_type = aggregates.totals_by_type(db, user_id, m_start, m_end)
            actual = round_money(total_expenses(by_type))
        else:
            # Specific category
            if budget:
                line = db.scalars(
                    select(BudgetLine).where(
                        BudgetLine.budget_id == budget.id,
                        BudgetLine.category_id == category_id,
                    )
                ).one_or_none()
                if line:
                    budget_amt = line.amount
            actuals = _get_category_actuals(db, user_id, m_start, m_end)
            actual = round_money(actuals.get(category_id, ZERO))

        util = None
        rem = None
        is_over = False
        if budget_amt is not None and budget_amt > ZERO:
            util = budget_utilization(actual, budget_amt)
            rem = budget_remaining(budget_amt, actual)
            is_over = actual > budget_amt

        items.append(
            BudgetMonthComparisonItem(
                month=m_str,
                month_label=lbl,
                budget=budget_amt,
                actual=actual,
                utilization=util,
                remaining=rem,
                is_over_budget=is_over,
            )
        )

    return BudgetComparisonResponse(
        category_id=category_id,
        category_name=cat_name,
        months=items,
    )


def evaluate_budget_alerts(db: Session, user_id: uuid.UUID, month: date) -> list[BudgetAlert]:
    """Evaluate budget alert thresholds for month and record any triggered alerts."""
    budget = db.scalars(
        select(Budget).where(Budget.user_id == user_id, Budget.month == month)
    ).one_or_none()
    if budget is None:
        return []

    start = month
    end = month_end(start.year, start.month)
    created_alerts: list[BudgetAlert] = []

    # 1. Overall alerts
    if budget.overall_amount is not None and budget.overall_amount > ZERO:
        by_type = aggregates.totals_by_type(db, user_id, start, end)
        overall_actual = total_expenses(by_type)
        overall_util = budget_utilization(overall_actual, budget.overall_amount)
        for th in (80, 100):
            if overall_util >= th:
                existing = db.scalars(
                    select(BudgetAlert).where(
                        BudgetAlert.user_id == user_id,
                        BudgetAlert.budget_line_id.is_(None),
                        BudgetAlert.month == month,
                        BudgetAlert.threshold == th,
                    )
                ).one_or_none()
                if not existing:
                    alert = BudgetAlert(
                        user_id=user_id,
                        budget_line_id=None,
                        month=month,
                        threshold=th,
                    )
                    db.add(alert)
                    created_alerts.append(alert)

    # 2. Line alerts
    cat_actuals = _get_category_actuals(db, user_id, start, end)
    lines = db.scalars(select(BudgetLine).where(BudgetLine.budget_id == budget.id)).all()
    for line in lines:
        if line.amount > ZERO:
            actual = cat_actuals.get(line.category_id, ZERO)
            util = budget_utilization(actual, line.amount)
            for th in line.alert_thresholds:
                if util >= th:
                    existing = db.scalars(
                        select(BudgetAlert).where(
                            BudgetAlert.user_id == user_id,
                            BudgetAlert.budget_line_id == line.id,
                            BudgetAlert.month == month,
                            BudgetAlert.threshold == th,
                        )
                    ).one_or_none()
                    if not existing:
                        alert = BudgetAlert(
                            user_id=user_id,
                            budget_line_id=line.id,
                            month=month,
                            threshold=th,
                        )
                        db.add(alert)
                        created_alerts.append(alert)

    db.flush()
    return created_alerts


def list_budget_alerts(
    db: Session, user_id: uuid.UUID, month_str: str | None = None
) -> list[BudgetAlertResponse]:
    stmt = select(BudgetAlert).where(BudgetAlert.user_id == user_id)
    if month_str:
        month = parse_month(month_str)
        stmt = stmt.where(BudgetAlert.month == month)
    stmt = stmt.order_by(BudgetAlert.triggered_at.desc())
    alerts = db.scalars(stmt).all()

    cats_by_id = aggregates.categories_by_id(db, user_id)
    responses: list[BudgetAlertResponse] = []
    for a in alerts:
        cat_id = None
        cat_name = None
        if a.budget_line:
            cat_id = a.budget_line.category_id
            cat = cats_by_id.get(cat_id)
            if cat:
                cat_name = cat.name
        responses.append(
            BudgetAlertResponse(
                id=a.id,
                month=f"{a.month.year:04d}-{a.month.month:02d}",
                budget_line_id=a.budget_line_id,
                category_id=cat_id,
                category_name=cat_name,
                threshold=a.threshold,
                triggered_at=a.triggered_at,
            )
        )
    return responses
