"""Rate limiting: failed-login limiter (per IP and per email) and per-user API limits."""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.errors import AppError, error_body


class FailedLoginLimiter:
    """Sliding-window counter of failed logins. In-memory (single API instance in P0)."""

    def __init__(self, max_failures: int, window_seconds: int) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque[float]:
        q = self._events[key]
        while q and q[0] <= now - self.window:
            q.popleft()
        return q

    def check(self, *keys: str) -> None:
        """Raise 429 if any key has reached the failure limit within the window."""
        now = time.monotonic()
        with self._lock:
            retry_after = 0.0
            for key in keys:
                q = self._prune(key, now)
                if len(q) >= self.max_failures:
                    retry_after = max(retry_after, q[0] + self.window - now)
        if retry_after > 0:
            seconds = str(max(1, math.ceil(retry_after)))
            raise AppError(
                "Too many failed login attempts. Try again later.",
                code="rate_limited",
                status_code=429,
                headers={"Retry-After": seconds},
            )

    def record_failure(self, *keys: str) -> None:
        now = time.monotonic()
        with self._lock:
            for key in keys:
                self._prune(key, now).append(now)

    def reset(self, *keys: str) -> None:
        with self._lock:
            for key in keys:
                self._events.pop(key, None)

    def clear(self) -> None:
        with self._lock:
            self._events.clear()


def client_ip(request: Request) -> str:
    return get_remote_address(request) or "unknown"


def _user_or_ip_key(request: Request) -> str:
    from app.core.security import decode_access_token

    auth = request.headers.get("Authorization", "")
    if auth.lower().startswith("bearer "):
        try:
            return f"user:{decode_access_token(auth[7:])}"
        except AppError:
            pass
    return f"ip:{client_ip(request)}"


async def _rate_limit_handler(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RateLimitExceeded)
    return JSONResponse(
        error_body("rate_limited", "Too many requests. Try again later."),
        status_code=429,
        headers={"Retry-After": "60"},
    )


def install_rate_limiting(app: FastAPI, *, api_limit: str, max_failures: int, window: int) -> None:
    limiter = Limiter(key_func=_user_or_ip_key, default_limits=[api_limit])
    app.state.limiter = limiter
    app.state.login_limiter = FailedLoginLimiter(max_failures, window)
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)


def get_login_limiter(request: Request) -> FailedLoginLimiter:
    limiter: FailedLoginLimiter = request.app.state.login_limiter
    return limiter
