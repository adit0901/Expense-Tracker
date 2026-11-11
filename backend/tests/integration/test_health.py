from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.core.db import get_engine


def test_live(client: TestClient) -> None:
    assert client.get("/health/live").status_code == 200


def test_ready_ok(client: TestClient, app: FastAPI) -> None:
    from tests.conftest import os

    engine = create_engine(os.environ["DATABASE_URL"])
    app.dependency_overrides[get_engine] = lambda: engine
    resp = client.get("/health/ready")
    assert resp.status_code == 200, resp.text
    assert resp.json()["data"]["checks"] == {"database": "ok", "migrations": "ok"}


def test_ready_503_when_db_down(client: TestClient, app: FastAPI) -> None:
    dead = create_engine(
        "postgresql+psycopg://x:y@127.0.0.1:1/none", connect_args={"connect_timeout": 1}
    )
    app.dependency_overrides[get_engine] = lambda: dead
    resp = client.get("/health/ready")
    assert resp.status_code == 503
    body = resp.json()
    assert body["error"]["details"] == [{"dependency": "database"}]
    assert "x:y" not in resp.text
