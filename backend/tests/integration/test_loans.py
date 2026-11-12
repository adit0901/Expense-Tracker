from __future__ import annotations

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient

from tests.factories import create_account
from tests.helpers import AuthedUser, data


@pytest.mark.integration
def test_loan_crud_and_mid_tenure(client: TestClient, user: AuthedUser) -> None:
    u = user

    # 1. New home loan: 5,000,000 at 8.5% for 240 months -> EMI 43,391.16
    home_loan = data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "home",
                "lender": "HDFC Ltd",
                "original_principal": "5000000.00",
                "annual_rate": "8.50",
                "tenure_months": 240,
                "start_date": "2026-11-01",
            },
        )
    )
    assert home_loan["type"] == "home"
    assert home_loan["original_principal"] == "5000000.00"
    assert home_loan["emi_amount"] == "43391.16"
    assert home_loan["current_outstanding"] == "5000000.00"
    assert home_loan["remaining_installments"] == 240

    # 2. Existing car loan mid-tenure: 380,000 outstanding as of 2026-11-01
    car_loan = data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "car",
                "lender": "SBI Car Loan",
                "original_principal": "600000.00",
                "annual_rate": "9.00",
                "tenure_months": 36,
                "start_date": "2024-11-01",
                "baseline_outstanding": "380000.00",
                "baseline_date": "2026-11-01",
                "first_emi_date": "2026-12-01",
            },
        )
    )
    assert car_loan["type"] == "car"
    assert car_loan["baseline_outstanding"] == "380000.00"
    assert car_loan["current_outstanding"] == "380000.00"

    # 3. Update loan
    up = data(u.patch(f"/api/v1/loans/{home_loan['id']}", json={"lender": "HDFC Bank"}))
    assert up["lender"] == "HDFC Bank"


@pytest.mark.integration
def test_loan_schedule_and_summary_commitment(client: TestClient, user: AuthedUser) -> None:
    u = user

    # Create two loans: EMI 43391.16 and EMI 12500.00 (overridden)
    data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "home",
                "lender": "Bank 1",
                "original_principal": "5000000.00",
                "annual_rate": "8.50",
                "tenure_months": 240,
                "start_date": "2026-11-01",
            },
        )
    )
    data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "car",
                "lender": "Bank 2",
                "original_principal": "500000.00",
                "annual_rate": "9.00",
                "tenure_months": 48,
                "start_date": "2026-11-01",
                "emi_amount": "12500.00",
            },
        )
    )

    # Loan summary: commitment should be 43391.16 + 12500.00 = 55891.16
    summary = data(u.get("/api/v1/loans/summary"))
    assert summary["total_monthly_emi_commitment"] == "55891.16"
    assert summary["active_loans_count"] == 2

    # Schedule test: 1,000,000 at 12% for 12 months
    loan12 = data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "personal",
                "lender": "Axis Bank",
                "original_principal": "1000000.00",
                "annual_rate": "12.00",
                "tenure_months": 12,
                "start_date": "2026-11-01",
                "first_emi_date": "2026-12-01",
            },
        )
    )
    sched = data(u.get(f"/api/v1/loans/{loan12['id']}/schedule"))
    assert sched["total_interest"] == "66185.45"
    assert len(sched["installments"]) == 12

    inst1 = sched["installments"][0]
    assert inst1["installment_no"] == 1
    assert inst1["interest"] == "10000.00"
    assert inst1["principal"] == "78848.79"
    assert inst1["payment"] == "88848.79"
    assert inst1["closing_outstanding"] == "921151.21"

    inst12 = sched["installments"][11]
    assert inst12["installment_no"] == 12
    assert inst12["payment"] == "88848.76"
    assert inst12["closing_outstanding"] == "0.00"


