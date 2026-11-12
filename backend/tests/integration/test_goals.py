from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data


@pytest.mark.integration
def test_savings_target_achievement_and_negative_savings(
    client: TestClient, user: AuthedUser
) -> None:
    u = user
    food_cat = cat_id(u, "Food")
    salary_cat = cat_id(u, "Salary", kind="income")
    acct = create_account(u, "Savings Bank")

    # 1. Set savings target of 30,000 for 2026-11
    u.put("/api/v1/savings-targets/2026-11", json={"amount": "30000.00"})

    # 2. Income 50,000, Expense 14,000 -> Actual Savings 36,000
    make_txn(
        u,
        type="income",
        account_id=acct["id"],
        category_id=salary_cat,
        amount="50000.00",
        txn_date="2026-11-05",
    )
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="14000.00",
        txn_date="2026-11-10",
        payment_method="upi",
    )

    st = data(u.get("/api/v1/savings-targets?month=2026-11"))
    assert st["target_amount"] == "30000.00"
    assert st["actual_savings"] == "36000.00"
    assert st["achievement_pct"] == "120.00"
    assert st["shortfall"] == "0.00"
    assert st["is_achieved"] is True

    # 3. Negative savings scenario in 2026-12:
    # Target 30000.00, Income 10000.00, Expense 15000.00 -> Actual -5000.00
    make_txn(
        u,
        type="income",
        account_id=acct["id"],
        category_id=salary_cat,
        amount="10000.00",
        txn_date="2026-12-05",
    )
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="15000.00",
        txn_date="2026-12-10",
        payment_method="upi",
    )

    st_dec = data(u.get("/api/v1/savings-targets?month=2026-12"))
    assert st_dec["actual_savings"] == "-5000.00"
    assert st_dec["achievement_pct"] == "0.00"
    assert st_dec["shortfall"] == "35000.00"
    assert st_dec["is_achieved"] is False


@pytest.mark.integration
def test_goal_crud_and_contributions(client: TestClient, user: AuthedUser) -> None:
    u = user

    # 1. Create Goal with starting_amount 50000.00
    created = data(
        u.post(
            "/api/v1/goals",
            json={
                "name": "Emergency Fund",
                "type": "emergency_fund",
                "target_amount": "300000.00",
                "starting_amount": "50000.00",
                "target_date": "2027-06-30",
            },
        )
    )
    goal_id = created["id"]
    assert created["name"] == "Emergency Fund"
    assert created["current_amount"] == "50000.00"
    assert created["progress_pct"] == "16.67"
    assert created["remaining_amount"] == "250000.00"

    # 2. Add contribution of 25000.00
    c1 = data(
        u.post(
            f"/api/v1/goals/{goal_id}/contributions",
            json={"amount": "25000.00", "date": "2026-11-10", "kind": "contribution"},
        )
    )
    assert c1["amount"] == "25000.00"

    # Current amount now 75000.00
    g = data(u.get(f"/api/v1/goals/{goal_id}"))
    assert g["current_amount"] == "75000.00"
    assert g["progress_pct"] == "25.00"
    assert g["remaining_amount"] == "225000.00"

    # 3. Over-withdrawal: try withdrawing 80000.00 when current is 75000.00
    resp_over = u.post(
        f"/api/v1/goals/{goal_id}/withdrawals",
        json={"amount": "80000.00", "date": "2026-11-12"},
    )
    assert resp_over.status_code == 422
    assert "insufficient_goal_balance" in resp_over.text

    # 4. Valid withdrawal of 20000.00 -> balance becomes 55000.00
    u.post(
        f"/api/v1/goals/{goal_id}/withdrawals",
        json={"amount": "20000.00", "date": "2026-11-12"},
    )
    g_after = data(u.get(f"/api/v1/goals/{goal_id}"))
    assert g_after["current_amount"] == "55000.00"

    # 5. List contributions
    contribs = data(u.get(f"/api/v1/goals/{goal_id}/contributions"))
    assert len(contribs) == 2

    # 6. Update goal
    up = data(u.patch(f"/api/v1/goals/{goal_id}", json={"name": "Rainy Day Fund"}))
    assert up["name"] == "Rainy Day Fund"

    # 7. Delete goal
    del_resp = u.delete(f"/api/v1/goals/{goal_id}")
    assert del_resp.status_code == 204
    get_404 = u.get(f"/api/v1/goals/{goal_id}")
    assert get_404.status_code == 404


@pytest.mark.integration
def test_goal_projections_and_overdue(client: TestClient, user: AuthedUser) -> None:
    u = user

    # 1. Goal with no contributions:
    # 3-month average is 0, so estimated completion is "Cannot estimate"
    g1 = data(
        u.post(
            "/api/v1/goals",
            json={
                "name": "Vacation 2027",
                "type": "vacation",
                "target_amount": "100000.00",
                "target_date": "2027-12-31",
            },
        )
    )
    assert g1["estimated_completion_label"] == "Cannot estimate"
    assert g1["estimated_completion_date"] is None
    assert g1["is_overdue"] is False

    # 2. Overdue goal: target date in the past
    g2 = data(
        u.post(
            "/api/v1/goals",
            json={
                "name": "Past Trip",
                "type": "vacation",
                "target_amount": "50000.00",
                "target_date": "2025-01-01",
            },
        )
    )
    assert g2["is_overdue"] is True
    assert g2["required_monthly_contribution"] is None
