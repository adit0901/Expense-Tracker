import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.audit import AuditLog
from app.models.enums import TransactionType
from app.models.transaction import Transaction
from tests.factories import category_id, create_account, insert_txn
from tests.helpers import AuthedUser, data

URL = "/api/v1/categories"
EXPECTED_EXPENSE = {
    "Food",
    "Rent",
    "Shopping",
    "Travel",
    "Healthcare",
    "Utilities",
    "Fuel",
    "Entertainment",
    "Insurance",
    "Education",
    "Loan Interest",
    "Others",
}
EXPECTED_INCOME = {
    "Salary",
    "Bonus",
    "Freelance",
    "Business",
    "Rental",
    "Dividends",
    "Interest",
    "Other Income",
}
ESSENTIAL = {"Rent", "Utilities", "Healthcare", "Insurance", "Education", "Food", "Loan Interest"}


def _list(u: AuthedUser, **params: object) -> list[dict[str, object]]:
    result: list[dict[str, object]] = data(u.get(URL, params={"page_size": 100, **params}))
    return result


def _by_name(u: AuthedUser, name: str, kind: str = "expense") -> dict[str, object]:
    return next(c for c in _list(u, kind=kind) if c["name"] == name)


def test_new_user_default_categories(user: AuthedUser) -> None:
    expense = _list(user, kind="expense")
    income = _list(user, kind="income")
    assert {c["name"] for c in expense} == EXPECTED_EXPENSE
    assert {c["name"] for c in income} == EXPECTED_INCOME
    assert {c["name"] for c in expense if c["is_essential"]} == ESSENTIAL
    assert [c["name"] for c in expense if c["is_system"]] == ["Loan Interest"]
    assert "EMIs" not in {c["name"] for c in expense}


