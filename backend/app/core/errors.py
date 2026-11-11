"""Domain errors and their mapping to the error envelope."""

from __future__ import annotations

from typing import Any

import structlog
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.request_context import get_request_id

log = structlog.get_logger("app.errors")


class AppError(Exception):
    """An expected, client-visible error with a stable machine code."""

    status_code = 400
    code = "bad_request"

    def __init__(
        self,
        message: str,
        *,
        code: str | None = None,
        status_code: int | None = None,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        if code is not None:
            self.code = code
        if status_code is not None:
            self.status_code = status_code
        self.details = details or []
        self.headers = headers


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"

    def __init__(self, entity: str = "Resource") -> None:
        super().__init__(f"{entity} not found")


class ConflictError(AppError):
    status_code = 409
    code = "conflict"


class ValidationAppError(AppError):
    """Business-rule validation failure reported as 422."""

    status_code = 422
    code = "validation_error"


class AuthError(AppError):
    status_code = 401
    code = "not_authenticated"


_HTTP_CODES = {
    400: "bad_request",
    401: "not_authenticated",
    403: "forbidden",
    404: "not_found",
    405: "method_not_allowed",
    413: "payload_too_large",
    429: "rate_limited",
}


def error_body(
    code: str,
    message: str,
    details: list[dict[str, Any]] | None = None,
    request_id: str | None = None,
) -> dict[str, Any]:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or [],
            "request_id": request_id or get_request_id(),
        }
    }


def _field_from_loc(loc: tuple[Any, ...]) -> str:
    parts = [str(p) for p in loc if p not in ("body", "query", "path", "header", "cookie")]
    return ".".join(parts) if parts else str(loc[-1]) if loc else ""


async def _app_error_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, AppError)
    return JSONResponse(
        error_body(exc.code, exc.message, exc.details),
        status_code=exc.status_code,
        headers=exc.headers,
    )


async def _validation_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)
    details = [
        {
            "field": _field_from_loc(tuple(e.get("loc", ()))),
            "message": e.get("msg", ""),
            "type": e.get("type", ""),
        }
        for e in exc.errors()
    ]
    return JSONResponse(
        error_body("validation_error", "Request validation failed", details), status_code=422
    )


async def _http_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, StarletteHTTPException)
    code = _HTTP_CODES.get(exc.status_code, "http_error")
    message = exc.detail if isinstance(exc.detail, str) else "Request failed"
    return JSONResponse(error_body(code, message), status_code=exc.status_code, headers=exc.headers)


async def _unhandled_handler(request: Request, exc: Exception) -> JSONResponse:
    request_id = getattr(request.state, "request_id", None)
    log.error("unhandled_exception", exc_type=type(exc).__name__, request_id=request_id)
    headers = {"X-Request-ID": request_id} if request_id else None
    return JSONResponse(
        error_body("internal_error", "An unexpected error occurred", request_id=request_id),
        status_code=500,
        headers=headers,
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(AppError, _app_error_handler)
    app.add_exception_handler(RequestValidationError, _validation_handler)
    app.add_exception_handler(StarletteHTTPException, _http_handler)
    app.add_exception_handler(Exception, _unhandled_handler)