@pytest.mark.integration
def test_confirmed_payment_flow_and_expense_aggregation(
    client: TestClient, user: AuthedUser
) -> None:
    u = user

    acct = create_account(u, "Salary Checking", opening_balance="200000.00")

    loan = data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "personal",
                "lender": "Axis Bank",
                "original_principal": "1000000.00",
                "annual_rate": "12.00",
                "tenure_months": 12,
                "start_date": "2026-11-01",
                "first_emi_date": "2026-12-01",
            },
        )
    )
    loan_id = loan["id"]

    # 1. Verify generic /transactions rejects loan_payment
    resp_generic = u.post(
        "/api/v1/transactions",
        json={
            "type": "loan_payment",
            "account_id": acct["id"],
            "amount": "88848.79",
            "txn_date": "2026-12-01",
        },
    )
    assert resp_generic.status_code == 422

    # 2. Confirm EMI payment for installment 1
    pay_res = data(
        u.post(
            f"/api/v1/loans/{loan_id}/payments",
            json={
                "account_id": acct["id"],
                "payment_date": "2026-12-01",
                "payment_type": "installment",
            },
        )
    )
    assert pay_res["principal"] == "78848.79"
    assert pay_res["interest"] == "10000.00"
    assert pay_res["total_amount"] == "88848.79"
    assert pay_res["current_outstanding"] == "921151.21"

    # 3. Bank balance decreased by 88,848.79: 200,000 - 88,848.79 = 111,151.21
    acct_after = data(u.get(f"/api/v1/accounts/{acct['id']}"))
    assert acct_after["current_balance"] == "111151.21"

    # 4. Expenses report includes ONLY interest component (+10,000.00)
    rep = data(
        u.get(
            "/api/v1/reports/expenses",
            params={"period": "custom", "start": "2026-12-01", "end": "2026-12-31"},
        )
    )
    assert rep["total_expenses"] == "10000.00"

    # 5. Prepayment of 50,000.00
    prep_res = data(
        u.post(
            f"/api/v1/loans/{loan_id}/payments",
            json={
                "account_id": acct["id"],
                "payment_date": "2026-12-15",
                "payment_type": "prepayment",
                "amount": "50000.00",
                "strategy": "reduce_tenure",
            },
        )
    )
    assert prep_res["principal"] == "50000.00"
    assert prep_res["interest"] == "0.00"
    assert prep_res["current_outstanding"] == "871151.21"

    # Prepayment does not increase expenses
    rep2 = data(
        u.get(
            "/api/v1/reports/expenses",
            params={"period": "custom", "start": "2026-12-01", "end": "2026-12-31"},
        )
    )
    assert rep2["total_expenses"] == "10000.00"


@pytest.mark.integration
def test_rate_change_negative_amortization_and_simulation(
    client: TestClient, user: AuthedUser
) -> None:
    u = user

    loan = data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "home",
                "lender": "Home Finance",
                "original_principal": "3000000.00",
                "annual_rate": "8.50",
                "tenure_months": 240,
                "start_date": "2026-11-01",
                "first_emi_date": "2026-12-01",
            },
        )
    )
    loan_id = loan["id"]

    # 1. Simulation leaves loan unchanged
    sim = data(
        u.post(
            f"/api/v1/loans/{loan_id}/simulate",
            json={
                "kind": "extra_monthly_payment",
                "effective_date": "2026-12-01",
                "amount": "5000.00",
            },
        )
    )
    assert Decimal(sim["interest_saved"]) > Decimal("0")
    assert sim["tenure_months_saved"] > 0

    # Verify loan in DB is unchanged
    l_db = data(u.get(f"/api/v1/loans/{loan_id}"))
    assert l_db["tenure_months"] == 240
    assert l_db["current_outstanding"] == "3000000.00"

    # 2. Negative amortization rejection:
    # Rate change to 20% keeping current EMI (26034.67) while interest on 3M is 50,000
    resp_neg = u.post(
        f"/api/v1/loans/{loan_id}/events",
        json={
            "kind": "rate_change",
            "effective_date": "2026-12-01",
            "payload": {"annual_rate": "20.00", "strategy": "keep_emi"},
        },
    )
    assert resp_neg.status_code == 422
    assert "negative_amortization" in resp_neg.text
