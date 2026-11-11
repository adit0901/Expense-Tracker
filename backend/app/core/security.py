"""Password hashing (Argon2id), JWT access tokens and opaque token helpers."""

from __future__ import annotations

import hashlib
import secrets
import uuid
from datetime import UTC, datetime, timedelta
from functools import lru_cache
from pathlib import Path

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import get_settings
from app.core.errors import AuthError, ValidationAppError

MIN_PASSWORD_LENGTH = 10
_COMMON_PASSWORDS_FILE = Path(__file__).with_name("common_passwords.txt")


@lru_cache
def _hasher() -> PasswordHasher:
    if get_settings().app_env == "test":
        return PasswordHasher(time_cost=1, memory_cost=8 * 1024, parallelism=1)
    return PasswordHasher()  # Argon2id with library defaults


def hash_password(password: str) -> str:
    return _hasher().hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _hasher().verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


# A valid hash used to equalize timing when the email does not exist.
@lru_cache
def dummy_hash() -> str:
    return hash_password(secrets.token_urlsafe(16))


@lru_cache
def common_passwords() -> frozenset[str]:
    lines = _COMMON_PASSWORDS_FILE.read_text(encoding="utf-8").splitlines()
    return frozenset(x.strip().lower() for x in lines if x.strip() and not x.startswith("#"))


def validate_password_policy(password: str, field: str = "password") -> None:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValidationAppError(
            f"Password must be at least {MIN_PASSWORD_LENGTH} characters long",
            code="weak_password",
            details=[{"field": field, "message": "too_short"}],
        )
    if password.lower() in common_passwords():
        raise ValidationAppError(
            "Password is too common; choose a less predictable password",
            code="weak_password",
            details=[{"field": field, "message": "too_common"}],
        )


def create_access_token(user_id: uuid.UUID) -> tuple[str, int]:
    settings = get_settings()
    ttl = settings.access_token_ttl_minutes * 60
    now = datetime.now(UTC)
    payload = {
        "sub": str(user_id),
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(seconds=ttl)).timestamp()),
        "jti": uuid.uuid4().hex,
        "typ": "access",
    }
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, ttl


def decode_access_token(token: str) -> uuid.UUID:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options={"require": ["sub", "exp", "jti"]},
        )
        if payload.get("typ") != "access":
            raise AuthError("Invalid access token")
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, ValueError) as exc:
        raise AuthError("Invalid or expired access token") from exc


def generate_opaque_token() -> str:
    """256-bit random token, URL-safe."""
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
