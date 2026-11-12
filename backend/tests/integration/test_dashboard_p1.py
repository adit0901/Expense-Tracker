"""Integration tests for P1 extended Overview Dashboard: planning tiles, charts, budget status."""

from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data


@pytest.mark.integration
def test_dashboard_overview_empty_planning_state(
    client: TestClient, user: AuthedUser
) -> None:
    u = user
    # New user with no accounts, no loans, no savings target, no budget
    params = {"period": "this_month", "as_of": "2026-11-15"}
    ov = data(u.get("/api/v1/dashboard/overview", params=params))

    assert ov["net_worth"]["value"] == "0.00"
    assert ov["total_assets"]["value"] == "0.00"
    assert ov["total_liabilities"]["value"] == "0.00"
    assert ov["outstanding_loans"]["value"] == "0.00"
    assert ov["monthly_emi_commitment"]["value"] == "0.00"

    # Savings target tile unconfigured ("Set a target" state)
    assert ov["savings_target"]["configured"] is False
    assert ov["savings_target"]["target_amount"] is None

    # Budget status unconfigured
    assert ov["budget_utilization_pct"] is None
    assert ov["budget_alerts"] == []


@pytest.mark.integration
def test_dashboard_overview_with_planning_data_and_budget_alert(
    client: TestClient, user: AuthedUser
) -> None:
    u = user
    # 1. Bank account with 300,000.00
    acct = create_account(u, "Main Bank", opening_balance="300000.00", type="bank")

    # 2. FD of 200,000.00
    data(
        u.post(
            "/api/v1/assets",
            json={
                "name": "Fixed Deposit",
                "type": "fixed_deposit",
                "is_liquid": True,
                "current_value": "200000.00",
                "as_of": "2026-11-01",
            },
        )
    )

    # 3. Personal loan of 100,000.00 @ 12% for 12 months -> EMI ~8884.88
    data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "personal",
                "lender": "Axis Bank",
                "original_principal": "100000.00",
                "annual_rate": "12.0",
                "tenure_months": 12,
                "start_date": "2026-11-01",
            },
        )
    )

    # 4. Set savings target for 2026-11
    data(
        u.put(
            "/api/v1/savings-targets/2026-11",
            json={"amount": "50000.00"},
        )
    )

    # 5. Set budget for 2026-11: Overall 50,000.00, Food 10,000.00
    food_id = cat_id(u, "Food")
    data(
        u.put(
            "/api/v1/budgets/2026-11",
            json={
                "overall_amount": "50000.00",
                "lines": [{"category_id": food_id, "amount": "10000.00"}],
            },
        )
    )

    # 6. Food expenses of 11,200.00 (112% of Food budget -> over budget alert!)
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        amount="11200.00",
        txn_date="2026-11-10",
        category_id=food_id,
        payment_method="upi",
    )

    # 7. Take 2 net worth snapshots for trend series
    data(u.post("/api/v1/net-worth/snapshots", json={"as_of": "2026-10-31"}))
    data(u.post("/api/v1/net-worth/snapshots", json={"as_of": "2026-11-30"}))

    # Fetch Overview
    params = {"period": "this_month", "as_of": "2026-11-15"}
    ov = data(u.get("/api/v1/dashboard/overview", params=params))

    # Balance sheet tiles
    # Bank 300k - 11.2k = 288.8k + 200k FD = 488,800.00 assets
    assert ov["total_assets"]["value"] == "488800.00"
    # Liabilities = 100,000.00 loan
    assert ov["total_liabilities"]["value"] == "100000.00"
    # Net worth = 388,800.00
    assert ov["net_worth"]["value"] == "388800.00"

    # Loan tiles
    assert ov["outstanding_loans"]["value"] == "100000.00"
    assert Decimal(ov["monthly_emi_commitment"]["value"]) > Decimal("8000.00")

    # Savings target tile configured
    assert ov["savings_target"]["configured"] is True
    assert ov["savings_target"]["target_amount"] == "50000.00"

    # Budget status & alert: Food at 112%
    assert ov["budget_utilization_pct"] is not None
    assert len(ov["budget_alerts"]) >= 1
    alert_names = [a["category_name"] for a in ov["budget_alerts"]]
    assert "Food" in alert_names

    # Trend series
    assert len(ov["net_worth_trend"]) == 2
    assert len(ov["asset_allocation"]) >= 2
    assert len(ov["loan_trend"]) == 12
