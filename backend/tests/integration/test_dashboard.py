from datetime import date

import pytest

from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data

NOV = {"period": "this_month", "as_of": "2026-11-15"}


@pytest.fixture
def ids(user: AuthedUser) -> dict[str, str]:
    bank = create_account(user, "HDFC Savings", "bank", "10000.00", "2025-01-01")
    card = create_account(user, "Card", "credit_card", "0.00", "2025-01-01")
    cash = create_account(user, "Cash", "cash", "500.00", "2025-01-01")
    return {
        "bank": str(bank["id"]),
        "card": str(card["id"]),
        "cash": str(cash["id"]),
        "salary": cat_id(user, "Salary", "income"),
        "food": cat_id(user, "Food"),
        "rent": cat_id(user, "Rent"),
        "shopping": cat_id(user, "Shopping"),
    }


def _inc(u: AuthedUser, ids: dict[str, str], amount: str, d: str) -> None:
    make_txn(
        u,
        type="income",
        account_id=ids["bank"],
        amount=amount,
        category_id=ids["salary"],
        txn_date=d,
        description=f"salary {d}",
    )


def _exp(
    u: AuthedUser,
    ids: dict[str, str],
    amount: str,
    d: str,
    cat: str = "food",
    method: str = "upi",
    account: str = "bank",
) -> None:
    make_txn(
        u,
        type="expense",
        account_id=ids[account],
        amount=amount,
        category_id=ids[cat],
        payment_method=method,
        txn_date=d,
        description=f"{cat} {amount} {d}",
    )


# ---- 7.1 overview ---------------------------------------------------------------------------


def test_november_vs_october(user: AuthedUser, ids: dict[str, str]) -> None:
    _inc(user, ids, "100000.00", "2026-10-01")
    _exp(user, ids, "60000.00", "2026-10-05")
    _inc(user, ids, "120000.00", "2026-11-01")
    _exp(user, ids, "90000.00", "2026-11-05")
    _exp(user, ids, "500.00", "2026-10-31")  # back-dated, belongs to October
    ov = data(user.get("/api/v1/dashboard/overview", params=NOV))
    assert ov["period"]["label"] == "Nov 2026" and ov["previous_period"]["label"] == "Oct 2026"
    assert ov["income"] == {
        "value": "120000.00",
        "previous": "100000.00",
        "change": "20.00",
        "change_kind": "percent",
    }
    assert ov["expenses"]["value"] == "90000.00" and ov["expenses"]["previous"] == "60500.00"
    assert ov["savings"]["value"] == "30000.00" and ov["savings"]["previous"] == "39500.00"
    assert ov["savings_rate"]["value"] == "25.00" and ov["savings_rate"]["previous"] == "39.50"
    assert ov["savings_rate"]["change"] == "-14.50"
    assert ov["savings_rate"]["change_kind"] == "points"
    # Liquid funds: bank + cash, as of mid-November vs end of October.
    assert ov["liquid_funds"]["value"] == "80000.00"
    assert ov["liquid_funds"]["previous"] == "50000.00"
    assert ov["has_transactions"] is True


def test_zero_base_change_is_null(user: AuthedUser, ids: dict[str, str]) -> None:
    _inc(user, ids, "1000.00", "2026-11-02")
    ov = data(user.get("/api/v1/dashboard/overview", params=NOV))
    assert ov["income"]["previous"] == "0.00" and ov["income"]["change"] is None
    assert ov["savings_rate"]["previous"] is None and ov["savings_rate"]["change"] is None


def test_new_user_empty_state(user: AuthedUser) -> None:
    ov = data(user.get("/api/v1/dashboard/overview", params=NOV))
    assert ov["has_transactions"] is False and ov["has_accounts"] is False
    assert ov["income"]["value"] == "0.00" and ov["savings_rate"]["value"] is None


def test_card_purchase_and_bill_same_month_counted_once(
    user: AuthedUser, ids: dict[str, str]
) -> None:
    _exp(user, ids, "15000.00", "2026-11-03", cat="shopping", method="credit_card", account="card")
    make_txn(
        user,
        type="transfer",
        account_id=ids["bank"],
        counter_account_id=ids["card"],
        amount="15000.00",
        txn_date="2026-11-20",
    )
    ov = data(user.get("/api/v1/dashboard/overview", params=NOV))
    assert ov["expenses"]["value"] == "15000.00"


