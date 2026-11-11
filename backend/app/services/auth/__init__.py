"""Authentication: registration, login, refresh rotation, logout, password reset/change."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import structlog
from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError, AuthError, ConflictError
from app.core.rate_limit import FailedLoginLimiter
from app.core.security import (
    create_access_token,
    dummy_hash,
    generate_opaque_token,
    hash_password,
    hash_token,
    validate_password_policy,
    verify_password,
)
from app.models.user import PasswordResetToken, RefreshToken, User, UserPreferences
from app.services.users.registration import run_registration_hooks

log = structlog.get_logger("app.auth")


@dataclass(frozen=True)
class IssuedTokens:
    user: User
    access_token: str
    expires_in: int
    refresh_token: str


def _now() -> datetime:
    return datetime.now(UTC)


def _normalize_email(email: str) -> str:
    return email.strip()


def register(db: Session, *, full_name: str, email: str, password: str) -> User:
    validate_password_policy(password)
    email = _normalize_email(email)
    if db.scalar(select(User.id).where(User.email == email)) is not None:
        raise ConflictError("An account with this email already exists", code="email_taken")
    user = User(email=email, full_name=full_name.strip(), password_hash=hash_password(password))
    user.preferences = UserPreferences()
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ConflictError(
            "An account with this email already exists", code="email_taken"
        ) from exc
    run_registration_hooks(db, user)
    db.commit()
    log.info("user_registered", user_id=str(user.id))
    return user


def _issue_refresh(
    db: Session, user_id: uuid.UUID, family_id: uuid.UUID
) -> tuple[str, RefreshToken]:
    raw = generate_opaque_token()
    now = _now()
    token = RefreshToken(
        user_id=user_id,
        token_hash=hash_token(raw),
        family_id=family_id,
        created_at=now,
        expires_at=now + timedelta(days=get_settings().refresh_token_ttl_days),
    )
    db.add(token)
    db.flush()
    return raw, token


def _issue_session(db: Session, user: User, family_id: uuid.UUID | None = None) -> IssuedTokens:
    raw, _ = _issue_refresh(db, user.id, family_id or uuid.uuid4())
    access, ttl = create_access_token(user.id)
    return IssuedTokens(user=user, access_token=access, expires_in=ttl, refresh_token=raw)


def login(
    db: Session, *, email: str, password: str, ip: str, limiter: FailedLoginLimiter
) -> IssuedTokens:
    email = _normalize_email(email)
    keys = (f"ip:{ip}", f"email:{email.lower()}")
    limiter.check(*keys)
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        verify_password(dummy_hash(), password)  # equalize timing
        ok = False
    else:
        ok = (
            user.is_active
            and user.deleted_at is None
            and verify_password(user.password_hash, password)
        )
    if not ok or user is None:
        limiter.record_failure(*keys)
        log.info("login_failed")
        raise AuthError("Invalid email or password", code="invalid_credentials")
    limiter.reset(keys[1])
    tokens = _issue_session(db, user)
    db.commit()
    log.info("login_succeeded", user_id=str(user.id))
    return tokens


def _revoke_family(db: Session, family_id: uuid.UUID) -> None:
    db.execute(
        update(RefreshToken)
        .where(RefreshToken.family_id == family_id, RefreshToken.revoked_at.is_(None))
        .values(revoked_at=_now())
    )


def _revoke_all_for_user(
    db: Session, user_id: uuid.UUID, *, except_family: uuid.UUID | None = None
) -> None:
    stmt = update(RefreshToken).where(
        RefreshToken.user_id == user_id, RefreshToken.revoked_at.is_(None)
    )
    if except_family is not None:
        stmt = stmt.where(RefreshToken.family_id != except_family)
    db.execute(stmt.values(revoked_at=_now()))


def _find_refresh(db: Session, raw: str | None, *, lock: bool = False) -> RefreshToken | None:
    if not raw:
        return None
    stmt = select(RefreshToken).where(RefreshToken.token_hash == hash_token(raw))
    if lock:
        stmt = stmt.with_for_update()
    return db.scalar(stmt)


def refresh(db: Session, raw: str | None) -> IssuedTokens:
    token = _find_refresh(db, raw, lock=True)
    if token is None:
        raise AuthError("Invalid refresh token", code="invalid_refresh_token")
    if token.revoked_at is not None:
        # Reuse of a rotated/revoked token: assume theft and kill the whole session family.
        _revoke_family(db, token.family_id)
        db.commit()
        log.warning("refresh_token_reuse", user_id=str(token.user_id))
        raise AuthError("Invalid refresh token", code="invalid_refresh_token")
    if token.expires_at <= _now():
        raise AuthError("Refresh token expired", code="invalid_refresh_token")
    user = db.get(User, token.user_id)
    if user is None or not user.is_active:
        raise AuthError("Invalid refresh token", code="invalid_refresh_token")
    new_raw, new_token = _issue_refresh(db, user.id, token.family_id)
    token.revoked_at = _now()
    token.replaced_by = new_token.id
    access, ttl = create_access_token(user.id)
    db.commit()
    return IssuedTokens(user=user, access_token=access, expires_in=ttl, refresh_token=new_raw)


def logout(db: Session, user: User, raw: str | None) -> None:
    token = _find_refresh(db, raw)
    if token is not None and token.user_id == user.id and token.revoked_at is None:
        token.revoked_at = _now()
        db.commit()
    log.info("logout", user_id=str(user.id))


def request_password_reset(db: Session, email: str) -> tuple[User, str] | None:
    """Create a reset token for an existing user. Returns None (silently) for unknown emails."""
    user = db.scalar(select(User).where(User.email == _normalize_email(email)))
    if user is None or not user.is_active:
        return None
    raw = generate_opaque_token()
    now = _now()
    db.add(
        PasswordResetToken(
            user_id=user.id,
            token_hash=hash_token(raw),
            created_at=now,
            expires_at=now + timedelta(minutes=get_settings().password_reset_ttl_minutes),
        )
    )
    db.commit()
    return user, raw


def confirm_password_reset(db: Session, raw: str, new_password: str) -> None:
    token = db.scalar(
        select(PasswordResetToken)
        .where(PasswordResetToken.token_hash == hash_token(raw))
        .with_for_update()
    )
    if token is None or token.used_at is not None or token.expires_at <= _now():
        raise AppError("Reset link is invalid or has expired", code="reset_token_invalid")
    validate_password_policy(new_password, field="new_password")
    user = db.get(User, token.user_id)
    if user is None:
        raise AppError("Reset link is invalid or has expired", code="reset_token_invalid")
    user.password_hash = hash_password(new_password)
    token.used_at = _now()
    _revoke_all_for_user(db, user.id)
    db.commit()
    log.info("password_reset_completed", user_id=str(user.id))


def change_password(
    db: Session, user: User, *, current_password: str, new_password: str, refresh_raw: str | None
) -> None:
    if not verify_password(user.password_hash, current_password):
        raise AppError(
            "Current password is incorrect",
            code="invalid_current_password",
            details=[{"field": "current_password", "message": "incorrect"}],
        )
    validate_password_policy(new_password, field="new_password")
    current = _find_refresh(db, refresh_raw)
    keep = current.family_id if current is not None and current.user_id == user.id else None
    user.password_hash = hash_password(new_password)
    _revoke_all_for_user(db, user.id, except_family=keep)
    db.commit()
    log.info("password_changed", user_id=str(user.id))
