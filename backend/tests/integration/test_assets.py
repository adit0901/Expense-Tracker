from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.helpers import AuthedUser, data


@pytest.mark.integration
def test_asset_creation_and_bank_type_rejection(
    client: TestClient, user: AuthedUser
) -> None:
    u = user

    # 1. FD creation with details
    res = data(
        u.post(
            "/api/v1/assets",
            json={
                "type": "fixed_deposit",
                "name": "HDFC Tax Saver FD",
                "current_value": "205000.00",
                "is_liquid": False,
                "details": {
                    "principal": "200000.00",
                    "rate": "7.10",
                    "maturity_date": "2027-11-01",
                },
            },
        )
    )
    assert res["name"] == "HDFC Tax Saver FD"
    assert res["type"] == "fixed_deposit"
    assert res["current_value"] == "205000.00"
    assert res["details"]["principal"] == "200000.00"

    # 2. Reject type "bank" with 422
    resp_bank = u.post(
        "/api/v1/assets",
        json={
            "type": "bank",
            "name": "My Savings Account",
            "current_value": "50000.00",
        },
    )
    assert resp_bank.status_code == 422
    assert "bank" in resp_bank.text.lower()


@pytest.mark.integration
def test_valuation_history_and_historical_lookup(
    client: TestClient, user: AuthedUser
) -> None:
    u = user

    # Gold valued 150,000 on 2026-06-30
    asset = data(
        u.post(
            "/api/v1/assets",
            json={
                "type": "gold",
                "name": "Sovereign Gold Bond",
                "current_value": "150000.00",
                "as_of": "2026-06-30",
                "is_liquid": True,
            },
        )
    )
    asset_id = asset["id"]

    # Revalued to 165,000 on 2026-10-31
    data(
        u.post(
            f"/api/v1/assets/{asset_id}/valuations",
            json={"as_of": "2026-10-31", "value": "165000.00"},
        )
    )

    # Net worth / lookup on 2026-09-30 uses 150000.00
    a_sep = data(u.get(f"/api/v1/assets/{asset_id}?as_of=2026-09-30"))
    assert a_sep["current_value"] == "150000.00"
    assert a_sep["latest_valuation_date"] == "2026-06-30"

    # Lookup on 2026-11-01 uses 165000.00
    a_nov = data(u.get(f"/api/v1/assets/{asset_id}?as_of=2026-11-01"))
    assert a_nov["current_value"] == "165000.00"
    assert a_nov["latest_valuation_date"] == "2026-10-31"

    # List valuations
    vals = data(u.get(f"/api/v1/assets/{asset_id}/valuations"))
    assert len(vals) == 2


@pytest.mark.integration
def test_closing_asset_with_history_retention(
    client: TestClient, user: AuthedUser
) -> None:
    u = user

    # Real estate bought and valued 5,000,000 on 2026-01-01
    asset = data(
        u.post(
            "/api/v1/assets",
            json={
                "type": "real_estate",
                "name": "Apartment in Whitefield",
                "current_value": "5000000.00",
                "as_of": "2026-01-01",
            },
        )
    )
    asset_id = asset["id"]

    # Property sold / closed on 2026-12-15
    closed = data(
        u.post(
            f"/api/v1/assets/{asset_id}/close",
            json={"closed_at": "2026-12-15"},
        )
    )
    assert closed["closed_at"] == "2026-12-15"

    # Before closing (2026-12-01): still active with 5,000,000 value
    before_close = data(u.get(f"/api/v1/assets/{asset_id}?as_of=2026-12-01"))
    assert before_close["current_value"] == "5000000.00"

    # After closing (2026-12-20): value is 0.00
    after_close = data(u.get(f"/api/v1/assets/{asset_id}?as_of=2026-12-20"))
    assert after_close["current_value"] == "0.00"

    # Default list on 2026-12-20 excludes closed asset
    list_open = data(u.get("/api/v1/assets?as_of=2026-12-20"))
    assert len(list_open) == 0

    # List with include_closed=true includes it
    list_all = data(u.get("/api/v1/assets?as_of=2026-12-20&include_closed=true"))
    assert len(list_all) == 1


@pytest.mark.integration
def test_liabilities_crud_balances_and_closing(
    client: TestClient, user: AuthedUser
) -> None:
    u = user

    # 1. Create family loan of 100,000 on 2026-10-01
    liab = data(
        u.post(
            "/api/v1/liabilities",
            json={
                "name": "Loan from Uncle",
                "current_balance": "100000.00",
                "as_of": "2026-10-01",
                "notes": "Interest free personal loan",
            },
        )
    )
    liab_id = liab["id"]
    assert liab["current_balance"] == "100000.00"

    # 2. Lower balance to 80,000 on 2026-11-01
    b2 = data(
        u.post(
            f"/api/v1/liabilities/{liab_id}/balances",
            json={"as_of": "2026-11-01", "balance": "80000.00"},
        )
    )
    assert b2["balance"] == "80000.00"

    # Check historical balance lookup
    l_oct = data(u.get(f"/api/v1/liabilities/{liab_id}?as_of=2026-10-15"))
    assert l_oct["current_balance"] == "100000.00"

    l_nov = data(u.get(f"/api/v1/liabilities/{liab_id}?as_of=2026-11-05"))
    assert l_nov["current_balance"] == "80000.00"

    # 3. Update metadata
    up = data(u.patch(f"/api/v1/liabilities/{liab_id}", json={"name": "Family Loan"}))
    assert up["name"] == "Family Loan"

    # 4. Close liability
    closed = data(
        u.post(
            f"/api/v1/liabilities/{liab_id}/close",
            json={"closed_at": "2026-11-30"},
        )
    )
    assert closed["closed_at"] == "2026-11-30"

    # After closing date
    after = data(u.get(f"/api/v1/liabilities/{liab_id}?as_of=2026-12-05"))
    assert after["current_balance"] == "0.00"

