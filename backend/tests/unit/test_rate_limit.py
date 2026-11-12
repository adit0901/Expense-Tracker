from __future__ import annotations

import fakeredis
import pytest

from app.core.errors import AppError
from app.core.rate_limit import RedisFailedLoginLimiter


def test_redis_failed_login_limiter_allows_up_to_limit() -> None:
    fake_redis = fakeredis.FakeRedis()
    limiter = RedisFailedLoginLimiter(max_failures=5, window_seconds=60, redis_client=fake_redis)

    limiter.check("user@example.com")
    for _ in range(5):
        limiter.record_failure("user@example.com")

    with pytest.raises(AppError) as exc_info:
        limiter.check("user@example.com")

    assert exc_info.value.status_code == 429
    assert exc_info.value.code == "rate_limited"
    assert "Retry-After" in exc_info.value.headers
    assert int(exc_info.value.headers["Retry-After"]) > 0


def test_redis_failed_login_limiter_reset() -> None:
    fake_redis = fakeredis.FakeRedis()
    limiter = RedisFailedLoginLimiter(max_failures=3, window_seconds=60, redis_client=fake_redis)

    for _ in range(3):
        limiter.record_failure("user@example.com")

    with pytest.raises(AppError):
        limiter.check("user@example.com")

    limiter.reset("user@example.com")
    # Should not raise now
    limiter.check("user@example.com")


def test_redis_failed_login_limiter_clear() -> None:
    fake_redis = fakeredis.FakeRedis()
    limiter = RedisFailedLoginLimiter(max_failures=2, window_seconds=60, redis_client=fake_redis)

    limiter.record_failure("user1@example.com")
    limiter.record_failure("user1@example.com")
    limiter.record_failure("user2@example.com")
    limiter.record_failure("user2@example.com")

    with pytest.raises(AppError):
        limiter.check("user1@example.com")

    limiter.clear()
    limiter.check("user1@example.com")
    limiter.check("user2@example.com")
