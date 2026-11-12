"""Test helpers shared across integration tests."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from fastapi.testclient import TestClient

BASE_URL = "https://testserver"  # https so Secure cookies are sent back
DEFAULT_PASSWORD = "Correct-Horse-Battery-9"


@dataclass
class AuthedUser:
    id: uuid.UUID
    email: str
    password: str
    client: TestClient

    def get(self, url: str, **kw: Any) -> Any:
        return self.client.get(url, **kw)

    def post(self, url: str, **kw: Any) -> Any:
        return self.client.post(url, **kw)

    def put(self, url: str, **kw: Any) -> Any:
        return self.client.put(url, **kw)

    def patch(self, url: str, **kw: Any) -> Any:
        return self.client.patch(url, **kw)

    def delete(self, url: str, **kw: Any) -> Any:
        return self.client.request("DELETE", url, **kw)


def data(resp: Any) -> Any:
    assert resp.status_code < 300, resp.text
    return resp.json()["data"]
