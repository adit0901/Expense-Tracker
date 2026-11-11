"""Envelope, error mapping and pagination behaviour on a throwaway app (no DB needed)."""

from decimal import Decimal
from typing import Annotated, Any

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import column

from app.core.config import Settings
from app.core.money import PositiveAmount
from app.core.pagination import PageParams, build_meta, page_params, parse_sort
from app.core.responses import Envelope, ok
from app.main import create_app


class Body(BaseModel):
    amount: PositiveAmount
    description: str | None = None


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings(app_env="test"))

    @app.post("/api/v1/_test/items")
    def create_item(body: Body) -> Envelope[Body]:
        return ok(body)

    @app.get("/api/v1/_test/boom")
    def boom() -> None:
        raise RuntimeError("SELECT secret FROM users -- internal detail")

    @app.get("/api/v1/_test/list")
    def items(
        params: Annotated[PageParams, Depends(page_params)], sort: str | None = None
    ) -> dict[str, Any]:
        order = parse_sort(sort, {"date": column("date")}, [column("date").desc()])
        return {"data": [str(o) for o in order], "meta": build_meta(params, 0).model_dump()}

    return TestClient(app, raise_server_exceptions=False)


def test_success_envelope_and_string_amount(client: TestClient) -> None:
    resp = client.post("/api/v1/_test/items", json={"amount": 1250.5})
    assert resp.status_code == 200
    assert resp.json() == {"data": {"amount": "1250.50", "description": None}, "meta": {}}


def test_validation_error_lists_field(client: TestClient) -> None:
    resp = client.post("/api/v1/_test/items", json={"description": "x"})
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "validation_error"
    assert any(d["field"] == "amount" for d in err["details"])
    assert err["request_id"] == resp.headers["X-Request-ID"]


def test_unhandled_error_hides_internals(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/boom")
    assert resp.status_code == 500
    body = resp.json()
    assert body["error"]["code"] == "internal_error"
    assert "SELECT" not in resp.text and "Traceback" not in resp.text
    assert body["error"]["request_id"] == resp.headers["X-Request-ID"]


def test_unversioned_path_is_404(client: TestClient) -> None:
    resp = client.get("/accounts")
    assert resp.status_code == 404
    assert resp.json()["error"]["code"] == "not_found"


def test_page_size_capped_at_100(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/list", params={"page_size": 500})
    assert resp.status_code == 422
    detail = resp.json()["error"]["details"][0]
    assert detail["field"] == "page_size"
    assert "100" in detail["message"]


def test_disallowed_sort_field(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/list", params={"sort": "password_hash"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "invalid_sort"


def test_allowed_sort_and_meta(client: TestClient) -> None:
    resp = client.get("/api/v1/_test/list", params={"sort": "-date", "page": 2, "page_size": 10})
    assert resp.status_code == 200
    assert resp.json()["meta"] == {"page": 2, "page_size": 10, "total_items": 0, "total_pages": 0}


def test_build_meta_total_pages() -> None:
    assert build_meta(PageParams(page=1, page_size=25), 51).total_pages == 3


def test_security_headers_and_request_id(client: TestClient) -> None:
    resp = client.get("/health/live")
    assert resp.status_code == 200
    assert len(resp.headers["X-Request-ID"]) >= 8
    assert resp.headers["X-Content-Type-Options"] == "nosniff"
    assert resp.headers["X-Frame-Options"] == "DENY"
    assert "max-age" in resp.headers["Strict-Transport-Security"]
    assert "default-src 'none'" in resp.headers["Content-Security-Policy"]


def test_cors_rejects_unknown_origin(client: TestClient) -> None:
    headers = {"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"}
    resp = client.options("/api/v1/_test/list", headers=headers)
    assert resp.status_code == 400
    assert "access-control-allow-origin" not in resp.headers


def test_cors_allows_configured_origin(client: TestClient) -> None:
    headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "GET"}
    resp = client.options("/api/v1/_test/list", headers=headers)
    assert resp.status_code == 200
    assert resp.headers["access-control-allow-origin"] == "http://localhost:5173"


def test_decimal_input_accepts_string(client: TestClient) -> None:
    resp = client.post("/api/v1/_test/items", json={"amount": "10.10"})
    assert resp.json()["data"]["amount"] == "10.10"
    assert Decimal(resp.json()["data"]["amount"]) == Decimal("10.1")
