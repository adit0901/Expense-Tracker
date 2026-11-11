from decimal import Decimal

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.transaction import Transaction
from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data

URL = "/api/v1/transactions"


def _balance(u: AuthedUser, account_id: object) -> str:
    return str(data(u.get(f"/api/v1/accounts/{account_id}"))["current_balance"])


@pytest.fixture
def setup(user: AuthedUser) -> dict[str, str]:
    bank = create_account(user, "HDFC Savings", "bank", "50000.00", "2026-01-01")
    card = create_account(user, "HDFC Card", "credit_card", "0.00", "2026-01-01")
    cash = create_account(user, "Cash", "cash", "2000.00", "2026-01-01")
    wallet = create_account(user, "Paytm", "wallet", "0.00", "2026-01-01")
    return {
        "bank": str(bank["id"]),
        "card": str(card["id"]),
        "cash": str(cash["id"]),
        "wallet": str(wallet["id"]),
        "food": cat_id(user, "Food"),
        "shopping": cat_id(user, "Shopping"),
        "salary": cat_id(user, "Salary", "income"),
    }


# ---- 5.2 balances --------------------------------------------------------------------------


def test_balance_after_income_and_expenses(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="income",
        account_id=setup["bank"],
        amount="80000.00",
        category_id=setup["salary"],
    )
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="12000.00",
        category_id=setup["food"],
        payment_method="upi",
    )
    assert _balance(user, setup["bank"]) == "118000.00"


def test_accounts_summary_scenario(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="income",
        account_id=setup["bank"],
        amount="80000.00",
        category_id=setup["salary"],
    )
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="2000.00",
        category_id=setup["food"],
        payment_method="upi",
    )
    make_txn(
        user,
        type="expense",
        account_id=setup["card"],
        amount="15000.00",
        category_id=setup["shopping"],
        payment_method="credit_card",
    )
    make_txn(
        user,
        type="transfer",
        account_id=setup["bank"],
        counter_account_id=setup["card"],
        amount="10000.00",
    )
    assert _balance(user, setup["bank"]) == "118000.00"
    assert _balance(user, setup["card"]) == "5000.00"
    summary = data(user.get("/api/v1/accounts/summary"))
    assert summary["liquid_funds"] == "120000.00"
    assert summary["credit_card_outstanding"] == "5000.00"
    assert summary["bank_balance"] == "118000.00" and summary["cash_balance"] == "2000.00"


def test_transactions_before_opening_date_ignored(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="100.00",
        category_id=setup["food"],
        payment_method="upi",
        txn_date="2025-12-31",
    )
    assert _balance(user, setup["bank"]) == "50000.00"


def test_archived_account_excluded_from_summary(user: AuthedUser, setup: dict[str, str]) -> None:
    user.post(f"/api/v1/accounts/{setup['cash']}/archive")
    assert data(user.get("/api/v1/accounts/summary"))["liquid_funds"] == "50000.00"


# ---- 5.3 create/read/update/delete ---------------------------------------------------------


def test_create_expense(user: AuthedUser, setup: dict[str, str]) -> None:
    t = make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="450.00",
        category_id=setup["food"],
        payment_method="upi",
        txn_date="2026-11-10",
        payee="Swiggy",
        description="Dinner",
        tags=["Weekend", "weekend"],
    )
    assert t["amount"] == "450.00" and t["currency"] == "INR"
    assert t["category_name"] == "Food" and t["account_name"] == "HDFC Savings"
    assert t["tags"] == ["weekend"]
    assert _balance(user, setup["bank"]) == "49550.00"
    assert data(user.get(f"{URL}/{t['id']}"))["id"] == t["id"]


