from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.integrations.email import InMemoryEmailSender
from app.models.user import PasswordResetToken, RefreshToken, User
from tests.helpers import DEFAULT_PASSWORD, AuthedUser, data

REG = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"


def _register(client: TestClient, email: str, password: str = DEFAULT_PASSWORD) -> Any:
    return client.post(REG, json={"full_name": "Asha Rao", "email": email, "password": password})


# ---- registration (3.2) ------------------------------------------------------------------


def test_register_success_has_defaults_and_no_secret(client: TestClient, db: Session) -> None:
    resp = _register(client, "asha@example.com")
    assert resp.status_code == 201
    body = resp.json()["data"]
    assert body["email"] == "asha@example.com" and body["full_name"] == "Asha Rao"
    assert "password" not in resp.text and "hash" not in resp.text
    user = db.scalars(select(User).where(User.email == "asha@example.com")).one()
    assert user.password_hash.startswith("$argon2id$")
    assert user.preferences.currency == "INR"


def test_register_duplicate_email_case_insensitive(client: TestClient) -> None:
    assert _register(client, "asha@example.com").status_code == 201
    resp = _register(client, "Asha@Example.com")
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "email_taken"


def test_register_weak_password(client: TestClient) -> None:
    resp = _register(client, "weak@example.com", "password123")
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "weak_password" and "common" in err["message"].lower()
    short = _register(client, "short@example.com", "Ab1!xyz")
    assert short.status_code == 422 and "10 characters" in short.json()["error"]["message"]


# ---- login / refresh / logout (3.3) -----------------------------------------------------


def test_login_returns_access_token_and_refresh_cookie(client: TestClient) -> None:
    _register(client, "login@example.com")
    resp = client.post(LOGIN, json={"email": "LOGIN@example.com", "password": DEFAULT_PASSWORD})
    assert resp.status_code == 200
    body = resp.json()["data"]
    assert body["token_type"] == "bearer" and body["expires_in"] == 900
    cookie = resp.headers["set-cookie"]
    for attr in ("fintrack_refresh=", "HttpOnly", "Secure", "SameSite=strict", "Path=/api/v1/auth"):
        assert attr.lower() in cookie.lower()
    me = client.get("/api/v1/users/me", headers={"Authorization": f"Bearer {body['access_token']}"})
    assert me.status_code == 200 and me.json()["data"]["email"] == "login@example.com"


def test_invalid_credentials_identical_for_unknown_email_and_wrong_password(
    client: TestClient,
) -> None:
    _register(client, "known@example.com")
    wrong = client.post(LOGIN, json={"email": "known@example.com", "password": "Wrong-pass-123"})
    unknown = client.post(LOGIN, json={"email": "nobody@example.com", "password": "Wrong-pass-1"})
    assert wrong.status_code == unknown.status_code == 401
    w, u = wrong.json()["error"], unknown.json()["error"]
    assert w["code"] == u["code"] == "invalid_credentials"
    assert w["message"] == u["message"]


def test_refresh_rotates_and_old_token_stops_working(user: AuthedUser) -> None:
    old = user.client.cookies.get("fintrack_refresh")
    r1 = user.post("/api/v1/auth/refresh")
    assert r1.status_code == 200 and r1.json()["data"]["access_token"]
    new = user.client.cookies.get("fintrack_refresh")
    assert new and new != old
    # Presenting the old (rotated) token fails.
    user.client.cookies.clear()
    replay = user.client.post("/api/v1/auth/refresh", cookies={"fintrack_refresh": old})
    assert replay.status_code == 401


def test_refresh_reuse_revokes_family(user: AuthedUser, db: Session) -> None:
    old = user.client.cookies.get("fintrack_refresh")
    assert user.post("/api/v1/auth/refresh").status_code == 200
    current = user.client.cookies.get("fintrack_refresh")
    user.client.cookies.clear()
    reuse = user.client.post("/api/v1/auth/refresh", cookies={"fintrack_refresh": old})
    assert reuse.status_code == 401
    active = db.scalars(
        select(RefreshToken).where(
            RefreshToken.user_id == user.id, RefreshToken.revoked_at.is_(None)
        )
    ).all()
    assert active == []
    after = user.client.post("/api/v1/auth/refresh", cookies={"fintrack_refresh": current})
    assert after.status_code == 401


def test_refresh_without_cookie(client: TestClient) -> None:
    assert client.post("/api/v1/auth/refresh").status_code == 401


def test_logout_revokes_refresh_token(user: AuthedUser) -> None:
    token = user.client.cookies.get("fintrack_refresh")
    resp = user.post("/api/v1/auth/logout")
    assert resp.status_code == 204
    user.client.cookies.clear()
    again = user.client.post("/api/v1/auth/refresh", cookies={"fintrack_refresh": token})
    assert again.status_code == 401


def test_protected_endpoint_requires_token(client: TestClient) -> None:
    resp = client.get("/api/v1/users/me")
    assert resp.status_code == 401
    assert resp.json()["error"]["code"] == "not_authenticated"
    bad = client.get("/api/v1/users/me", headers={"Authorization": "Bearer not-a-jwt"})
    assert bad.status_code == 401


