"""Current-user profile, preferences and account deletion."""

from __future__ import annotations

from fastapi import APIRouter, Response, status

from app.api.deps import CurrentUser, DbSession
from app.api.v1.auth import _clear_refresh_cookie
from app.core.responses import Envelope, ok
from app.schemas.users import (
    DeleteAccountIn,
    PreferencesOut,
    PreferencesUpdate,
    ProfileUpdate,
    UserOut,
)
from app.services import users as users_service

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me")
def get_me(user: CurrentUser) -> Envelope[UserOut]:
    return ok(UserOut.model_validate(user))


@router.patch("/me")
def update_me(body: ProfileUpdate, user: CurrentUser, db: DbSession) -> Envelope[UserOut]:
    return ok(UserOut.model_validate(users_service.update_profile(db, user, body)))


@router.delete("/me", status_code=status.HTTP_204_NO_CONTENT)
def delete_me(body: DeleteAccountIn, user: CurrentUser, db: DbSession) -> Response:
    users_service.delete_account(db, user, body.password)
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_refresh_cookie(response)
    return response


@router.get("/me/preferences")
def get_preferences(user: CurrentUser, db: DbSession) -> Envelope[PreferencesOut]:
    return ok(PreferencesOut.model_validate(users_service.get_preferences(db, user)))


@router.patch("/me/preferences")
def update_preferences(
    body: PreferencesUpdate, user: CurrentUser, db: DbSession
) -> Envelope[PreferencesOut]:
    prefs = users_service.update_preferences(db, user, body)
    return ok(PreferencesOut.model_validate(prefs))
