from __future__ import annotations

import asyncio

from app.tasks.worker import WorkerSettings, health_check, parse_redis_settings


def test_worker_health_check() -> None:
    result = asyncio.run(health_check({}))
    assert result == "ok"


def test_parse_redis_settings() -> None:
    settings = parse_redis_settings("redis://:secret@redis-host:6380/2")
    assert settings.host == "redis-host"
    assert settings.port == 6380
    assert settings.database == 2
    assert settings.password == "secret"


def test_worker_settings_configured() -> None:
    assert health_check in WorkerSettings.functions
