import pytest

from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data

SRC = "/api/v1/income-sources"


@pytest.fixture
def bank(user: AuthedUser) -> str:
    return str(create_account(user, "HDFC Savings", "bank", "0.00", "2026-01-01")["id"])


def _source(u: AuthedUser, name: str, type_: str, **kw: object) -> dict[str, object]:
    result: dict[str, object] = data(u.post(SRC, json={"name": name, "type": type_, **kw}))
    return result


# ---- 6.1 ----------------------------------------------------------------------------------


def test_income_sources_crud_and_deactivate(user: AuthedUser, bank: str) -> None:
    acme = _source(
        user,
        "Acme Corp Salary",
        "salary",
        default_category_id=cat_id(user, "Salary", "income"),
        default_account_id=bank,
    )
    free = _source(user, "Freelance Design", "freelance")
    assert {s["name"] for s in data(user.get(SRC))} == {"Acme Corp Salary", "Freelance Design"}
    upd = data(user.patch(f"{SRC}/{free['id']}", json={"is_active": False, "name": "Design"}))
    assert upd["is_active"] is False and upd["name"] == "Design"
    assert [s["name"] for s in data(user.get(SRC))] == ["Acme Corp Salary"]
    assert len(data(user.get(SRC, params={"include_inactive": True}))) == 2
    assert data(user.get(f"{SRC}/{acme['id']}"))["default_account_id"] == bank
    bad = user.post(
        SRC, json={"name": "X", "type": "salary", "default_category_id": cat_id(user, "Food")}
    )
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "category_kind_mismatch"
    assert user.post(SRC, json={"name": "X", "type": "pension"}).status_code == 422


def test_multiple_sources_reported_separately(user: AuthedUser, bank: str) -> None:
    acme = _source(user, "Acme Corp Salary", "salary")
    free = _source(user, "Freelance Design", "freelance")
    salary_cat = cat_id(user, "Salary", "income")
    make_txn(
        user,
        type="income",
        account_id=bank,
        amount="100000.00",
        category_id=salary_cat,
        income_source_id=acme["id"],
        txn_date="2026-03-01",
    )
    make_txn(
        user,
        type="income",
        account_id=bank,
        amount="25000.00",
        category_id=cat_id(user, "Freelance", "income"),
        income_source_id=free["id"],
        txn_date="2026-03-10",
    )
    by_source = data(
        user.get(
            "/api/v1/reports/income",
            params={"period": "custom", "start": "2026-03-01", "end": "2026-03-31"},
        )
    )["by_source"]
    assert [(s["name"], s["total"]) for s in by_source] == [
        ("Acme Corp Salary", "100000.00"),
        ("Freelance Design", "25000.00"),
    ]
    listed = data(user.get("/api/v1/transactions", params={"income_source_id": free["id"]}))
    assert [t["amount"] for t in listed] == ["25000.00"]
    expense_with_source = user.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": bank,
            "amount": "1.00",
            "txn_date": "2026-03-01",
            "category_id": cat_id(user, "Food"),
            "payment_method": "upi",
            "income_source_id": acme["id"],
        },
    )
    assert expense_with_source.status_code == 422


# ---- 6.2 ----------------------------------------------------------------------------------

BREAKDOWN = {
    "gross": "150000.00",
    "deductions": [
        {"name": "Income Tax/TDS", "amount": "25000.00"},
        {"name": "EPF employee contribution", "amount": "1800.00"},
        {"name": "Professional Tax", "amount": "200.00"},
    ],
}


def test_valid_salary_breakdown(user: AuthedUser, bank: str) -> None:
    t = make_txn(
        user,
        type="income",
        account_id=bank,
        amount="123000.00",
        category_id=cat_id(user, "Salary", "income"),
        salary_breakdown=BREAKDOWN,
        txn_date="2026-11-01",
    )
    b = t["salary_breakdown"]
    assert b["gross"] == "150000.00" and b["total_deductions"] == "27000.00"  # type: ignore[index]
    assert b["net"] == "123000.00"  # type: ignore[index]
    assert [d["name"] for d in b["deductions"]] == [  # type: ignore[index]
        "Income Tax/TDS",
        "EPF employee contribution",
        "Professional Tax",
    ]
    assert data(user.get(f"/api/v1/accounts/{bank}"))["current_balance"] == "123000.00"


