"""Authentication endpoints."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, Request, Response, status

from app.api.deps import CurrentUser, DbSession
from app.core.config import get_settings
from app.core.rate_limit import FailedLoginLimiter, client_ip, get_login_limiter
from app.core.responses import Envelope, ok
from app.integrations.email import EmailSender, OutgoingEmail, get_email_sender
from app.schemas.auth import (
    ChangePasswordIn,
    LoginIn,
    MessageOut,
    PasswordResetConfirmIn,
    PasswordResetRequestIn,
    RegisterIn,
    TokenOut,
)
from app.schemas.users import UserOut
from app.services import auth as auth_service
from app.services.auth import IssuedTokens

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_COOKIE = "fintrack_refresh"
REFRESH_COOKIE_PATH = "/api/v1/auth"
RESET_REQUESTED_MESSAGE = "If an account exists for that email, a reset link has been sent."

RefreshCookie = Annotated[str | None, Cookie(alias=REFRESH_COOKIE)]


def _set_refresh_cookie(response: Response, raw: str) -> None:
    response.set_cookie(
        REFRESH_COOKIE,
        raw,
        max_age=get_settings().refresh_token_ttl_days * 86400,
        httponly=True,
        secure=True,
        samesite="strict",
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        REFRESH_COOKIE, path=REFRESH_COOKIE_PATH, secure=True, httponly=True, samesite="strict"
    )


def _token_response(response: Response, tokens: IssuedTokens) -> Envelope[TokenOut]:
    _set_refresh_cookie(response, tokens.refresh_token)
    return ok(
        TokenOut(
            access_token=tokens.access_token,
            expires_in=tokens.expires_in,
            user=UserOut.model_validate(tokens.user),
        )
    )


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(body: RegisterIn, db: DbSession) -> Envelope[UserOut]:
    user = auth_service.register(
        db, full_name=body.full_name, email=str(body.email), password=body.password
    )
    return ok(UserOut.model_validate(user))


@router.post("/login")
def login(
    body: LoginIn,
    request: Request,
    response: Response,
    db: DbSession,
    limiter: Annotated[FailedLoginLimiter, Depends(get_login_limiter)],
) -> Envelope[TokenOut]:
    tokens = auth_service.login(
        db, email=str(body.email), password=body.password, ip=client_ip(request), limiter=limiter
    )
    return _token_response(response, tokens)


@router.post("/refresh")
def refresh(
    response: Response, db: DbSession, fintrack_refresh: RefreshCookie = None
) -> Envelope[TokenOut]:
    try:
        tokens = auth_service.refresh(db, fintrack_refresh)
    except Exception:
        _clear_refresh_cookie(response)
        raise
    return _token_response(response, tokens)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response, user: CurrentUser, db: DbSession, fintrack_refresh: RefreshCookie = None
) -> Response:
    auth_service.logout(db, user, fintrack_refresh)
    response.status_code = status.HTTP_204_NO_CONTENT
    _clear_refresh_cookie(response)
    return response


@router.post("/password-reset/request", status_code=status.HTTP_202_ACCEPTED)
def password_reset_request(
    body: PasswordResetRequestIn,
    db: DbSession,
    background: BackgroundTasks,
    sender: Annotated[EmailSender, Depends(get_email_sender)],
) -> Envelope[MessageOut]:
    result = auth_service.request_password_reset(db, str(body.email))
    if result is not None:
        user, raw = result
        link = f"{get_settings().frontend_base_url}/reset-password?token={raw}"
        message = OutgoingEmail(
            to=user.email,
            subject="Reset your FinTrack password",
            body=(
                f"Hi {user.full_name},\n\nUse this link within 30 minutes to reset your "
                f"FinTrack password:\n\n{link}\n\nIf you did not request this, ignore this email."
            ),
        )
        background.add_task(sender.send, message)
    return ok(MessageOut(message=RESET_REQUESTED_MESSAGE))


@router.post("/password-reset/confirm")
def password_reset_confirm(body: PasswordResetConfirmIn, db: DbSession) -> Envelope[MessageOut]:
    auth_service.confirm_password_reset(db, body.token, body.new_password)
    return ok(MessageOut(message="Password updated. Please sign in."))


@router.post("/password/change")
def change_password(
    body: ChangePasswordIn,
    user: CurrentUser,
    db: DbSession,
    fintrack_refresh: RefreshCookie = None,
) -> Envelope[MessageOut]:
    auth_service.change_password(
        db,
        user,
        current_password=body.current_password,
        new_password=body.new_password,
        refresh_raw=fintrack_refresh,
    )
    return ok(MessageOut(message="Password changed. Other sessions were signed out."))
