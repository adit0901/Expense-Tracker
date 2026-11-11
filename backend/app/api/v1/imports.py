"""CSV import endpoints: upload -> preview, confirm, undo."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Header, UploadFile, status
from fastapi.responses import JSONResponse

from app.api.deps import CurrentUser, DbSession
from app.core.errors import AppError, ValidationAppError
from app.core.responses import Envelope, ok
from app.schemas.imports import ImportBatchOut, ImportConfirmIn
from app.services import imports as svc
from app.services.transactions import idempotency

router = APIRouter(prefix="/imports", tags=["imports"])
MAX_BYTES = 10 * 1024 * 1024


@router.post("", status_code=status.HTTP_201_CREATED, response_model=Envelope[ImportBatchOut])
async def upload_import(
    user: CurrentUser,
    db: DbSession,
    file: Annotated[UploadFile, File()],
    account_id: Annotated[uuid.UUID, Form()],
    date_format: Annotated[str, Form()] = "DD/MM/YYYY",
    column_mapping: Annotated[str | None, Form(description="JSON object")] = None,
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key", max_length=100)] = None,
) -> Any:
    data = await file.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise AppError("File exceeds the 10 MB limit", code="file_too_large", status_code=413)
    mapping: dict[str, Any] | None = None
    if column_mapping:
        try:
            parsed = json.loads(column_mapping)
        except json.JSONDecodeError as exc:
            raise ValidationAppError(
                "column_mapping must be a JSON object",
                details=[{"field": "column_mapping", "message": "invalid_json"}],
            ) from exc
        if not isinstance(parsed, dict):
            raise ValidationAppError(
                "column_mapping must be a JSON object",
                details=[{"field": "column_mapping", "message": "invalid"}],
            )
        mapping = parsed
    endpoint = "POST /imports"
    body_hash = hashlib.sha256(
        data + f"|{account_id}|{date_format}|{column_mapping}".encode()
    ).hexdigest()
    if idempotency_key:
        cached = idempotency.lookup(db, user.id, idempotency_key, endpoint, body_hash)
        if cached is not None:
            return JSONResponse(cached.response_body, status_code=cached.response_status)
    batch = svc.create_import(
        db,
        user.id,
        file_name=file.filename or "import.csv",
        data=data,
        account_id=account_id,
        date_format=date_format,
        mapping=mapping,
    )
    payload = ok(batch).model_dump(mode="json")
    if idempotency_key:
        idempotency.store(db, user.id, idempotency_key, endpoint, body_hash, 201, payload)
    return JSONResponse(payload, status_code=201)


@router.get("/{batch_id}")
def get_import(batch_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Envelope[ImportBatchOut]:
    return ok(svc.get_import(db, user.id, batch_id))


@router.post("/{batch_id}/confirm")
def confirm_import(
    batch_id: uuid.UUID, user: CurrentUser, db: DbSession, body: ImportConfirmIn | None = None
) -> Envelope[ImportBatchOut]:
    return ok(svc.confirm_import(db, user.id, batch_id, body.selected_rows if body else None))


@router.post("/{batch_id}/undo")
def undo_import(batch_id: uuid.UUID, user: CurrentUser, db: DbSession) -> Envelope[ImportBatchOut]:
    return ok(svc.undo_import(db, user.id, batch_id))