def test_custom_range_inclusive(user: AuthedUser, ids: dict[str, str]) -> None:
    _exp(user, ids, "1.00", "2026-07-14")
    _exp(user, ids, "2.00", "2026-07-15")
    _exp(user, ids, "4.00", "2026-09-15")
    _exp(user, ids, "8.00", "2026-09-16")
    params = {"period": "custom", "start": "2026-07-15", "end": "2026-09-15"}
    assert (
        data(user.get("/api/v1/dashboard/overview", params=params))["expenses"]["value"] == "6.00"
    )
    trend = data(user.get("/api/v1/dashboard/trends", params=params))["months"]
    assert [m["month"] for m in trend] == ["2026-07", "2026-08", "2026-09"]
    assert [m["expenses"] for m in trend] == ["2.00", "0.00", "4.00"]
    bad = user.get("/api/v1/dashboard/overview", params={"period": "custom"})
    assert bad.status_code == 422


def test_financial_year_filter(user: AuthedUser, ids: dict[str, str]) -> None:
    _exp(user, ids, "10.00", "2026-03-31")
    _exp(user, ids, "20.00", "2026-04-01")
    _exp(user, ids, "40.00", "2027-03-31")
    ov = data(
        user.get("/api/v1/dashboard/overview", params={"period": "this_fy", "as_of": "2026-11-15"})
    )
    assert ov["period"]["label"] == "FY 2026-27" and ov["expenses"]["value"] == "60.00"
    assert ov["expenses"]["previous"] == "10.00"


# ---- 7.2 trends + breakdown ------------------------------------------------------------------


def test_trends_last_12_months_with_zero_months(user: AuthedUser, ids: dict[str, str]) -> None:
    d = date(2025, 6, 1)
    for i in range(18):
        y, m = divmod(d.month - 1 + i, 12)
        month = f"{d.year + y}-{m + 1:02d}"
        if month == "2026-05":
            continue  # a month with no activity
        _inc(user, ids, "1000.00", f"{month}-01")
        if month != "2026-08":
            _exp(user, ids, "250.00", f"{month}-10")
    months = data(user.get("/api/v1/dashboard/trends", params=NOV))["months"]
    assert len(months) == 12
    assert months[0]["month"] == "2025-12" and months[-1]["month"] == "2026-11"
    may = next(m for m in months if m["month"] == "2026-05")
    assert may == {
        "month": "2026-05",
        "label": "May 2026",
        "income": "0.00",
        "expenses": "0.00",
        "savings": "0.00",
        "savings_rate": None,
    }
    aug = next(m for m in months if m["month"] == "2026-08")
    assert aug["savings_rate"] == "100.00"
    assert months[-1]["savings_rate"] == "75.00"


def test_category_breakdown_top6_plus_other(user: AuthedUser, ids: dict[str, str]) -> None:
    names = [
        "Food",
        "Rent",
        "Shopping",
        "Travel",
        "Healthcare",
        "Utilities",
        "Fuel",
        "Entertainment",
    ]
    for i, name in enumerate(names):
        make_txn(
            user,
            type="expense",
            account_id=ids["bank"],
            amount=f"{(8 - i) * 100}.00",
            category_id=cat_id(user, name),
            payment_method="upi",
            txn_date="2026-11-05",
        )
    groceries = data(
        user.post(
            "/api/v1/categories",
            json={"kind": "expense", "name": "Groceries", "parent_id": ids["food"]},
        )
    )
    make_txn(
        user,
        type="expense",
        account_id=ids["bank"],
        amount="50.00",
        category_id=groceries["id"],
        payment_method="upi",
        txn_date="2026-11-06",
    )
    b = data(user.get("/api/v1/dashboard/category-breakdown", params=NOV))
    assert b["total_expenses"] == "3650.00"
    cats = b["categories"]
    assert len(cats) == 7
    assert cats[0]["name"] == "Food" and cats[0]["total"] == "850.00"  # incl. subcategory
    assert cats[-1] == {
        "category_id": None,
        "name": "Other categories",
        "color": None,
        "total": "300.00",
        "share": "8.22",
        "is_other": True,
    }
    assert cats[0]["category_id"] == ids["food"]


# ---- 7.3 reports ------------------------------------------------------------------------------


