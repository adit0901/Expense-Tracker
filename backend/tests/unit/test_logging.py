import json

import pytest
import structlog
from fastapi.testclient import TestClient

from app.core.config import Settings
from app.core.logging import REDACTED, redact_processor
from app.main import create_app


def test_redaction_processor_masks_sensitive_keys() -> None:
    event = {
        "event": "login",
        "password": "hunter2-hunter2",
        "amount": "450.00",
        "payload": {"new_password": "x", "description": "Dinner", "refresh_token": "abc", "ok": 1},
        "user_id": "u1",
    }
    out = redact_processor(None, "info", event)
    assert out["password"] == REDACTED
    assert out["amount"] == REDACTED
    assert out["payload"] == {
        "new_password": REDACTED,
        "description": REDACTED,
        "refresh_token": REDACTED,
        "ok": 1,
    }
    assert out["user_id"] == "u1"


def test_logged_payload_is_redacted_in_output(capsys: pytest.CaptureFixture[str]) -> None:
    create_app(Settings(app_env="test"))  # configures logging
    structlog.get_logger("test").info("payload", password="s3cret-pass", amount="99.00")
    line = capsys.readouterr().out.strip().splitlines()[-1]
    data = json.loads(line)
    assert data["password"] == REDACTED and data["amount"] == REDACTED
    assert "s3cret-pass" not in line and "99.00" not in line


def test_request_log_line_matches_header(capsys: pytest.CaptureFixture[str]) -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    resp = client.get("/health/live")
    rid = resp.headers["X-Request-ID"]
    lines = [json.loads(x) for x in capsys.readouterr().out.splitlines() if x.startswith("{")]
    req = [x for x in lines if x.get("event") == "request" and x.get("request_id") == rid]
    assert len(req) == 1
    assert req[0]["route"] == "/health/live"
    assert req[0]["method"] == "GET" and req[0]["status"] == 200
    assert "duration_ms" in req[0]


def test_incoming_request_id_is_propagated() -> None:
    client = TestClient(create_app(Settings(app_env="test")))
    resp = client.get("/health/live", headers={"X-Request-ID": "abc12345-req"})
    assert resp.headers["X-Request-ID"] == "abc12345-req"
