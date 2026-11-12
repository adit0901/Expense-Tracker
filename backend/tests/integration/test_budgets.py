from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data


@pytest.mark.integration
def test_budget_crud_and_utilization(client: TestClient, user: AuthedUser) -> None:
    u = user
    food_cat = cat_id(u, "Food")

    # 1. Set budget for 2026-11: overall 60000.00, Food 12000.00
    res = data(
        u.put(
            "/api/v1/budgets/2026-11",
            json={
                "overall_amount": "60000.00",
                "lines": [
                    {
                        "category_id": food_cat,
                        "amount": "12000.00",
                        "alert_thresholds": [80, 100],
                    }
                ],
            },
        )
    )
    assert res["month"] == "2026-11"
    assert res["overall_amount"] == "60000.00"
    assert len(res["lines"]) == 1
    assert res["lines"][0]["amount"] == "12000.00"
    assert res["lines"][0]["actual"] == "0.00"
    assert res["lines"][0]["utilization"] == "0.00"
    assert res["lines"][0]["remaining"] == "12000.00"
    assert res["lines"][0]["is_over_budget"] is False

    # 2. Add an expense of 9000.00 in Food
    acct = create_account(u, "Bank 1")
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="9000.00",
        txn_date="2026-11-10",
        payment_method="upi",
    )

    # 3. Check budget again: utilization should be 75.00, remaining 3000.00
    b_res = data(u.get("/api/v1/budgets?month=2026-11"))
    food_line = b_res["lines"][0]
    assert food_line["actual"] == "9000.00"
    assert food_line["utilization"] == "75.00"
    assert food_line["remaining"] == "3000.00"
    assert food_line["is_over_budget"] is False

    # 4. Add another expense of 4500.00 in Food -> total 13500.00
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="4500.00",
        txn_date="2026-11-15",
        payment_method="upi",
    )

    b_res2 = data(u.get("/api/v1/budgets?month=2026-11"))
    food_line2 = b_res2["lines"][0]
    assert food_line2["actual"] == "13500.00"
    assert food_line2["utilization"] == "112.50"
    assert food_line2["remaining"] == "-1500.00"
    assert food_line2["is_over_budget"] is True


@pytest.mark.integration
def test_budget_subcategory_rollup(client: TestClient, user: AuthedUser) -> None:
    u = user
    parent_cat = cat_id(u, "Food")

    # Create subcategory under Food
    subcat_res = data(
        u.post(
            "/api/v1/categories",
            json={"name": "Fine Dining", "kind": "expense", "parent_id": parent_cat},
        )
    )
    subcat_id = subcat_res["id"]

    # Budget is set on parent category
    u.put(
        "/api/v1/budgets/2026-11",
        json={
            "overall_amount": "50000.00",
            "lines": [{"category_id": parent_cat, "amount": "10000.00"}],
        },
    )

    acct = create_account(u, "Main Bank")
    # Expense on parent: 3000
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=parent_cat,
        amount="3000.00",
        txn_date="2026-11-05",
        payment_method="upi",
    )
    # Expense on subcat: 4000
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=subcat_id,
        amount="4000.00",
        txn_date="2026-11-06",
        payment_method="upi",
    )

    b_res = data(u.get("/api/v1/budgets?month=2026-11"))
    line = b_res["lines"][0]
    # Parent includes subcategory: 3000 + 4000 = 7000
    assert line["actual"] == "7000.00"
    assert line["utilization"] == "70.00"


@pytest.mark.integration
def test_budget_over_allocation_warning(client: TestClient, user: AuthedUser) -> None:
    u = user
    c1 = cat_id(u, "Food")
    c2 = cat_id(u, "Shopping")

    # Category budgets sum to 70000 against 60000 overall
    res = data(
        u.put(
            "/api/v1/budgets/2026-11",
            json={
                "overall_amount": "60000.00",
                "lines": [
                    {"category_id": c1, "amount": "40000.00"},
                    {"category_id": c2, "amount": "30000.00"},
                ],
            },
        )
    )
    assert res["warning"] == "Category budgets exceed overall budget"
    assert res["overall_amount"] == "60000.00"


@pytest.mark.integration
def test_copy_budget_forward(client: TestClient, user: AuthedUser) -> None:
    u = user
    food_cat = cat_id(u, "Food")

    # Set budget for Oct 2026
    u.put(
        "/api/v1/budgets/2026-10",
        json={
            "overall_amount": "55000.00",
            "lines": [{"category_id": food_cat, "amount": "15000.00"}],
        },
    )

    # Copy to Dec 2026
    copied = data(u.post("/api/v1/budgets/2026-12/copy-from/2026-10"))
    assert copied["month"] == "2026-12"
    assert copied["overall_amount"] == "55000.00"
    assert len(copied["lines"]) == 1
    assert copied["lines"][0]["amount"] == "15000.00"

    # Attempting to copy again to Dec 2026 should fail (conflict 409)
    err_res = u.post("/api/v1/budgets/2026-12/copy-from/2026-10")
    assert err_res.status_code == 409


@pytest.mark.integration
def test_budget_alert_evaluation_and_deduplication(client: TestClient, user: AuthedUser) -> None:
    u = user
    food_cat = cat_id(u, "Food")
    acct = create_account(u, "Checking")

    # Set Food budget 10,000 with 80% and 100% thresholds
    u.put(
        "/api/v1/budgets/2026-11",
        json={
            "overall_amount": "50000.00",
            "lines": [
                {
                    "category_id": food_cat,
                    "amount": "10000.00",
                    "alert_thresholds": [80, 100],
                }
            ],
        },
    )

    # 1. Expense of 7800 (78% - no alert)
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="7800.00",
        txn_date="2026-11-01",
        payment_method="upi",
    )
    alerts1 = data(u.get("/api/v1/budget-alerts?month=2026-11"))
    assert len(alerts1) == 0

    # 2. Another expense of 500 raises to 8300 (83% - triggers 80% alert)
    t2 = make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="500.00",
        txn_date="2026-11-02",
        payment_method="upi",
    )
    alerts2 = data(u.get("/api/v1/budget-alerts?month=2026-11"))
    assert len(alerts2) == 1
    assert alerts2[0]["threshold"] == 80

    # 3. Another expense of 550 raises to 8850 (below 100% - still only one 80% alert)
    t3 = make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="550.00",
        txn_date="2026-11-03",
        payment_method="upi",
    )
    alerts3 = data(u.get("/api/v1/budget-alerts?month=2026-11"))
    assert len(alerts3) == 1

    # 4. Delete t3: utilization drops to 83%. Delete t2: utilization drops to 78%.
    u.delete(f"/api/v1/transactions/{t3['id']}")
    u.delete(f"/api/v1/transactions/{t2['id']}")

    # 5. Add expense of 600 re-crossing 80%: no duplicate alert should be created
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        category_id=food_cat,
        amount="600.00",
        txn_date="2026-11-04",
        payment_method="upi",
    )
    alerts4 = data(u.get("/api/v1/budget-alerts?month=2026-11"))
    assert len(alerts4) == 1
    assert alerts4[0]["threshold"] == 80


@pytest.mark.integration
def test_budget_comparison_endpoint(client: TestClient, user: AuthedUser) -> None:
    u = user
    comp = data(u.get("/api/v1/budgets/comparison?months=6"))
    assert "months" in comp
    assert len(comp["months"]) == 6
