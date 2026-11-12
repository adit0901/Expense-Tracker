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
            Probe("POST", "/api/v1/accounts/{id}/unarchive"),
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


def _budget(u: AuthedUser) -> str:
    from tests.factories import cat_id

    c = cat_id(u, "Food")
    res = data(
        u.put(
            "/api/v1/budgets/2026-11",
            json={
                "overall_amount": "50000.00",
                "lines": [{"category_id": c, "amount": "10000.00"}],
            },
        )
    )
    return str(res["id"])


register_case(
    OwnedCase(
        name="budget",
        create=_budget,
        probes=[
            Probe("GET", "/api/v1/budgets?month=2026-11"),
        ],
    )
)


def _goal(u: AuthedUser) -> str:
    res = data(
        u.post(
            "/api/v1/goals",
            json={
                "name": "Secret Vacation",
                "type": "vacation",
                "target_amount": "50000.00",
            },
        )
    )
    return str(res["id"])


register_case(
    OwnedCase(
        name="goal",
        create=_goal,
        probes=[
            Probe("GET", "/api/v1/goals/{id}"),
            Probe("PATCH", "/api/v1/goals/{id}", json={"name": "Hijacked"}),
            Probe("DELETE", "/api/v1/goals/{id}"),
            Probe("GET", "/api/v1/goals/{id}/contributions"),
            Probe(
                "POST",
                "/api/v1/goals/{id}/contributions",
                json={"amount": "1000.00", "date": "2026-11-01"},
            ),
        ],
        list_path="/api/v1/goals",
    )
)


def _asset(u: AuthedUser) -> str:
    res = data(
        u.post(
            "/api/v1/assets",
            json={
                "name": "Secret Gold",
                "type": "gold",
                "current_value": "100000.00",
            },
        )
    )
    return str(res["id"])


register_case(
    OwnedCase(
        name="asset",
        create=_asset,
        probes=[
            Probe("GET", "/api/v1/assets/{id}"),
            Probe("PATCH", "/api/v1/assets/{id}", json={"name": "Hijacked"}),
            Probe("POST", "/api/v1/assets/{id}/close", json={"closed_at": "2026-12-31"}),
            Probe("GET", "/api/v1/assets/{id}/valuations"),
            Probe(
                "POST",
                "/api/v1/assets/{id}/valuations",
                json={"as_of": "2026-11-01", "value": "110000.00"},
            ),
        ],
        list_path="/api/v1/assets",
    )
)


def _liability(u: AuthedUser) -> str:
    res = data(
        u.post(
            "/api/v1/liabilities",
            json={
                "name": "Secret Debt",
                "current_balance": "50000.00",
            },
        )
    )
    return str(res["id"])


register_case(
    OwnedCase(
        name="liability",
        create=_liability,
        probes=[
            Probe("GET", "/api/v1/liabilities/{id}"),
            Probe("PATCH", "/api/v1/liabilities/{id}", json={"name": "Hijacked"}),
            Probe("POST", "/api/v1/liabilities/{id}/close", json={"closed_at": "2026-12-31"}),
            Probe("GET", "/api/v1/liabilities/{id}/balances"),
            Probe(
                "POST",
                "/api/v1/liabilities/{id}/balances",
                json={"as_of": "2026-11-01", "balance": "40000.00"},
            ),
        ],
        list_path="/api/v1/liabilities",
    )
)


def _loan(u: AuthedUser) -> str:
    res = data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "personal",
                "lender": "Secret Bank",
                "original_principal": "100000.00",
                "annual_rate": "10.0",
                "tenure_months": 12,
                "start_date": "2026-11-01",
            },
        )
    )
    return str(res["id"])


register_case(
    OwnedCase(
        name="loan",
        create=_loan,
        probes=[
            Probe("GET", "/api/v1/loans/{id}"),
            Probe("PATCH", "/api/v1/loans/{id}", json={"lender": "Hijacked"}),
            Probe("DELETE", "/api/v1/loans/{id}"),
            Probe("GET", "/api/v1/loans/{id}/schedule"),
            Probe(
                "POST",
                "/api/v1/loans/{id}/simulate",
                json={
                    "kind": "rate_change",
                    "effective_date": "2026-12-01",
                    "annual_rate": "12.0",
                    "strategy": "keep_tenure",
                },
            ),
        ],
        list_path="/api/v1/loans",
    )
)


def _net_worth_snapshot(u: AuthedUser) -> str:
    res = data(u.post("/api/v1/net-worth/snapshots", json={"as_of": "2026-11-01"}))
    return str(res["as_of"])


register_case(
    OwnedCase(
        name="net_worth_snapshot",
        create=_net_worth_snapshot,
        probes=[
            Probe("POST", "/api/v1/net-worth/snapshots/{id}/recompute"),
        ],
        list_path="/api/v1/net-worth/snapshots",
    )
)
