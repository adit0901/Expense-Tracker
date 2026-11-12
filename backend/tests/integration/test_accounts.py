from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import TransactionType
from tests.factories import category_id, create_account, insert_txn
from tests.helpers import AuthedUser, data

URL = "/api/v1/accounts"


def test_create_bank_account_balance_equals_opening(user: AuthedUser) -> None:
    acct = create_account(user, "HDFC Savings", "bank", "50000.00", "2026-01-01")
    assert acct["current_balance"] == "50000.00"
    assert acct["opening_balance"] == "50000.00" and acct["currency"] == "INR"
    assert acct["balance_label"] == "Balance" and acct["is_liability"] is False
    listed = data(user.get(URL))
    assert [a["name"] for a in listed] == ["HDFC Savings"]
    assert listed[0]["current_balance"] == "50000.00"


def test_credit_card_labelled_outstanding(user: AuthedUser) -> None:
    card = create_account(user, "HDFC Regalia", "credit_card", last4="4321")
    assert card["balance_label"] == "Outstanding" and card["is_liability"] is True
    assert card["last4"] == "4321"


def test_full_account_number_rejected(user: AuthedUser) -> None:
    for bad in ["12345", "123456789012", "12a4", "123"]:
        resp = user.post(URL, json={"name": f"Acct {bad}", "type": "bank", "last4": bad})
        assert resp.status_code == 422, bad
        assert resp.json()["error"]["details"][0]["field"] == "last4"


def test_unsupported_currency_and_bad_type(user: AuthedUser) -> None:
    assert (
        user.post(URL, json={"name": "X", "type": "bank", "currency": "USD"}).json()["error"][
            "code"
        ]
        == "unsupported_currency"
    )
    assert user.post(URL, json={"name": "X", "type": "brokerage"}).status_code == 422
    assert (
        user.post(URL, json={"name": "X", "type": "bank", "opening_balance": "1.005"}).status_code
        == 422
    )


def test_duplicate_name_case_insensitive(user: AuthedUser) -> None:
    create_account(user, "Cash Wallet", "cash")
    resp = user.post(URL, json={"name": "cash wallet", "type": "cash"})
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "account_name_taken"


def test_update_account(user: AuthedUser) -> None:
    acct = create_account(user, "Old", "bank", "100.00")
    out = data(user.patch(f"{URL}/{acct['id']}", json={"name": "New", "opening_balance": "250.50"}))
    assert out["name"] == "New" and out["current_balance"] == "250.50"


def test_delete_account_without_transactions(user: AuthedUser) -> None:
    acct = create_account(user)
    assert user.delete(f"{URL}/{acct['id']}").status_code == 204
    assert user.get(f"{URL}/{acct['id']}").status_code == 404


def test_delete_account_with_history_conflicts_and_offers_archive(
    user: AuthedUser, db: Session
) -> None:
    acct = create_account(user)
    insert_txn(
        db,
        user.id,
        type=TransactionType.expense,
        account_id=acct["id"],
        amount="10.00",
        category_id=category_id(db, user.id, "Food"),
    )
    resp = user.delete(f"{URL}/{acct['id']}")
    assert resp.status_code == 409
    err = resp.json()["error"]
    assert err["code"] == "account_has_transactions"
    assert err["details"][0]["suggested_action"] == "archive"


def test_account_used_as_transfer_destination_cannot_be_deleted(
    user: AuthedUser, db: Session
) -> None:
    bank = create_account(user, "Bank")
    wallet = create_account(user, "Wallet", "wallet")
    insert_txn(
        db,
        user.id,
        type=TransactionType.transfer,
        account_id=bank["id"],
        counter_account_id=wallet["id"],
        amount="5.00",
    )
    assert user.delete(f"{URL}/{wallet['id']}").status_code == 409


def test_archive_hides_from_list_but_keeps_record(user: AuthedUser) -> None:
    acct = create_account(user)
    out = data(user.post(f"{URL}/{acct['id']}/archive"))
    assert out["archived_at"] is not None
    assert data(user.get(URL)) == []
    assert [a["id"] for a in data(user.get(URL, params={"include_archived": True}))] == [acct["id"]]
    assert user.get(f"{URL}/{acct['id']}").status_code == 200


def test_unarchive_restores_account_to_lists_and_summary(user: AuthedUser) -> None:
    acct = create_account(user, opening_balance="1500.00")
    user.post(f"{URL}/{acct['id']}/archive")
    assert data(user.get(f"{URL}/summary"))["liquid_funds"] == "0.00"
    out = data(user.post(f"{URL}/{acct['id']}/unarchive"))
    assert out["archived_at"] is None
    assert [a["id"] for a in data(user.get(URL))] == [acct["id"]]
    assert data(user.get(f"{URL}/summary"))["liquid_funds"] == "1500.00"
    # Unarchiving an active account is a no-op, not an error.
    assert data(user.post(f"{URL}/{acct['id']}/unarchive"))["archived_at"] is None


def test_list_pagination_and_sort(user: AuthedUser) -> None:
    for n in ["B", "A", "C"]:
        create_account(user, n)
    resp = user.get(URL, params={"page_size": 2, "sort": "-name"})
    body = resp.json()
    assert [a["name"] for a in body["data"]] == ["C", "B"]
    assert body["meta"] == {"page": 1, "page_size": 2, "total_items": 3, "total_pages": 2}
    assert user.get(URL, params={"sort": "balance"}).json()["error"]["code"] == "invalid_sort"


def test_account_audit_entries(user: AuthedUser, db: Session) -> None:
    acct = create_account(user)
    user.patch(f"{URL}/{acct['id']}", json={"name": "Renamed"})
    user.post(f"{URL}/{acct['id']}/archive")
    user.post(f"{URL}/{acct['id']}/unarchive")
    user.post(f"{URL}/{acct['id']}/unarchive")  # no-op: no second entry
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.entity_id == acct["id"])
        .order_by(AuditLog.occurred_at, AuditLog.action)
    ).all()
    actions = sorted((r.action, tuple(r.changed_fields)) for r in rows)
    assert actions == [
        ("archive", ("archived_at",)),
        ("create", ()),
        ("unarchive", ("archived_at",)),
        ("update", ("name",)),
    ]
    assert all(r.actor_user_id == user.id for r in rows)