@pytest.mark.parametrize("amount", ["0", "-100", "10.555"])
def test_invalid_amounts(user: AuthedUser, setup: dict[str, str], amount: str) -> None:
    resp = user.post(
        URL,
        json={
            "type": "expense",
            "account_id": setup["bank"],
            "amount": amount,
            "category_id": setup["food"],
            "payment_method": "upi",
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["details"][0]["field"] == "amount"


def test_missing_amount(user: AuthedUser, setup: dict[str, str]) -> None:
    resp = user.post(
        URL,
        json={
            "type": "expense",
            "account_id": setup["bank"],
            "category_id": setup["food"],
            "payment_method": "upi",
            "txn_date": "2026-11-10",
        },
    )
    err = resp.json()["error"]
    assert resp.status_code == 422 and err["code"] == "validation_error"
    assert any(d["field"] == "amount" for d in err["details"])


def test_decimal_precision_preserved(user: AuthedUser, setup: dict[str, str]) -> None:
    for a in ["0.10", "0.20", "0.30"]:
        make_txn(
            user,
            type="expense",
            account_id=setup["bank"],
            amount=a,
            category_id=setup["food"],
            payment_method="cash",
            payee=f"p{a}",
        )
    assert _balance(user, setup["bank"]) == "49999.40"


def test_category_kind_mismatch(user: AuthedUser, setup: dict[str, str]) -> None:
    resp = user.post(
        URL,
        json={
            "type": "expense",
            "account_id": setup["bank"],
            "amount": "10.00",
            "category_id": setup["salary"],
            "payment_method": "upi",
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "category_kind_mismatch"


def test_card_method_with_bank_account(user: AuthedUser, setup: dict[str, str]) -> None:
    resp = user.post(
        URL,
        json={
            "type": "expense",
            "account_id": setup["bank"],
            "amount": "10.00",
            "category_id": setup["food"],
            "payment_method": "credit_card",
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "payment_method_account_mismatch"


def test_expense_requires_payment_method(user: AuthedUser, setup: dict[str, str]) -> None:
    resp = user.post(
        URL,
        json={
            "type": "expense",
            "account_id": setup["bank"],
            "amount": "10.00",
            "category_id": setup["food"],
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["details"][0]["field"] == "payment_method"


def test_card_bill_payment_is_transfer(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="expense",
        account_id=setup["card"],
        amount="15000.00",
        category_id=setup["shopping"],
        payment_method="credit_card",
    )
    t = make_txn(
        user,
        type="transfer",
        account_id=setup["bank"],
        counter_account_id=setup["card"],
        amount="10000.00",
        payment_method="bank_transfer",
    )
    assert t["type"] == "transfer" and t["category_id"] is None
    assert t["counter_account_name"] == "HDFC Card"
    assert _balance(user, setup["card"]) == "5000.00"
    assert _balance(user, setup["bank"]) == "40000.00"


def test_wallet_transfer_updates_both(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="transfer",
        account_id=setup["bank"],
        counter_account_id=setup["wallet"],
        amount="20000.00",
    )
    assert _balance(user, setup["bank"]) == "30000.00"
    assert _balance(user, setup["wallet"]) == "20000.00"


def test_same_account_transfer(user: AuthedUser, setup: dict[str, str]) -> None:
    resp = user.post(
        URL,
        json={
            "type": "transfer",
            "account_id": setup["bank"],
            "counter_account_id": setup["bank"],
            "amount": "1.00",
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "same_account_transfer"


def test_transfer_with_category_rejected(user: AuthedUser, setup: dict[str, str]) -> None:
    resp = user.post(
        URL,
        json={
            "type": "transfer",
            "account_id": setup["bank"],
            "counter_account_id": setup["cash"],
            "amount": "1.00",
            "category_id": setup["food"],
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422


def test_refund_reduces_balance_effect(user: AuthedUser, setup: dict[str, str]) -> None:
    exp = make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="3000.00",
        category_id=setup["shopping"],
        payment_method="upi",
    )
    r = make_txn(
        user,
        type="refund",
        account_id=setup["bank"],
        amount="1000.00",
        category_id=setup["shopping"],
        refund_of_id=exp["id"],
    )
    assert r["refund_of_id"] == exp["id"]
    assert _balance(user, setup["bank"]) == "48000.00"
    bad = user.post(
        URL,
        json={
            "type": "refund",
            "account_id": setup["bank"],
            "amount": "1.00",
            "category_id": setup["salary"],
            "txn_date": "2026-10-15",
        },
    )
    assert bad.status_code == 422


def test_archived_account_rejected_for_new_entries(user: AuthedUser, setup: dict[str, str]) -> None:
    user.post(f"/api/v1/accounts/{setup['cash']}/archive")
    resp = user.post(
        URL,
        json={
            "type": "expense",
            "account_id": setup["cash"],
            "amount": "1.00",
            "category_id": setup["food"],
            "payment_method": "cash",
            "txn_date": "2026-11-10",
        },
    )
    assert resp.status_code == 422 and resp.json()["error"]["code"] == "account_archived"


def test_update_and_audit(user: AuthedUser, setup: dict[str, str], db: Session) -> None:
    t = make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="450.00",
        category_id=setup["food"],
        payment_method="upi",
    )
    out = data(user.patch(f"{URL}/{t['id']}", json={"amount": "500.00", "notes": "fixed"}))
    assert out["amount"] == "500.00" and out["notes"] == "fixed"
    assert _balance(user, setup["bank"]) == "49500.00"
    entry = db.scalars(
        select(AuditLog).where(AuditLog.entity_id == t["id"], AuditLog.action == "update")
    ).one()
    assert entry.changed_fields == ["amount", "notes"]
    # Changing to a transfer requires clearing the category.
    bad = user.patch(
        f"{URL}/{t['id']}", json={"type": "transfer", "counter_account_id": setup["cash"]}
    )
    assert bad.status_code == 422
    ok = data(
        user.patch(
            f"{URL}/{t['id']}",
            json={"type": "transfer", "category_id": None, "counter_account_id": setup["cash"]},
        )
    )
    assert ok["type"] == "transfer"


def test_update_validation_error_keeps_record(user: AuthedUser, setup: dict[str, str]) -> None:
    t = make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="450.00",
        category_id=setup["food"],
        payment_method="upi",
    )
    assert user.patch(f"{URL}/{t['id']}", json={"amount": "-1"}).status_code == 422
    assert user.patch(f"{URL}/{t['id']}", json={"amount": None}).status_code == 422
    assert data(user.get(f"{URL}/{t['id']}"))["amount"] == "450.00"


def test_delete_restores_balance(user: AuthedUser, setup: dict[str, str], db: Session) -> None:
    t = make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="450.00",
        category_id=setup["food"],
        payment_method="upi",
    )
    assert _balance(user, setup["bank"]) == "49550.00"
    assert user.delete(f"{URL}/{t['id']}").status_code == 204
    assert _balance(user, setup["bank"]) == "50000.00"
    assert user.get(f"{URL}/{t['id']}").status_code == 404
    actions = db.scalars(select(AuditLog.action).where(AuditLog.entity_id == t["id"])).all()
    assert sorted(actions) == ["create", "delete"]


# ---- 5.4 search / filter ------------------------------------------------------------------


def test_filter_food_in_october_includes_subcategories(
    user: AuthedUser, setup: dict[str, str]
) -> None:
    groceries = data(
        user.post(
            "/api/v1/categories",
            json={"kind": "expense", "name": "Groceries", "parent_id": setup["food"]},
        )
    )
    base = {"type": "expense", "account_id": setup["bank"], "payment_method": "upi"}
    make_txn(
        user, **base, amount="100.00", category_id=setup["food"], txn_date="2026-10-01", payee="a"
    )
    make_txn(
        user, **base, amount="250.50", category_id=groceries["id"], txn_date="2026-10-31", payee="b"
    )
    make_txn(
        user, **base, amount="999.00", category_id=setup["food"], txn_date="2026-11-01", payee="c"
    )
    make_txn(
        user,
        **base,
        amount="77.00",
        category_id=setup["shopping"],
        txn_date="2026-10-15",
        payee="d",
    )
    resp = user.get(
        URL,
        params={
            "category_id": setup["food"],
            "type": "expense",
            "date_from": "2026-10-01",
            "date_to": "2026-10-31",
        },
    )
    body = resp.json()
    assert sorted(t["amount"] for t in body["data"]) == ["100.00", "250.50"]
    assert body["meta"]["totals"]["expense"] == "350.50"
    assert body["meta"]["total_items"] == 2
    assert [t["txn_date"] for t in body["data"]] == ["2026-10-31", "2026-10-01"]  # date desc
    sub = next(t for t in body["data"] if t["category_name"] == "Groceries")
    assert sub["parent_category_name"] == "Food"


def test_filters_method_amount_tag_account_text(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="100.00",
        category_id=setup["food"],
        payment_method="upi",
        tags=["office"],
        description="Team lunch at 50% off",
    )
    make_txn(
        user,
        type="expense",
        account_id=setup["cash"],
        amount="500.00",
        category_id=setup["food"],
        payment_method="cash",
        notes="birthday dinner",
    )
    make_txn(
        user,
        type="transfer",
        account_id=setup["bank"],
        counter_account_id=setup["wallet"],
        amount="300.00",
    )

    def ids(**params: object) -> list[str]:
        return [t["amount"] for t in data(user.get(URL, params=params))]

    assert ids(payment_method="cash") == ["500.00"]
    assert sorted(ids(amount_min="150", amount_max="600")) == ["300.00", "500.00"]
    assert ids(tag="OFFICE") == ["100.00"]
    assert ids(q="birthday") == ["500.00"]
    assert ids(q="50%") == ["100.00"]
    assert ids(q="_") == []
    assert sorted(ids(account_id=setup["wallet"])) == ["300.00"]
    assert sorted(ids(type=["transfer", "expense"])) == ["100.00", "300.00", "500.00"]


def test_sql_meta_characters_in_search(
    user: AuthedUser, setup: dict[str, str], db: Session
) -> None:
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="1.00",
        category_id=setup["food"],
        payment_method="upi",
        description="normal",
    )
    resp = user.get(URL, params={"q": "'; DROP TABLE users; --"})
    assert resp.status_code == 200 and resp.json()["data"] == []
    assert db.scalar(select(func.count()).select_from(Transaction)) >= 1


def test_sort_allow_list(user: AuthedUser, setup: dict[str, str]) -> None:
    for a in ["5.00", "50.00", "20.00"]:
        make_txn(
            user,
            type="expense",
            account_id=setup["bank"],
            amount=a,
            category_id=setup["food"],
            payment_method="upi",
            payee=a,
        )
    assert [t["amount"] for t in data(user.get(URL, params={"sort": "amount"}))] == [
        "5.00",
        "20.00",
        "50.00",
    ]
    assert user.get(URL, params={"sort": "notes"}).json()["error"]["code"] == "invalid_sort"


# ---- 5.5 duplicates -----------------------------------------------------------------------


def test_duplicate_warning_and_confirmed_save(user: AuthedUser, setup: dict[str, str]) -> None:
    body = {
        "type": "expense",
        "account_id": setup["bank"],
        "amount": "450.00",
        "category_id": setup["food"],
        "payment_method": "upi",
        "txn_date": "2026-11-10",
        "payee": "Swiggy",
    }
    make_txn(user, **body)
    next_day = {**body, "txn_date": "2026-11-11", "payee": "SWIGGY "}
    check = data(user.post(f"{URL}/duplicate-check", json=next_day))
    assert check["is_possible_duplicate"] is True and len(check["candidates"]) == 1
    resp = user.post(URL, json=next_day)
    assert resp.status_code == 409
    assert resp.json()["error"]["code"] == "possible_duplicate"
    assert len(data(user.get(URL))) == 1  # nothing saved
    saved = user.post(URL, json={**next_day, "confirm_duplicate": True})
    assert saved.status_code == 201
    assert len(data(user.get(URL))) == 2


def test_not_duplicate_when_different(user: AuthedUser, setup: dict[str, str]) -> None:
    body = {
        "type": "expense",
        "account_id": setup["bank"],
        "amount": "450.00",
        "category_id": setup["food"],
        "payment_method": "upi",
        "txn_date": "2026-11-10",
        "payee": "Swiggy",
    }
    make_txn(user, **body)
    for variant in [
        {"txn_date": "2026-11-12"},
        {"amount": "451.00"},
        {"payee": "Amazon Pay"},
        {"account_id": setup["cash"], "payment_method": "cash"},
    ]:
        check = data(user.post(f"{URL}/duplicate-check", json={**body, **variant}))
        assert check["is_possible_duplicate"] is False, variant


# ---- 5.6 idempotency ----------------------------------------------------------------------


def test_idempotency_key_creates_once(user: AuthedUser, setup: dict[str, str]) -> None:
    body = {
        "type": "expense",
        "account_id": setup["bank"],
        "amount": "99.00",
        "category_id": setup["food"],
        "payment_method": "upi",
        "txn_date": "2026-11-10",
    }
    h = {"Idempotency-Key": "retry-abc-123"}
    r1 = user.post(URL, json=body, headers=h)
    r2 = user.post(URL, json=body, headers=h)
    assert r1.status_code == r2.status_code == 201
    assert r1.json()["data"]["id"] == r2.json()["data"]["id"]
    assert r2.headers.get("Idempotent-Replayed") == "true"
    assert len(data(user.get(URL))) == 1
    reused = user.post(URL, json={**body, "amount": "1.00"}, headers=h)
    assert reused.status_code == 422
    assert reused.json()["error"]["code"] == "idempotency_key_reused"


# ---- 5.8 CSV export -----------------------------------------------------------------------


def test_csv_export_escapes_formulas(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="1250.50",
        category_id=setup["food"],
        payment_method="upi",
        txn_date="2026-10-05",
        description='=HYPERLINK("x")',
        payee="+cmd",
        notes="@sum",
    )
    resp = user.get(f"{URL}/export.csv", params={"date_from": "2026-10-01"})
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    lines = resp.text.splitlines()
    assert lines[0].startswith("date,type,account")
    assert "2026-10-05,expense,HDFC Savings,,Food,,1250.50,INR,upi,'+cmd" in lines[1]
    assert '"\'=HYPERLINK(""x"")"' in lines[1]
    assert "'@sum" in lines[1]


def test_csv_export_respects_filters(user: AuthedUser, setup: dict[str, str]) -> None:
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="1.00",
        category_id=setup["food"],
        payment_method="upi",
        txn_date="2026-09-01",
    )
    make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="2.00",
        category_id=setup["food"],
        payment_method="upi",
        txn_date="2026-10-01",
    )
    text = user.get(f"{URL}/export.csv", params={"date_from": "2026-10-01"}).text
    assert len(text.splitlines()) == 2 and ",2.00," in text


def test_amount_values_are_exact(user: AuthedUser, setup: dict[str, str], db: Session) -> None:
    t = make_txn(
        user,
        type="expense",
        account_id=setup["bank"],
        amount="1250.5",
        category_id=setup["food"],
        payment_method="upi",
    )
    assert t["amount"] == "1250.50"
    stored = db.scalar(select(Transaction.amount).where(Transaction.id == t["id"]))
    assert stored == Decimal("1250.5")
