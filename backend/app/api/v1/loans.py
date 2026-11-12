"""Loans and EMIs endpoints."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from app.api.deps import CurrentUser, DbSession
from app.core.responses import Envelope, ok
from app.models.enums import LoanStatus
from app.schemas.loan import (
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
from app.services import loans as svc

router = APIRouter(tags=["loans-and-emi"])


@router.get("/loans")
def list_loans(
    user: CurrentUser,
    db: DbSession,
    status: Annotated[LoanStatus | None, Query()] = None,
) -> Envelope[list[LoanOut]]:
    return ok(svc.list_loans(db, user.id, status=status))


@router.get("/loans/summary")
def get_loans_summary(
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanSummaryOut]:
    return ok(svc.get_loans_summary(db, user.id))


@router.post("/loans", status_code=status.HTTP_201_CREATED)
def create_loan(
    body: LoanCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanOut]:
    return ok(svc.create_loan(db, user.id, body))


@router.get("/loans/{id}")
def get_loan(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanOut]:
    return ok(svc.get_loan(db, user.id, id))


@router.patch("/loans/{id}")
def update_loan(
    id: uuid.UUID,
    body: LoanUpdate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanOut]:
    return ok(svc.update_loan(db, user.id, id, body))


@router.delete("/loans/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_loan(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> None:
    svc.delete_loan(db, user.id, id)


@router.get("/loans/{id}/schedule")
def get_loan_schedule(
    id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanScheduleOut]:
    return ok(svc.get_loan_schedule(db, user.id, id))


@router.post("/loans/{id}/payments", status_code=status.HTTP_201_CREATED)
def record_payment(
    id: uuid.UUID,
    body: LoanPaymentCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanPaymentOut]:
    return ok(svc.record_payment(db, user.id, id, body))


@router.post("/loans/{id}/events", status_code=status.HTTP_201_CREATED)
def add_loan_event(
    id: uuid.UUID,
    body: LoanEventCreate,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanEventOut]:
    return ok(svc.add_loan_event(db, user.id, id, body))


@router.post("/loans/{id}/simulate")
def simulate(
    id: uuid.UUID,
    body: LoanSimulateRequest,
    user: CurrentUser,
    db: DbSession,
) -> Envelope[LoanSimulateOut]:
    return ok(svc.simulate(db, user.id, id, body))