def test_create_subcategory_and_third_level_rejected(user: AuthedUser) -> None:
    food = _by_name(user, "Food")
    groceries = data(
        user.post(URL, json={"kind": "expense", "name": "Groceries", "parent_id": food["id"]})
    )
    assert groceries["parent_id"] == food["id"]
    resp = user.post(
        URL, json={"kind": "expense", "name": "Vegetables", "parent_id": groceries["id"]}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "category_depth_exceeded"


def test_subcategory_kind_must_match_parent(user: AuthedUser) -> None:
    salary = _by_name(user, "Salary", "income")
    resp = user.post(URL, json={"kind": "expense", "name": "X", "parent_id": salary["id"]})
    assert resp.status_code == 422


def test_names_unique_case_insensitive_within_parent(user: AuthedUser) -> None:
    dup_top = user.post(URL, json={"kind": "expense", "name": "food"})
    assert dup_top.status_code == 409
    assert dup_top.json()["error"]["code"] == "category_name_taken"
    # Same name as an income category is fine (different kind).
    assert user.post(URL, json={"kind": "income", "name": "Food"}).status_code == 201
    food, shopping = _by_name(user, "Food"), _by_name(user, "Shopping")
    assert (
        user.post(
            URL, json={"kind": "expense", "name": "Online", "parent_id": food["id"]}
        ).status_code
        == 201
    )
    assert (
        user.post(
            URL, json={"kind": "expense", "name": "ONLINE", "parent_id": food["id"]}
        ).status_code
        == 409
    )
    assert (
        user.post(
            URL, json={"kind": "expense", "name": "Online", "parent_id": shopping["id"]}
        ).status_code
        == 201
    )


def test_rename_recolor_and_toggle_essential(user: AuthedUser) -> None:
    fuel = _by_name(user, "Fuel")
    out = data(
        user.patch(
            f"{URL}/{fuel['id']}", json={"is_essential": True, "color": "#123456", "name": "Petrol"}
        )
    )
    assert out["is_essential"] is True and out["color"] == "#123456" and out["name"] == "Petrol"
    salary = _by_name(user, "Salary", "income")
    assert user.patch(f"{URL}/{salary['id']}", json={"is_essential": True}).status_code == 422


def test_system_category_protected(user: AuthedUser) -> None:
    li = _by_name(user, "Loan Interest")
    resp = user.delete(f"{URL}/{li['id']}")
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "system_category"
    assert user.patch(f"{URL}/{li['id']}", json={"name": "EMI"}).status_code == 409
    assert data(user.patch(f"{URL}/{li['id']}", json={"color": "#000000"}))["color"] == "#000000"


def test_delete_unused_category(user: AuthedUser) -> None:
    ent = _by_name(user, "Entertainment")
    out = data(user.delete(f"{URL}/{ent['id']}"))
    assert out["reassigned_transactions"] == 0
    assert "Entertainment" not in {c["name"] for c in _list(user, kind="expense")}


def test_delete_in_use_without_replacement(user: AuthedUser, db: Session) -> None:
    acct = create_account(user)
    insert_txn(
        db,
        user.id,
        type=TransactionType.expense,
        account_id=acct["id"],
        amount="100.00",
        category_id=category_id(db, user.id, "Entertainment"),
    )
    ent = _by_name(user, "Entertainment")
    resp = user.delete(f"{URL}/{ent['id']}")
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "category_in_use"


def test_delete_with_reassignment_including_subcategories(user: AuthedUser, db: Session) -> None:
    acct = create_account(user)
    ent = _by_name(user, "Entertainment")
    movies = data(
        user.post(URL, json={"kind": "expense", "name": "Movies", "parent_id": ent["id"]})
    )
    t1 = insert_txn(
        db,
        user.id,
        type=TransactionType.expense,
        account_id=acct["id"],
        amount="100.00",
        category_id=ent["id"],
    )  # type: ignore[arg-type]
    t2 = insert_txn(
        db,
        user.id,
        type=TransactionType.expense,
        account_id=acct["id"],
        amount="50.00",
        category_id=movies["id"],
    )  # type: ignore[arg-type]
    others = _by_name(user, "Others")
    salary = _by_name(user, "Salary", "income")
    wrong_kind = user.delete(f"{URL}/{ent['id']}", params={"replacement_id": salary["id"]})
    assert wrong_kind.status_code == 422
    self_repl = user.delete(f"{URL}/{ent['id']}", params={"replacement_id": movies["id"]})
    assert self_repl.status_code == 422
    out = data(user.delete(f"{URL}/{ent['id']}", params={"replacement_id": others["id"]}))
    assert out["reassigned_transactions"] == 2
    db.expire_all()
    cats = set(
        db.scalars(select(Transaction.category_id).where(Transaction.id.in_([t1.id, t2.id])))
    )
    assert {str(c) for c in cats} == {others["id"]}
    names = {c["name"] for c in _list(user, kind="expense")}
    assert "Entertainment" not in names and "Movies" not in names
    audits = db.scalars(select(AuditLog.action).where(AuditLog.entity_id == t1.id)).all()
    assert audits == ["update"]


def test_db_trigger_blocks_third_level(user: AuthedUser, db: Session) -> None:
    food = _by_name(user, "Food")
    sub = data(user.post(URL, json={"kind": "expense", "name": "Snacks", "parent_id": food["id"]}))
    with pytest.raises(IntegrityError), db.begin_nested():
        db.execute(
            text(
                "INSERT INTO categories (id, user_id, kind, name, parent_id, is_essential, "
                "is_system) VALUES (gen_random_uuid(), :u, 'expense', 'Deep', :p, false, false)"
            ),
            {"u": user.id, "p": sub["id"]},
        )


def test_filters(user: AuthedUser) -> None:
    food = _by_name(user, "Food")
    data(user.post(URL, json={"kind": "expense", "name": "Groceries", "parent_id": food["id"]}))
    subs = _list(user, parent_id=food["id"])
    assert [c["name"] for c in subs] == ["Groceries"]
    tops = _list(user, kind="expense", top_level_only=True)
    assert "Groceries" not in {c["name"] for c in tops}


def test_cannot_reference_another_users_category(user: AuthedUser, other_user: AuthedUser) -> None:
    theirs = _by_name(user, "Food")
    resp = other_user.post(
        URL, json={"kind": "expense", "name": "Sneaky", "parent_id": theirs["id"]}
    )
    assert resp.status_code == 422
    assert resp.json()["error"]["code"] == "category_not_found"
    mine = _by_name(other_user, "Shopping")
    resp = other_user.delete(f"{URL}/{mine['id']}", params={"replacement_id": theirs["id"]})
    assert resp.status_code == 200  # unused category: replacement ignored, nothing leaks
    assert theirs["id"] not in resp.text


def test_category_audit_entries(user: AuthedUser, db: Session) -> None:
    cat = data(user.post(URL, json={"kind": "expense", "name": "Pets"}))
    user.patch(f"{URL}/{cat['id']}", json={"color": "#AABBCC"})
    user.delete(f"{URL}/{cat['id']}")
    rows = db.scalars(select(AuditLog).where(AuditLog.entity_id == cat["id"])).all()
    assert sorted((r.action, tuple(r.changed_fields)) for r in rows) == [
        ("create", ()),
        ("delete", ()),
        ("update", ("color",)),
    ]
    assert all(r.actor_user_id == user.id and r.entity_type == "category" for r in rows)
