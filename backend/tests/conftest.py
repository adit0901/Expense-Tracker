"""Shared fixtures. Integration tests run against a real PostgreSQL test database."""

from __future__ import annotations

import os

# Configure the environment before the app is imported.
os.environ.setdefault("APP_ENV", "test")
os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://fintrack_app:fintrack_app@localhost:54329/fintrack_test",
)
os.environ["MIGRATION_DATABASE_URL"] = os.environ.get(
    "TEST_MIGRATION_DATABASE_URL",
    "postgresql+psycopg://fintrack:fintrack@localhost:54329/fintrack_test",
)
os.environ.setdefault("JWT_SECRET", "test-secret-" + "x" * 32)

from collections.abc import Iterator
from pathlib import Path

import pytest
from alembic.config import Config
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session

from alembic import command
from app.core.db import get_db

BACKEND = Path(__file__).resolve().parents[1]


def _alembic_config() -> Config:
    cfg = Config(str(BACKEND / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND / "alembic"))
    return cfg


@pytest.fixture(scope="session")
def migrated_db() -> Iterator[None]:
    cfg = _alembic_config()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")
    yield


@pytest.fixture(scope="session")
def app_engine(migrated_db: None) -> Iterator[Engine]:
    engine = create_engine(os.environ["DATABASE_URL"])
    yield engine
    engine.dispose()


@pytest.fixture
def db(app_engine: Engine) -> Iterator[Session]:
    """A session inside an outer transaction that is rolled back after each test."""
    connection = app_engine.connect()
    outer = connection.begin()
    session = Session(
        bind=connection, join_transaction_mode="create_savepoint", expire_on_commit=False
    )
    try:
        yield session
    finally:
        session.close()
        outer.rollback()
        connection.close()


@pytest.fixture
def app(db: Session) -> Iterator[FastAPI]:
    from app.main import app as fastapi_app

    def _override() -> Iterator[Session]:
        yield db

    fastapi_app.dependency_overrides[get_db] = _override
    yield fastapi_app
    fastapi_app.dependency_overrides.clear()


@pytest.fixture
def client(app: FastAPI) -> Iterator[TestClient]:
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
