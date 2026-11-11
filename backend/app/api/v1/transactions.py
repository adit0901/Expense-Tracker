"""Transactions endpoints: CRUD, search, duplicate check, CSV export, receipts."""

from __future__ import annotations

import uuid
from datetime import date
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, File, Header, Query, Response, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, DbSession
from app.core.pagination import PageParams, page_params
from app.core.responses import Envelope, ok
from app.integrations.storage import StorageBackend, get_storage
from app.models.enums import PaymentMethod, TransactionType
from app.schemas.transactions import (
    AttachmentOut,
    DuplicateCheckOut,
    TransactionCreate,
    TransactionFilters,
    TransactionOut,
    TransactionPage,
    TransactionUpdate,
)
from app.services import attachments as att_service
from app.services import transactions as svc
from app.services.transactions import idempotency
from app.services.transactions.csv_export import transactions_csv

router = APIRouter(prefix="/transactions", tags=["transactions"])

IdempotencyHeader = Annotated[str | None, Header(alias="Idempotency-Key", max_length=100)]


def transaction_filters(
    date_from: date | None = None,
    date_to: date | None = None,
    type: Annotated[list[TransactionType] | None, Query()] = None,
    account_id: uuid.UUID | None = None,
    category_id: uuid.UUID | None = None,
    payment_method: PaymentMethod | None = None,
    amount_min: Annotated[Decimal | None, Query(ge=0)] = None,
    amount_max: Annotated[Decimal | None, Query(ge=0)] = None,
    tag: Annotated[str | None, Query(max_length=40)] = None,
    q: Annotated[str | None, Query(max_length=100)] = None,
    income_source_id: uuid.UUID | None = None,
    import_batch_id: uuid.UUID | None = None,
) -> TransactionFilters:
    return TransactionFilters(
        date_from=date_from,
        date_to=date_to,
        types=type,
        account_id=account_id,
        category_id=category_id,
        payment_method=payment_method,
        amount_min=amount_min,
        amount_max=amount_max,
        tag=tag,
        q=q,
        income_source_id=income_source_id,
        import_batch_id=import_batch_id,
    )


Filters = Annotated[TransactionFilters, Depends(transaction_filters)]


@router.get("", response_model=TransactionPage)
def list_transactions(
    user: CurrentUser,
    db: DbSession,
    filters: Filters,
    params: Annotated[PageParams, Depends(page_params)],
    sort: str | None = None,
) -> TransactionPage:
    items, meta = svc.list_transactions(db, user.id, filters, params, sort)
    return TransactionPage(data=items, meta=meta)


@router.get("/export.csv", response_class=Response)
def export_csv(
    user: CurrentUser, db: DbSession, filters: Filters, sort: str | None = None
) -> Response:
    rows, lookup = svc.iter_filtered(db, user.id, filters, sort)
    body = transactions_csv(svc.to_out(t, lookup) for t in rows)
    return Response(
        content=body.encode("utf-8"),
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="transactions.csv"'},
    )


@router.post("/duplicate-check")
def duplicate_check(
    body: TransactionCreate, user: CurrentUser, db: DbSession
) -> Envelope[DuplicateCheckOut]:
    return ok(svc.duplicate_check(db, user.id, body))


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope[TransactionOut])
def create_transaction(
    body: TransactionCreate,
    user: CurrentUser,
    db: DbSession,
    idempotency_key: IdempotencyHeader = None,
) -> Any:
    endpoint = "POST /transactions"
    body_hash = idempotency.request_hash(body.model_dump(mode="json"))
    if idempotency_key:
        cached = idempotency.lookup(db, user.id, idempotency_key, endpoint, body_hash)
        if cached is not None:
            return JSONResponse(
                cached.response_body,
                status_code=cached.response_status,
                headers={"Idempotent-Replayed": "true"},
            )
    payload = ok(svc.create_transaction(db, user.id, body)).model_dump(mode="json")
    if idempotency_key:
        idempotency.store(db, user.id, idempotency_key, endpoint, body_hash, 201, payload)
    return JSONResponse(payload, status_code=201)


@router.get("/{txn_id}")
def get_transaction(
    txn_id: uuid.UUID, user: CurrentUser, db: DbSession
) -> Envelope[TransactionOut]:
    return ok(svc.get_transaction(db, user.id, txn_id))


@router.patch("/{txn_id}")
def update_transaction(
    txn_id: uuid.UUID, body: TransactionUpdate, user: CurrentUser, db: DbSession
) -> Envelope[TransactionOut]:
    return ok(svc.update_transaction(db, user.id, txn_id, body))


@router.delete("/{txn_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_transaction(txn_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Response:
    svc.delete_transaction(db, user.id, txn_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{txn_id}/attachments", status_code=status.HTTP_201_CREATED)
async def upload_attachment(
    txn_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    storage: Annotated[StorageBackend, Depends(get_storage)],
    file: Annotated[UploadFile, File()],
) -> Envelope[AttachmentOut]:
    data = await file.read(att_service.MAX_BYTES + 1)
    if len(data) > att_service.MAX_BYTES:
        raise att_service.too_large()
    att = att_service.add_attachment(db, user.id, txn_id, file.filename, data, storage)
    return ok(
        AttachmentOut(
            id=att.id,
            original_name=att.original_name,
            mime_type=att.mime_type,
            size_bytes=att.size_bytes,
            created_at=att.created_at,
        )
    )
