"""Rate limiting: failed-login limiter (per IP and per email) and per-user API limits."""

from __future__ import annotations

import math
import threading
import time
from collections import defaultdict, deque
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.core.errors import AppError, error_body


class FailedLoginLimiter:
    """Sliding-window counter of failed logins. In-memory fallback."""

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


class RedisFailedLoginLimiter:
    """Sliding-window counter of failed logins stored in Redis sorted sets."""

    def __init__(self, max_failures: int, window_seconds: int, redis_client: Any) -> None:
        self.max_failures = max_failures
        self.window = window_seconds
        self.redis = redis_client

    def _redis_key(self, key: str) -> str:
        return f"rate_limit:login:{key}"

    def check(self, *keys: str) -> None:
        """Raise 429 if any key has reached the failure limit within the window."""
        now = time.time()
        retry_after = 0.0
        for key in keys:
            r_key = self._redis_key(key)
            pipe = self.redis.pipeline()
            pipe.zremrangebyscore(r_key, 0, now - self.window)
            pipe.zcard(r_key)
            pipe.zrange(r_key, 0, 0, withscores=True)
            _, count, earliest_items = pipe.execute()
            if count >= self.max_failures:
                if earliest_items:
                    earliest_time = float(earliest_items[0][1])
                    retry_after = max(retry_after, earliest_time + self.window - now)
                else:
                    retry_after = max(retry_after, self.window)
        if retry_after > 0:
            seconds = str(max(1, math.ceil(retry_after)))
            raise AppError(
                "Too many failed login attempts. Try again later.",
                code="rate_limited",
                status_code=429,
                headers={"Retry-After": seconds},
            )

    def record_failure(self, *keys: str) -> None:
        now = time.time()
        pipe = self.redis.pipeline()
        for key in keys:
            r_key = self._redis_key(key)
            pipe.zremrangebyscore(r_key, 0, now - self.window)
            member = f"{now}:{time.perf_counter_ns()}"
            pipe.zadd(r_key, {member: now})
            pipe.expire(r_key, int(self.window) + 60)
        pipe.execute()

    def reset(self, *keys: str) -> None:
        if keys:
            self.redis.delete(*[self._redis_key(k) for k in keys])

    def clear(self) -> None:
        keys = list(self.redis.scan_iter(match="rate_limit:login:*"))
        if keys:
            self.redis.delete(*keys)


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


def install_rate_limiting(
    app: FastAPI,
    *,
    api_limit: str,
    max_failures: int,
    window: int,
    redis_url: str | None = None,
    redis_client: Any | None = None,
) -> None:
    login_limiter: Any
    if redis_client is not None:
        login_limiter = RedisFailedLoginLimiter(max_failures, window, redis_client)
        limiter = Limiter(
            key_func=_user_or_ip_key,
            default_limits=[api_limit],
            storage_uri=redis_url or "memory://",
        )
    elif redis_url:
        try:
            import redis

            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            login_limiter = RedisFailedLoginLimiter(max_failures, window, client)
            limiter = Limiter(
                key_func=_user_or_ip_key,
                default_limits=[api_limit],
                storage_uri=redis_url,
            )
        except Exception:
            login_limiter = FailedLoginLimiter(max_failures, window)
            limiter = Limiter(key_func=_user_or_ip_key, default_limits=[api_limit])
    else:
        login_limiter = FailedLoginLimiter(max_failures, window)
        limiter = Limiter(key_func=_user_or_ip_key, default_limits=[api_limit])

    app.state.limiter = limiter
    app.state.login_limiter = login_limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_handler)
    app.add_middleware(SlowAPIMiddleware)


def get_login_limiter(request: Request) -> FailedLoginLimiter | RedisFailedLoginLimiter:
    limiter: FailedLoginLimiter | RedisFailedLoginLimiter = request.app.state.login_limiter
    return limiter
