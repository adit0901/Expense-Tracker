"""Receipt download/delete (owner only)."""

from __future__ import annotations

import uuid
from typing import Annotated
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response, status

from app.api.deps import CurrentUser, DbSession
from app.integrations.storage import StorageBackend, get_storage
from app.services import attachments as svc

router = APIRouter(prefix="/attachments", tags=["attachments"])


@router.get("/{attachment_id}", response_class=Response)
def download_attachment(
    attachment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> Response:
    att = svc.get_attachment(db, user.id, attachment_id)
    return Response(
        content=storage.read(att.storage_key),
        media_type=att.mime_type,
        headers={
            "Content-Disposition": f"attachment; filename*=UTF-8''{quote(att.original_name)}",
            "Cache-Control": "private, no-store",
        },
    )


@router.delete("/{attachment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_attachment(
    attachment_id: uuid.UUID,
    user: CurrentUser,
    db: DbSession,
    storage: Annotated[StorageBackend, Depends(get_storage)],
) -> Response:
    svc.delete_attachment(db, user.id, attachment_id, storage)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
