import json
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.models.transaction import ImportBatch, Transaction
from app.services import imports as import_service
from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data

URL = "/api/v1/imports"


def _csv(rows: list[str], header: str = "Date,Amount,Type,Description,Category,Method") -> bytes:
    return ("\n".join([header, *rows]) + "\n").encode()


def _upload(
    u: AuthedUser,
    account_id: object,
    content: bytes,
    mapping: dict[str, str] | None,
    date_format: str = "DD/MM/YYYY",
    name: str = "bank.csv",
) -> Any:
    form: dict[str, str] = {"account_id": str(account_id), "date_format": date_format}
    if mapping is not None:
        form["column_mapping"] = json.dumps(mapping)
    return u.post(URL, data=form, files={"file": (name, content, "text/csv")})


MAPPING = {
    "date": "Date",
    "amount": "Amount",
    "type": "Type",
    "description": "Description",
    "category": "Category",
    "payment_method": "Method",
}


@pytest.fixture
def bank(user: AuthedUser) -> str:
    return str(create_account(user, "HDFC Savings", "bank", "1000.00", "2026-01-01")["id"])


def test_preview_flags_invalid_date_and_unknown_category(user: AuthedUser, bank: str) -> None:
    content = _csv(
        [
            "05/10/2026,450.00,expense,Swiggy order,Food,UPI",
            "31/02/2026,10.00,expense,Bad date,Food,UPI",
            "06/10/2026,80000,income,Salary Oct,Salary,",
            "07/10/2026,99.99,expense,Mystery,Gadgets,Card",
            "08/10/2026,abc,expense,Bad amount,Food,UPI",
        ]
    )
    batch = data(_upload(user, bank, content, MAPPING))
    assert batch["status"] == "preview" and batch["row_count"] == 5
    rows = {r["row"]: r for r in batch["rows"]}
    assert rows[2]["errors"] == [] and rows[2]["selected"] is True
    assert rows[2]["category_name"] == "Food" and rows[2]["payment_method"] == "upi"
    assert rows[3]["errors"] and "invalid date" in rows[3]["errors"][0]
    assert rows[3]["selected"] is False
    assert rows[4]["type"] == "income" and rows[4]["category_name"] == "Salary"
    assert rows[5]["category_name"] == "Others" and rows[5]["warnings"]
    assert rows[6]["errors"] and rows[6]["selected"] is False
    assert batch["valid_count"] == 3 and batch["invalid_count"] == 2


def test_confirm_creates_valid_rows_atomically_tagged(
    user: AuthedUser, bank: str, db: Session
) -> None:
    content = _csv(
        [f"{d:02d}/10/2026,{d}.00,expense,Item {d},Food,UPI" for d in range(1, 21)]
        + ["99/99/2026,1.00,expense,Broken,Food,UPI"]
    )
    batch = data(_upload(user, bank, content, MAPPING))
    out = data(user.post(f"{URL}/{batch['id']}/confirm"))
    assert out["status"] == "confirmed" and out["imported_count"] == 20
    assert out["undo_available_until"] is not None
    count = db.scalar(
        select(func.count())
        .select_from(Transaction)
        .where(Transaction.import_batch_id == batch["id"])
    )
    assert count == 20
    listed = user.get("/api/v1/transactions", params={"import_batch_id": batch["id"]}).json()
    assert listed["meta"]["total_items"] == 20
    again = user.post(f"{URL}/{batch['id']}/confirm")
    assert again.status_code == 409


def test_selecting_invalid_row_rejected(user: AuthedUser, bank: str) -> None:
    batch = data(_upload(user, bank, _csv(["xx,1.00,expense,a,Food,UPI"]), MAPPING))
    resp = user.post(f"{URL}/{batch['id']}/confirm", json={"selected_rows": [2]})
    assert resp.status_code == 422


def test_atomic_rollback_on_failure(
    user: AuthedUser, bank: str, db: Session, monkeypatch: pytest.MonkeyPatch
) -> None:
    content = _csv(
        [f"{(i % 28) + 1:02d}/10/2026,{i}.00,expense,Row {i},Food,UPI" for i in range(1, 101)]
    )
    batch = data(_upload(user, bank, content, MAPPING))
    real = import_service.txn_service.build_transaction
    calls = {"n": 0}

    def flaky(*args: Any, **kwargs: Any) -> Any:
        calls["n"] += 1
        if calls["n"] == 40:
            raise RuntimeError("simulated failure while saving row 40")
        return real(*args, **kwargs)

    monkeypatch.setattr(import_service.txn_service, "build_transaction", flaky)
    resp = user.post(f"{URL}/{batch['id']}/confirm")
    assert resp.status_code == 500
    assert (
        db.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.user_id == user.id)
        )
        == 0
    )
    status = db.scalar(select(ImportBatch.status).where(ImportBatch.id == batch["id"]))
    assert status.value == "preview"


