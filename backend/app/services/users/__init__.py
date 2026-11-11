"""User profile, preferences and account deletion."""

from __future__ import annotations

from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import structlog
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.core.errors import AppError, ConflictError, ValidationAppError
from app.core.money import SUPPORTED_CURRENCIES
from app.core.security import verify_password
from app.models.user import User, UserPreferences
from app.schemas.users import PreferencesUpdate, ProfileUpdate
from app.services import audit
from app.services.users.deletion import run_deletion_hooks

log = structlog.get_logger("app.users")


def update_profile(db: Session, user: User, data: ProfileUpdate) -> User:
    if data.full_name is not None:
        user.full_name = data.full_name.strip()
    if data.email is not None and data.email.lower() != user.email.lower():
        if not data.current_password:
            raise ValidationAppError(
                "Current password is required to change email",
                code="current_password_required",
                details=[{"field": "current_password", "message": "required"}],
            )
        if not verify_password(user.password_hash, data.current_password):
            raise AppError(
                "Current password is incorrect",
                code="invalid_current_password",
                details=[{"field": "current_password", "message": "incorrect"}],
            )
        if db.scalar(select(User.id).where(User.email == data.email, User.id != user.id)):
            raise ConflictError("An account with this email already exists", code="email_taken")
        user.email = data.email
    db.commit()
    return user


def get_preferences(db: Session, user: User) -> UserPreferences:
    prefs = db.scalar(select(UserPreferences).where(UserPreferences.user_id == user.id))
    if prefs is None:  # defensive: every user gets preferences at registration
        prefs = UserPreferences(user_id=user.id)
        db.add(prefs)
        db.commit()
    return prefs


def update_preferences(db: Session, user: User, data: PreferencesUpdate) -> UserPreferences:
    prefs = get_preferences(db, user)
    changes = data.model_dump(exclude_unset=True, exclude_none=True)
    if "currency" in changes:
        currency = str(changes["currency"]).upper()
        if currency not in SUPPORTED_CURRENCIES:
            raise ValidationAppError(
                "Only INR is supported as the reporting currency",
                code="unsupported_currency",
                details=[{"field": "currency", "message": "unsupported"}],
            )
        changes["currency"] = currency
    if "timezone" in changes:
        try:
            ZoneInfo(str(changes["timezone"]))
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValidationAppError(
                "Unknown time zone", details=[{"field": "timezone", "message": "unknown"}]
            ) from exc
    for key, value in changes.items():
        setattr(prefs, key, value)
    db.commit()
    return prefs


def delete_account(db: Session, user: User, password: str) -> None:
    if not verify_password(user.password_hash, password):
        raise AppError(
            "Password is incorrect",
            code="invalid_password",
            details=[{"field": "password", "message": "incorrect"}],
        )
    user_id = user.id
    post_commit = run_deletion_hooks(db, user_id)
    # Retain audit history in anonymized form (owner-privileged function; app role can't UPDATE).
    db.execute(text("SELECT anonymize_audit_actor(:uid)"), {"uid": user_id})
    audit.record(db, actor_user_id=None, action="delete", entity_type="user", entity_id=None)
    db.delete(user)  # ON DELETE CASCADE removes all user-owned rows
    db.commit()
    for action in post_commit:
        try:
            action()
        except Exception as exc:  # file cleanup must not resurrect the account
            log.error("post_delete_cleanup_failed", error=type(exc).__name__)
    log.info("account_deleted")
