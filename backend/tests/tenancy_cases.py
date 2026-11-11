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


PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64


def _transaction(u: AuthedUser) -> str:
    from tests.factories import cat_id, make_txn

    acct = create_account(u, "Tenant Bank")
    t = make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        amount="10.00",
        category_id=cat_id(u, "Food"),
        payment_method="upi",
        description="secret",
    )
    return str(t["id"])


register_case(
    OwnedCase(
        name="transaction",
        create=_transaction,
        probes=[
            Probe("GET", "/api/v1/transactions/{id}"),
            Probe("PATCH", "/api/v1/transactions/{id}", json={"amount": "1.00"}),
            Probe("DELETE", "/api/v1/transactions/{id}"),
            Probe(
                "POST",
                "/api/v1/transactions/{id}/attachments",
                files={"file": ("r.png", PNG, "image/png")},
            ),
        ],
        list_path="/api/v1/transactions",
    )
)


def _attachment(u: AuthedUser) -> str:
    txn_id = _transaction(u)
    resp = u.post(
        f"/api/v1/transactions/{txn_id}/attachments", files={"file": ("r.png", PNG, "image/png")}
    )
    return str(data(resp)["id"])


register_case(
    OwnedCase(
        name="attachment",
        create=_attachment,
        probes=[
            Probe("GET", "/api/v1/attachments/{id}"),
            Probe("DELETE", "/api/v1/attachments/{id}"),
        ],
    )
)


def _import(u: AuthedUser) -> str:
    acct = create_account(u, "Tenant Import Bank")
    content = b"Date,Amount,Description\n01/10/2026,-10.00,Private row\n"
    resp = u.post(
        "/api/v1/imports",
        data={"account_id": str(acct["id"])},
        files={"file": ("x.csv", content, "text/csv")},
    )
    return str(data(resp)["id"])


register_case(
    OwnedCase(
        name="import",
        create=_import,
        probes=[
            Probe("GET", "/api/v1/imports/{id}"),
            Probe("POST", "/api/v1/imports/{id}/confirm"),
            Probe("POST", "/api/v1/imports/{id}/undo"),
        ],
    )
)


def _income_source(u: AuthedUser) -> str:
    return str(
        data(u.post("/api/v1/income-sources", json={"name": "Private Salary", "type": "salary"}))[
            "id"
        ]
    )


register_case(
    OwnedCase(
        name="income_source",
        create=_income_source,
        probes=[
            Probe("GET", "/api/v1/income-sources/{id}"),
            Probe("PATCH", "/api/v1/income-sources/{id}", json={"name": "Hijacked"}),
        ],
        list_path="/api/v1/income-sources?include_inactive=true",
    )
)
