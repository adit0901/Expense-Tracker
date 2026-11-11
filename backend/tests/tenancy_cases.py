"""OwnedCase registrations for each domain (extended as domains are added)."""

from __future__ import annotations

from tests.factories import create_account
from tests.helpers import AuthedUser, data
from tests.tenancy import OwnedCase, Probe, register_case


def _account(u: AuthedUser) -> str:
    return str(create_account(u, "Tenant Acct")["id"])


register_case(
    OwnedCase(
        name="account",
        create=_account,
        probes=[
            Probe("GET", "/api/v1/accounts/{id}"),
            Probe("PATCH", "/api/v1/accounts/{id}", json={"name": "Hijacked"}),
            Probe("POST", "/api/v1/accounts/{id}/archive"),
            Probe("DELETE", "/api/v1/accounts/{id}"),
        ],
        list_path="/api/v1/accounts?include_archived=true",
    )
)


def _category(u: AuthedUser) -> str:
    return str(
        data(u.post("/api/v1/categories", json={"kind": "expense", "name": "Private Cat"}))["id"]
    )


register_case(
    OwnedCase(
        name="category",
        create=_category,
        probes=[
            Probe("GET", "/api/v1/categories/{id}"),
            Probe("PATCH", "/api/v1/categories/{id}", json={"name": "Hijacked"}),
            Probe("DELETE", "/api/v1/categories/{id}"),
        ],
        list_path="/api/v1/categories?page_size=100",
    )
)
