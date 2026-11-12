"""Savings targets and financial goals endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.responses import Envelope, ok
from app.models.enums import GoalContributionKind, GoalStatus
from app.schemas.goal import (
    GoalContributionCreate,
    GoalContributionOut,
    GoalCreate,
    GoalOut,
    GoalUpdate,
    SavingsTargetIn,
    SavingsTargetOut,
)
from app.services import goals as svc

router = APIRouter(tags=["savings-and-goals"])


# --- Savings Targets ---


@router.get("/savings-targets")
def get_savings_target(
    user: CurrentUser,
    db: DbSession,
    month: Annotated[str | None, Query(description="Month in YYYY-MM format")] = None,
) -> Envelope[SavingsTargetOut]:
    return ok(svc.get_savings_target(db, user.id, month))


@router.put("/savings-targets/{effective_from}")
def set_savings_target(
    effective_from: str,
    body: SavingsTargetIn,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[SavingsTargetOut]:
    return ok(svc.set_savings_target(db, user.id, effective_from, body))


# --- Goals ---


@router.get("/goals")
def list_goals(
    user: CurrentUser,
    db: DbSession,
    status: Annotated[GoalStatus | None, Query()] = None,
) -> Envelope[list[GoalOut]]:
    return ok(svc.list_goals(db, user.id, status))


@router.post("/goals", status_code=status.HTTP_201_CREATED)
def create_goal(
    body: GoalCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[GoalOut]:
    return ok(svc.create_goal(db, user.id, body))


@router.get("/goals/{id}")
def get_goal(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[GoalOut]:
    return ok(svc.get_goal(db, user.id, id))


@router.patch("/goals/{id}")
def update_goal(
    id: uuid.UUID,
    body: GoalUpdate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[GoalOut]:
    return ok(svc.update_goal(db, user.id, id, body))


@router.delete("/goals/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_goal(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    svc.delete_goal(db, user.id, id)


# --- Goal Contributions ---


@router.get("/goals/{id}/contributions")
def list_contributions(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[list[GoalContributionOut]]:
    return ok(svc.list_contributions(db, user.id, id))


@router.post("/goals/{id}/contributions", status_code=status.HTTP_201_CREATED)
def add_contribution(
    id: uuid.UUID,
    body: GoalContributionCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[GoalContributionOut]:
    return ok(svc.add_contribution(db, user.id, id, body))


@router.post("/goals/{id}/withdrawals", status_code=status.HTTP_201_CREATED)
def add_withdrawal(
    id: uuid.UUID,
    body: GoalContributionCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[GoalContributionOut]:
    body.kind = GoalContributionKind.withdrawal
    return ok(svc.add_contribution(db, user.id, id, body))


@router.delete(
    "/goals/{id}/contributions/{contribution_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_contribution(
    id: uuid.UUID,
    contribution_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    svc.delete_contribution(db, user.id, id, contribution_id)