def test_salary_breakdown_mismatch(user: AuthedUser, bank: str) -> None:
    resp = user.post(
        "/api/v1/transactions",
        json={
            "type": "income",
            "account_id": bank,
            "amount": "125000.00",
            "txn_date": "2026-11-01",
            "category_id": cat_id(user, "Salary", "income"),
            "salary_breakdown": BREAKDOWN,
        },
    )
    assert resp.status_code == 422
    err = resp.json()["error"]
    assert err["code"] == "salary_breakdown_mismatch"
    assert err["details"][0]["expected_net"] == "123000.00"


def test_breakdown_only_on_income_and_update_revalidates(user: AuthedUser, bank: str) -> None:
    bad = user.post(
        "/api/v1/transactions",
        json={
            "type": "expense",
            "account_id": bank,
            "amount": "123000.00",
            "txn_date": "2026-11-01",
            "category_id": cat_id(user, "Food"),
            "payment_method": "upi",
            "salary_breakdown": BREAKDOWN,
        },
    )
    assert bad.status_code == 422
    t = make_txn(
        user,
        type="income",
        account_id=bank,
        amount="123000.00",
        category_id=cat_id(user, "Salary", "income"),
        salary_breakdown=BREAKDOWN,
    )
    # Changing the amount alone now contradicts the stored breakdown.
    resp = user.patch(f"/api/v1/transactions/{t['id']}", json={"amount": "120000.00"})
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "salary_breakdown_mismatch"
    cleared = data(
        user.patch(
            f"/api/v1/transactions/{t['id']}",
            json={"amount": "120000.00", "salary_breakdown": None},
        )
    )
    assert cleared["salary_breakdown"] is None and cleared["amount"] == "120000.00"


def test_tds_is_not_an_expense(user: AuthedUser, bank: str) -> None:
    make_txn(
        user,
        type="income",
        account_id=bank,
        amount="123000.00",
        category_id=cat_id(user, "Salary", "income"),
        salary_breakdown=BREAKDOWN,
        txn_date="2026-11-01",
    )
    params = {"period": "this_month", "as_of": "2026-11-15"}
    ov = data(user.get("/api/v1/dashboard/overview", params=params))
    assert ov["expenses"]["value"] == "0.00"
    assert ov["income"]["value"] == "123000.00"  # counted at net
    assert data(user.get("/api/v1/reports/expenses", params=params))["total_expenses"] == "0.00"


# ---- 6.4 ----------------------------------------------------------------------------------


def test_annual_income_report(user: AuthedUser, bank: str) -> None:
    acme = _source(user, "Acme Corp Salary", "salary")
    free = _source(user, "Freelance Design", "freelance")
    salary_cat = cat_id(user, "Salary", "income")
    for month in (1, 2, 3):
        make_txn(
            user,
            type="income",
            account_id=bank,
            amount="123000.00",
            category_id=salary_cat,
            income_source_id=acme["id"],
            salary_breakdown=BREAKDOWN,
            txn_date=f"2026-{month:02d}-01",
        )
    make_txn(
        user,
        type="income",
        account_id=bank,
        amount="40000.00",
        category_id=cat_id(user, "Freelance", "income"),
        income_source_id=free["id"],
        txn_date="2026-02-20",
    )
    make_txn(
        user,
        type="income",
        account_id=bank,
        amount="999.00",
        category_id=salary_cat,
        txn_date="2025-12-31",
    )  # outside the year
    params = {"period": "this_year", "as_of": "2026-06-01"}
    r = data(user.get("/api/v1/reports/income", params=params))
    assert r["period"]["label"] == "2026"
    assert r["total_income"] == "409000.00"
    months = {m["month"]: m["income"] for m in r["months"]}
    assert len(months) == 12
    assert months["2026-01"] == "123000.00" and months["2026-02"] == "163000.00"
    assert months["2026-04"] == "0.00"
    assert [(s["name"], s["total"]) for s in r["by_source"]] == [
        ("Acme Corp Salary", "369000.00"),
        ("Freelance Design", "40000.00"),
    ]
    sal = r["salary"]
    assert (sal["gross"], sal["total_deductions"], sal["net"]) == (
        "450000.00",
        "81000.00",
        "369000.00",
    )
    assert sal["deductions"][0] == {"name": "Income Tax/TDS", "amount": "75000.00"}
    csv_text = user.get("/api/v1/reports/income/export.csv", params=params).text
    lines = csv_text.splitlines()
    assert lines[0] == "month,net_income,salary_gross,salary_deductions,salary_net"
    assert "2026-02,163000.00,150000.00,27000.00,123000.00" in lines
    assert "total,409000.00,450000.00,81000.00,369000.00" in lines
