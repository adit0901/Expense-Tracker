"""Unauthenticated liveness/readiness probes."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Annotated, Any

from alembic.config import Config
from alembic.script import ScriptDirectory
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import Engine, text

from app.core.db import get_engine
from app.core.errors import error_body

router = APIRouter(prefix="/health", tags=["health"])

ALEMBIC_INI = Path(__file__).resolve().parents[2] / "alembic.ini"


@lru_cache
def expected_heads() -> frozenset[str]:
    cfg = Config(str(ALEMBIC_INI))
    cfg.set_main_option("script_location", str(ALEMBIC_INI.parent / "alembic"))
    return frozenset(ScriptDirectory.from_config(cfg).get_heads())


@router.get("/live")
def live() -> dict[str, Any]:
    return {"data": {"status": "ok"}, "meta": {}}


@router.get("/ready", response_model=None)
def ready(engine: Annotated[Engine, Depends(get_engine)]) -> JSONResponse | dict[str, Any]:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
            current = {r[0] for r in conn.execute(text("SELECT version_num FROM alembic_version"))}
    except Exception:
        return JSONResponse(
            error_body(
                "dependency_unavailable", "Database is unreachable", [{"dependency": "database"}]
            ),
            status_code=503,
        )
    if current != set(expected_heads()):
        return JSONResponse(
            error_body(
                "dependency_unavailable",
                "Database migrations are not current",
                [{"dependency": "migrations"}],
            ),
            status_code=503,
        )
    return {"data": {"status": "ok", "checks": {"database": "ok", "migrations": "ok"}}, "meta": {}}