def test_undo_within_24h_and_expiry(user: AuthedUser, bank: str, db: Session) -> None:
    content = _csv(["01/10/2026,10.00,expense,A,Food,UPI", "02/10/2026,20.00,expense,B,Food,UPI"])
    batch = data(_upload(user, bank, content, MAPPING))
    data(user.post(f"{URL}/{batch['id']}/confirm"))
    undone = data(user.post(f"{URL}/{batch['id']}/undo"))
    assert undone["status"] == "undone"
    assert (
        db.scalar(
            select(func.count()).select_from(Transaction).where(Transaction.user_id == user.id)
        )
        == 0
    )
    # Expired window.
    b2 = data(_upload(user, bank, _csv(["03/10/2026,30.00,expense,C,Food,UPI"]), MAPPING))
    data(user.post(f"{URL}/{b2['id']}/confirm"))
    db.execute(
        update(ImportBatch)
        .where(ImportBatch.id == b2["id"])
        .values(confirmed_at=datetime.now(UTC) - timedelta(hours=25))
    )
    db.commit()
    resp = user.post(f"{URL}/{b2['id']}/undo")
    assert resp.status_code == 409 and resp.json()["error"]["code"] == "import_undo_expired"


def test_duplicates_flagged_and_unselected(user: AuthedUser, bank: str) -> None:
    make_txn(
        user,
        type="expense",
        account_id=bank,
        amount="450.00",
        category_id=cat_id(user, "Food"),
        payment_method="upi",
        txn_date="2026-10-05",
        description="Swiggy order",
    )
    content = _csv(
        [
            "05/10/2026,450.00,expense,Swiggy order,Food,UPI",
            "06/10/2026,120.00,expense,Uber,Travel,UPI",
        ]
    )
    batch = data(_upload(user, bank, content, MAPPING))
    rows = {r["row"]: r for r in batch["rows"]}
    assert rows[2]["duplicate"] is True and rows[2]["selected"] is False
    assert rows[3]["duplicate"] is False and rows[3]["selected"] is True
    assert batch["duplicate_count"] == 1
    out = data(user.post(f"{URL}/{batch['id']}/confirm"))
    assert out["imported_count"] == 1
    # Re-importing the same file flags every row (fingerprint of the previous import).
    again = data(_upload(user, bank, content, MAPPING))
    assert all(r["duplicate"] for r in again["rows"])
    # Explicitly selecting a duplicate imports it (never silently discarded).
    forced = data(user.post(f"{URL}/{again['id']}/confirm", json={"selected_rows": [3]}))
    assert forced["imported_count"] == 1


def test_debit_credit_columns_and_encodings(user: AuthedUser, bank: str) -> None:
    header = "Txn Date;Narration;Withdrawal Amt.;Deposit Amt."
    text = "\n".join([header, "01-10-2026;Café coffee;1,250.50;", "02-10-2026;Refund salary;;5000"])
    content = text.encode("cp1252")
    batch = data(_upload(user, bank, content, None, date_format="DD-MM-YYYY"))
    assert batch["encoding"] == "windows-1252"
    assert batch["column_mapping"]["debit"] == "Withdrawal Amt."
    rows = batch["rows"]
    assert rows[0]["type"] == "expense" and rows[0]["amount"] == "1250.50"
    assert rows[0]["description"] == "Café coffee"
    assert rows[1]["type"] == "income" and rows[1]["category_name"] == "Other Income"
    bom = data(_upload(user, bank, "﻿".encode() + _csv(["01/10/2026,5,expense,x,Food,"]), MAPPING))
    assert bom["encoding"] == "utf-8" and bom["rows"][0]["errors"] == []


def test_upload_rejections(user: AuthedUser, bank: str) -> None:
    exe = b"MZ\x90\x00" + b"\x00" * 100
    r = _upload(user, bank, exe, MAPPING, name="data.csv")
    assert r.status_code == 422 and r.json()["error"]["code"] == "unsupported_file_type"
    big = _upload(user, bank, b"a" * (10 * 1024 * 1024 + 1), MAPPING)
    assert big.status_code == 413
    many = _csv([f"01/10/2026,{i}.00,expense,r{i},Food,UPI" for i in range(5001)])
    r = _upload(user, bank, many, MAPPING)
    assert r.status_code == 422 and r.json()["error"]["code"] == "too_many_rows"
    bad_map = _upload(user, bank, _csv(["01/10/2026,1,expense,a,Food,UPI"]), {"date": "Nope"})
    assert bad_map.status_code == 422 and bad_map.json()["error"]["code"] == "invalid_mapping"


def test_card_account_import_uses_credit_card_method(user: AuthedUser) -> None:
    card = create_account(user, "Card", "credit_card")
    batch = data(
        _upload(user, card["id"], _csv(["01/10/2026,500,expense,Amazon,Shopping,"]), MAPPING)
    )
    assert batch["rows"][0]["payment_method"] == "credit_card"
    out = data(user.post(f"{URL}/{batch['id']}/confirm"))
    assert out["imported_count"] == 1