def test_expense_report_by_method_sums_to_total(user: AuthedUser, ids: dict[str, str]) -> None:
    oct_ = {"period": "custom", "start": "2026-10-01", "end": "2026-10-31"}
    _exp(user, ids, "100.00", "2026-10-02", method="upi")
    _exp(user, ids, "200.00", "2026-10-03", method="cash", account="cash")
    _exp(user, ids, "300.00", "2026-10-04", method="debit_card")
    _exp(user, ids, "400.00", "2026-10-05", cat="shopping", method="credit_card", account="card")
    _exp(user, ids, "500.00", "2026-10-06", cat="rent", method="bank_transfer")
    shop = data(user.get("/api/v1/transactions", params={"payment_method": "credit_card"}))[0]
    make_txn(
        user,
        type="refund",
        account_id=ids["card"],
        amount="150.00",
        category_id=ids["shopping"],
        refund_of_id=shop["id"],
        txn_date="2026-10-20",
    )
    r = data(user.get("/api/v1/reports/expenses", params=oct_))
    assert r["total_expenses"] == "1350.00"
    methods = {m["method"]: m["total"] for m in r["by_payment_method"]}
    assert methods == {
        "upi": "100.00",
        "cash": "200.00",
        "debit_card": "300.00",
        "credit_card": "250.00",
        "bank_transfer": "500.00",
        "other": "0.00",
    }
    assert sum(float(v) for v in methods.values()) == 1350.00
    cats = {c["name"]: c["total"] for c in r["by_category"]}
    assert cats["Shopping"] == "250.00" and cats["Rent"] == "500.00"
    csv_text = user.get("/api/v1/reports/expenses/export.csv", params=oct_).text
    assert "payment_method,credit_card,,250.00,18.52" in csv_text
    assert "total,,,1350.00,100.00" in csv_text


def test_savings_trend_report_and_csv(user: AuthedUser, ids: dict[str, str]) -> None:
    _inc(user, ids, "1000.00", "2026-11-01")
    _exp(user, ids, "250.00", "2026-11-02")
    t = data(user.get("/api/v1/reports/savings-trend", params=NOV))
    assert t["months"][-1]["savings_rate"] == "75.00" and len(t["months"]) == 12
    csv_text = user.get("/api/v1/reports/savings-trend/export.csv", params=NOV).text
    assert csv_text.splitlines()[-1] == "2026-11,1000.00,250.00,750.00,75.00"
    assert ",0.00,0.00,0.00," in csv_text  # zero months have an empty rate


def test_archived_account_history_still_reported(user: AuthedUser, ids: dict[str, str]) -> None:
    _exp(user, ids, "700.00", "2025-06-01", account="cash", method="cash")
    user.post(f"/api/v1/accounts/{ids['cash']}/archive")
    r = data(
        user.get("/api/v1/reports/expenses", params={"period": "this_year", "as_of": "2025-07-01"})
    )
    assert r["total_expenses"] == "700.00"


# ---- 7.4 consistency ----------------------------------------------------------------------------


def test_dashboard_and_reports_identical(user: AuthedUser, ids: dict[str, str]) -> None:
    _inc(user, ids, "98765.43", "2026-10-01")
    _exp(user, ids, "1234.57", "2026-10-02")
    _exp(user, ids, "0.10", "2026-10-03")
    _exp(user, ids, "0.20", "2026-10-04")
    _exp(user, ids, "999.99", "2026-10-05", cat="shopping")
    make_txn(
        user,
        type="refund",
        account_id=ids["bank"],
        amount="99.99",
        category_id=ids["shopping"],
        txn_date="2026-10-06",
    )
    p = {"period": "last_month", "as_of": "2026-11-15"}
    ov = data(user.get("/api/v1/dashboard/overview", params=p))
    rep = data(user.get("/api/v1/reports/expenses", params=p))
    inc = data(user.get("/api/v1/reports/income", params=p))
    trend = data(user.get("/api/v1/reports/savings-trend", params=p))["months"][-1]
    dash_trend = data(user.get("/api/v1/dashboard/trends", params=p))["months"][-1]
    breakdown = data(user.get("/api/v1/dashboard/category-breakdown", params=p))
    listing = user.get(
        "/api/v1/transactions", params={"date_from": "2026-10-01", "date_to": "2026-10-31"}
    ).json()["meta"]["totals"]
    assert (
        ov["expenses"]["value"]
        == rep["total_expenses"]
        == trend["expenses"]
        == dash_trend["expenses"]
        == breakdown["total_expenses"]
        == listing["net_expense"]
        == "2134.87"
    )
    assert ov["income"]["value"] == inc["total_income"] == trend["income"] == "98765.43"
    assert ov["savings"]["value"] == trend["savings"] == "96630.56"
    assert ov["savings_rate"]["value"] == trend["savings_rate"] == "97.84"
    assert {c["name"]: c["total"] for c in rep["by_category"]} == {
        c["name"]: c["total"] for c in breakdown["categories"]
    }
