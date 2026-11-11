"""Cross-tenant isolation sweep (security-baseline: user-level data isolation)."""

from __future__ import annotations

import json
import re
import uuid

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

import tests.tenancy_cases  # noqa: F401  - registers OwnedCases
from tests.helpers import AuthedUser, data
from tests.tenancy import OWNED_CASES, PUBLIC_ENDPOINTS, OwnedCase


def _api_operations(app: FastAPI) -> list[tuple[str, str]]:
    ops = []
    for path, methods in app.openapi()["paths"].items():
        if not path.startswith("/api/v1/"):
            continue
        for method in methods:
            ops.append((method.upper(), path))
    return sorted(ops)


def test_sweep_covers_auth_and_user_endpoints(app: FastAPI) -> None:
    ops = set(_api_operations(app))
    for expected in [
        ("GET", "/api/v1/users/me"),
        ("PATCH", "/api/v1/users/me/preferences"),
        ("POST", "/api/v1/auth/logout"),
        ("DELETE", "/api/v1/users/me"),
    ]:
        assert expected in ops


def test_every_non_public_endpoint_requires_authentication(
    app: FastAPI, client: TestClient
) -> None:
    checked = 0
    for method, path in _api_operations(app):
        if (method, path) in PUBLIC_ENDPOINTS:
            continue
        url = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), path)
        resp = client.request(method, url)
        assert resp.status_code == 401, f"{method} {path} -> {resp.status_code}"
        assert resp.json()["error"]["code"] == "not_authenticated"
        checked += 1
    assert checked > 0


def test_users_me_is_scoped_to_caller(user: AuthedUser, other_user: AuthedUser) -> None:
    assert data(user.get("/api/v1/users/me"))["email"] == user.email
    assert data(other_user.get("/api/v1/users/me"))["email"] == other_user.email
    data(other_user.patch("/api/v1/users/me/preferences", json={"theme": "dark"}))
    assert data(user.get("/api/v1/users/me/preferences"))["theme"] == "system"


def test_access_token_of_one_user_cannot_be_used_for_another(
    user: AuthedUser, other_user: AuthedUser
) -> None:
    # Tokens carry only the caller's id; there is no way to address another user's profile.
    assert user.get(f"/api/v1/users/{other_user.id}").status_code == 404


@pytest.mark.parametrize("case", OWNED_CASES, ids=lambda c: c.name)
def test_owned_resources_are_invisible_to_other_users(
    case: OwnedCase, user: AuthedUser, other_user: AuthedUser
) -> None:
    resource_id = case.create(user)
    for probe in case.probes:
        url = probe.path.replace("{id}", resource_id)
        resp = other_user.client.request(probe.method, url, json=probe.json, files=probe.files)
        assert resp.status_code == 404, f"{probe.method} {url} -> {resp.status_code} {resp.text}"
        assert resource_id not in resp.text
    if case.list_path:
        listing = other_user.get(case.list_path)
        assert listing.status_code == 200
        assert resource_id not in json.dumps(listing.json())
    # The owner still has access.
    for probe in case.probes:
        if probe.method == "GET":
            assert user.get(probe.path.replace("{id}", resource_id)).status_code == 200
