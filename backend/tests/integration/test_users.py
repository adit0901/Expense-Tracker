from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.user import RefreshToken, User, UserPreferences
from app.services import audit
from tests.helpers import AuthedUser, data

ME = "/api/v1/users/me"
PREFS = "/api/v1/users/me/preferences"


def test_update_name(user: AuthedUser) -> None:
    assert data(user.patch(ME, json={"full_name": "Asha R."}))["full_name"] == "Asha R."
    assert data(user.get(ME))["full_name"] == "Asha R."


def test_email_change_requires_password(user: AuthedUser) -> None:
    resp = user.patch(ME, json={"email": "new@example.com"})
    assert resp.status_code == 422
    assert data(user.get(ME))["email"] == user.email
    wrong = user.patch(ME, json={"email": "new@example.com", "current_password": "Wrong-pass-1"})
    assert wrong.status_code == 400
    ok = user.patch(ME, json={"email": "new@example.com", "current_password": user.password})
    assert data(ok)["email"] == "new@example.com"


def test_email_change_to_taken_email(user: AuthedUser, other_user: AuthedUser) -> None:
    resp = user.patch(
        ME, json={"email": other_user.email.upper(), "current_password": user.password}
    )
    assert resp.status_code == 409


def test_default_preferences(user: AuthedUser) -> None:
    assert data(user.get(PREFS)) == {
        "currency": "INR",
        "theme": "system",
        "locale": "en-IN",
        "date_format": "DD/MM/YYYY",
        "number_grouping": "indian",
        "week_start": "monday",
        "timezone": "Asia/Kolkata",
    }


def test_update_preferences(user: AuthedUser) -> None:
    out = data(user.patch(PREFS, json={"theme": "dark", "number_grouping": "international"}))
    assert out["theme"] == "dark" and out["number_grouping"] == "international"
    assert data(user.get(PREFS))["theme"] == "dark"


def test_unsupported_currency(user: AuthedUser) -> None:
    resp = user.patch(PREFS, json={"currency": "EUR"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "unsupported_currency"
    assert data(user.patch(PREFS, json={"currency": "inr"}))["currency"] == "INR"


def test_invalid_theme_and_timezone(user: AuthedUser) -> None:
    assert user.patch(PREFS, json={"theme": "neon"}).status_code == 422
    assert user.patch(PREFS, json={"timezone": "Mars/Base"}).status_code == 422


# ---- account deletion (3.7) ---------------------------------------------------------------


def test_delete_account_wrong_password(user: AuthedUser) -> None:
    resp = user.delete(ME, json={"password": "Wrong-pass-12"})
    assert resp.status_code == 400
    assert user.get(ME).status_code == 200


def test_delete_account_removes_everything(
    user: AuthedUser, client: TestClient, db: Session
) -> None:
    audit.record(
        db, actor_user_id=user.id, action="create", entity_type="account", entity_id=user.id
    )
    db.commit()
    resp = user.delete(ME, json={"password": user.password})
    assert resp.status_code == 204
    # Can no longer log in or use the old token.
    login = client.post("/api/v1/auth/login", json={"email": user.email, "password": user.password})
    assert login.status_code == 401
    assert user.get(ME).status_code == 401
    # No user-owned rows remain.
    assert db.get(User, user.id) is None
    assert db.scalars(select(UserPreferences).where(UserPreferences.user_id == user.id)).all() == []
    assert db.scalars(select(RefreshToken).where(RefreshToken.user_id == user.id)).all() == []
    # Audit entries retained but anonymized.
    assert db.scalars(select(AuditLog).where(AuditLog.actor_user_id == user.id)).all() == []
    assert db.scalars(select(AuditLog).where(AuditLog.entity_type == "account")).all()