# ---- rate limiting (3.4) ------------------------------------------------------------------


def test_sixth_failed_login_is_rate_limited(client: TestClient) -> None:
    _register(client, "brute@example.com")
    for _ in range(5):
        r = client.post(LOGIN, json={"email": "brute@example.com", "password": "Nope-nope-123"})
        assert r.status_code == 401
    sixth = client.post(LOGIN, json={"email": "brute@example.com", "password": "Nope-nope-123"})
    assert sixth.status_code == 429
    assert int(sixth.headers["Retry-After"]) > 0
    assert sixth.json()["error"]["code"] == "rate_limited"
    # Even the right password is blocked during the window.
    right = client.post(LOGIN, json={"email": "brute@example.com", "password": DEFAULT_PASSWORD})
    assert right.status_code == 429


def test_failed_logins_limited_per_ip_across_emails(client: TestClient) -> None:
    for i in range(5):
        client.post(LOGIN, json={"email": f"x{i}@example.com", "password": "Nope-nope-123"})
    r = client.post(LOGIN, json={"email": "y@example.com", "password": "Nope-nope-123"})
    assert r.status_code == 429 and "Retry-After" in r.headers


# ---- password reset (3.5) -----------------------------------------------------------------


def _reset_token_from(outbox: InMemoryEmailSender) -> str:
    body = outbox.outbox[-1].body
    return body.split("token=")[1].split()[0]


def test_reset_request_unknown_email_same_response(
    client: TestClient, outbox: InMemoryEmailSender
) -> None:
    _register(client, "reset@example.com")
    known = client.post("/api/v1/auth/password-reset/request", json={"email": "reset@example.com"})
    unknown = client.post(
        "/api/v1/auth/password-reset/request", json={"email": "ghost@example.com"}
    )
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(outbox.outbox) == 1 and outbox.outbox[0].to == "reset@example.com"


def test_reset_success_consumes_token_and_signs_out(
    user: AuthedUser, client: TestClient, outbox: InMemoryEmailSender, db: Session
) -> None:
    client.post("/api/v1/auth/password-reset/request", json={"email": user.email})
    token = _reset_token_from(outbox)
    stored = db.scalars(select(PasswordResetToken.token_hash)).all()
    assert token not in stored  # only hashes are stored
    new_pw = "Brand-New-Secret-77"
    resp = client.post(
        "/api/v1/auth/password-reset/confirm", json={"token": token, "new_password": new_pw}
    )
    assert resp.status_code == 200
    reuse = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "Another-Secret-88"},
    )
    assert reuse.status_code == 400 and reuse.json()["error"]["code"] == "reset_token_invalid"
    # Existing sessions are signed out.
    assert user.post("/api/v1/auth/refresh").status_code == 401
    assert client.post(LOGIN, json={"email": user.email, "password": new_pw}).status_code == 200
    assert (
        client.post(LOGIN, json={"email": user.email, "password": user.password}).status_code == 401
    )


def test_reset_expired_token(
    user: AuthedUser, client: TestClient, outbox: InMemoryEmailSender, db: Session
) -> None:
    client.post("/api/v1/auth/password-reset/request", json={"email": user.email})
    token = _reset_token_from(outbox)
    db.execute(
        update(PasswordResetToken).values(
            expires_at=datetime.now(UTC) - timedelta(minutes=1),
            created_at=datetime.now(UTC) - timedelta(minutes=31),
        )
    )
    db.commit()
    resp = client.post(
        "/api/v1/auth/password-reset/confirm",
        json={"token": token, "new_password": "Brand-New-Secret-77"},
    )
    assert resp.status_code == 400
    assert resp.json()["error"]["code"] == "reset_token_invalid"


def test_reset_token_ttl_is_30_minutes(
    user: AuthedUser, client: TestClient, outbox: InMemoryEmailSender, db: Session
) -> None:
    client.post("/api/v1/auth/password-reset/request", json={"email": user.email})
    t = db.scalars(select(PasswordResetToken)).one()
    assert t.expires_at - t.created_at == timedelta(minutes=30)


# ---- change password (3.6) ----------------------------------------------------------------


def test_change_password_wrong_current(user: AuthedUser, client: TestClient) -> None:
    resp = user.post(
        "/api/v1/auth/password/change",
        json={"current_password": "Wrong-current-1", "new_password": "New-Secret-123"},
    )
    assert resp.status_code == 400
    assert (
        client.post(LOGIN, json={"email": user.email, "password": user.password}).status_code == 200
    )


def test_change_password_revokes_other_sessions(
    user: AuthedUser, make_user: Any, client: TestClient
) -> None:
    other_session = TestClient(user.client.app, base_url="https://testserver")
    assert (
        other_session.post(LOGIN, json={"email": user.email, "password": user.password}).status_code
        == 200
    )
    resp = user.post(
        "/api/v1/auth/password/change",
        json={"current_password": user.password, "new_password": "New-Secret-123"},
    )
    assert data(resp)["message"]
    assert other_session.post("/api/v1/auth/refresh").status_code == 401
    assert user.post("/api/v1/auth/refresh").status_code == 200  # current session kept
