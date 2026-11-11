from sqlalchemy import select
from sqlalchemy.orm import Session

from app.integrations.storage import get_storage
from app.models.transaction import Attachment
from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data

JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00" + b"\x00" * 64
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
PDF = b"%PDF-1.7\n" + b"0" * 64
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00\x00\x00\xff\xff" + b"\x00" * 64


def _txn(u: AuthedUser) -> dict[str, object]:
    acct = create_account(u, "Bank")
    return make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        amount="10.00",
        category_id=cat_id(u, "Food"),
        payment_method="upi",
    )


def _upload(u: AuthedUser, txn_id: object, name: str, content: bytes) -> object:
    return u.post(
        f"/api/v1/transactions/{txn_id}/attachments", files={"file": (name, content, "image/png")}
    )


def test_attach_view_download_delete(user: AuthedUser, db: Session) -> None:
    t = _txn(user)
    big_jpeg = JPEG + b"\x00" * (2 * 1024 * 1024)
    resp = _upload(user, t["id"], "../../etc/receipt.jpg", big_jpeg)
    assert resp.status_code == 201, resp.text  # type: ignore[attr-defined]
    att = resp.json()["data"]  # type: ignore[attr-defined]
    assert att["mime_type"] == "image/jpeg" and att["original_name"] == "receipt.jpg"
    assert att["size_bytes"] == len(big_jpeg)
    shown = data(user.get(f"/api/v1/transactions/{t['id']}"))["attachments"]
    assert [a["id"] for a in shown] == [att["id"]]
    dl = user.get(f"/api/v1/attachments/{att['id']}")
    assert dl.status_code == 200 and dl.content == big_jpeg
    assert dl.headers["content-type"] == "image/jpeg"
    assert dl.headers["content-disposition"].startswith("attachment;")
    row = db.scalars(select(Attachment).where(Attachment.id == att["id"])).one()
    assert row.storage_key != "receipt.jpg" and get_storage().exists(row.storage_key)
    assert user.delete(f"/api/v1/attachments/{att['id']}").status_code == 204
    assert not get_storage().exists(row.storage_key)
    assert user.get(f"/api/v1/attachments/{att['id']}").status_code == 404


def test_pdf_png_accepted(user: AuthedUser) -> None:
    t = _txn(user)
    assert _upload(user, t["id"], "a.pdf", PDF).status_code == 201  # type: ignore[attr-defined]
    assert _upload(user, t["id"], "b.png", PNG).status_code == 201  # type: ignore[attr-defined]


def test_disguised_executable_rejected(user: AuthedUser) -> None:
    t = _txn(user)
    resp = _upload(user, t["id"], "receipt.png", EXE)
    assert resp.status_code == 422  # type: ignore[attr-defined]
    assert resp.json()["error"]["code"] == "unsupported_file_type"  # type: ignore[attr-defined]
    text = _upload(user, t["id"], "receipt.png", b"just some text")
    assert text.status_code == 422  # type: ignore[attr-defined]


def test_oversized_file_413(user: AuthedUser) -> None:
    t = _txn(user)
    resp = _upload(user, t["id"], "big.jpg", JPEG + b"\x00" * (11 * 1024 * 1024))
    assert resp.status_code == 413  # type: ignore[attr-defined]


def test_max_five_attachments(user: AuthedUser) -> None:
    t = _txn(user)
    for i in range(5):
        assert _upload(user, t["id"], f"{i}.png", PNG).status_code == 201  # type: ignore[attr-defined]
    sixth = _upload(user, t["id"], "6.png", PNG)
    assert sixth.status_code == 409  # type: ignore[attr-defined]
    assert sixth.json()["error"]["code"] == "attachment_limit"  # type: ignore[attr-defined]


def test_deleting_transaction_deletes_receipts(user: AuthedUser, db: Session) -> None:
    t = _txn(user)
    att = _upload(user, t["id"], "r.png", PNG).json()["data"]  # type: ignore[attr-defined]
    key = db.scalar(select(Attachment.storage_key).where(Attachment.id == att["id"]))
    assert key and get_storage().exists(key)
    assert user.delete(f"/api/v1/transactions/{t['id']}").status_code == 204
    assert not get_storage().exists(key)
    assert db.scalar(select(Attachment).where(Attachment.id == att["id"])) is None


def test_account_deletion_removes_all_data_and_files(user: AuthedUser, db: Session) -> None:
    """Completes task 3.7: data and uploaded files are gone after account deletion."""
    from app.models import Account, Category, Transaction

    t = _txn(user)
    att = _upload(user, t["id"], "r.png", PNG).json()["data"]  # type: ignore[attr-defined]
    key = db.scalar(select(Attachment.storage_key).where(Attachment.id == att["id"]))
    assert user.delete("/api/v1/users/me", json={"password": user.password}).status_code == 204
    assert key and not get_storage().exists(key)
    for model in (Account, Category, Transaction, Attachment):
        assert db.scalars(select(model).where(model.user_id == user.id)).all() == []
