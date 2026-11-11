"""HTTP middleware: request id + access log, security headers."""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import FastAPI, Request, Response

from app.core.request_context import set_request_id

access_log = structlog.get_logger("app.access")
_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._-]{8,64}$")

API_CSP = "default-src 'none'; frame-ancestors 'none'"


def _route_template(request: Request) -> str:
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    return str(path) if path else "unmatched"


def install_middleware(app: FastAPI, *, hsts: bool = True) -> None:
    @app.middleware("http")
    async def security_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if hsts:
            response.headers.setdefault(
                "Strict-Transport-Security", "max-age=31536000; includeSubDomains"
            )
        if not request.url.path.startswith("/api/docs"):
            response.headers.setdefault("Content-Security-Policy", API_CSP)
        return response

    @app.middleware("http")
    async def request_context(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        incoming = request.headers.get("X-Request-ID", "")
        request_id = incoming if _REQUEST_ID_RE.match(incoming) else uuid.uuid4().hex
        request.state.request_id = request_id
        request.state.user_id = None
        set_request_id(request_id)
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(request_id=request_id)
        start = time.perf_counter()
        status = 500
        try:
            response = await call_next(request)
            status = response.status_code
            response.headers["X-Request-ID"] = request_id
            return response
        finally:
            user_id = getattr(request.state, "user_id", None)
            access_log.info(
                "request",
                method=request.method,
                route=_route_template(request),
                status=status,
                duration_ms=round((time.perf_counter() - start) * 1000, 2),
                user_id=str(user_id) if user_id else None,
            )
