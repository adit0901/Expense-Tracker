"""ARQ background worker configuration and job definitions."""

from __future__ import annotations

from typing import Any, ClassVar
from urllib.parse import urlparse

from arq.connections import RedisSettings
from arq.cron import cron

from app.core.config import get_settings


def parse_redis_settings(url: str) -> RedisSettings:
    """Parse a redis URL into ARQ RedisSettings."""
    parsed = urlparse(url)
    database = 0
    if parsed.path and len(parsed.path) > 1:
        try:
            database = int(parsed.path.lstrip("/"))
        except ValueError:
            database = 0
    return RedisSettings(
        host=parsed.hostname or "localhost",
        port=parsed.port or 6379,
        database=database,
        password=parsed.password,
    )


async def health_check(ctx: dict[str, Any]) -> str:
    """Health check job that can be run to verify worker connectivity."""
    return "ok"


async def take_month_end_snapshots_job(ctx: dict[str, Any]) -> int:
    """Take month-end snapshots for all active users (idempotent cron)."""
    from app.core.db import SessionLocal
    from app.services.net_worth import run_month_end_snapshots

    with SessionLocal() as db:
        return run_month_end_snapshots(db)


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    ctx["settings"] = settings


async def shutdown(ctx: dict[str, Any]) -> None:
    pass


class WorkerSettings:
    functions: ClassVar[list[Any]] = [health_check, take_month_end_snapshots_job]
    cron_jobs: ClassVar[list[Any]] = [
        cron(take_month_end_snapshots_job, hour=19, minute=0),  # 00:30 IST (UTC+5:30)
    ]
    on_startup = startup
    on_shutdown = shutdown

    @classmethod
    def get_redis_settings(cls) -> RedisSettings:
        return parse_redis_settings(get_settings().redis_url)

    redis_settings = parse_redis_settings(get_settings().redis_url)
