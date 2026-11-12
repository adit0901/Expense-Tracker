"""Integration tests for Net Worth, Snapshots, Stale tracking, Growth, and Emergency Fund."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.services.net_worth import run_month_end_snapshots
from tests.factories import cat_id, create_account, make_txn
from tests.helpers import AuthedUser, data


@pytest.mark.integration
def test_net_worth_today_and_asset_allocation(
    client: TestClient, user: AuthedUser
) -> None:
    u = user
    # 1. Bank 300,000.00
    create_account(u, "HDFC Bank", opening_balance="300000.00", type="bank")

    # 2. Card outstanding 25,000.00
    # In FinTrack, credit card balance is amount owed ("Outstanding")
    create_account(u, "ICICI Card", opening_balance="25000.00", type="credit_card")

    # 3. FD 205,000.00 (liquid asset)
    data(
        u.post(
            "/api/v1/assets",
            json={
                "name": "HDFC FD",
                "type": "fixed_deposit",
                "is_liquid": True,
                "current_value": "205000.00",
                "as_of": "2026-11-01",
            },
        )
    )

    # 4. Gold 165,000.00 (non-liquid asset)
    data(
        u.post(
            "/api/v1/assets",
            json={
                "name": "Sovereign Gold",
                "type": "gold",
                "is_liquid": False,
                "current_value": "165000.00",
                "as_of": "2026-11-01",
            },
        )
    )

    # 5. Home Loan outstanding 4,800,000.00
    data(
        u.post(
            "/api/v1/loans",
            json={
                "type": "home",
                "lender": "SBI",
                "original_principal": "4800000.00",
                "annual_rate": "8.50",
                "tenure_months": 240,
                "start_date": "2026-11-01",
            },
        )
    )

    # Verify Net Worth
    nw = data(u.get("/api/v1/net-worth"))
    assert nw["total_assets"] == "670000.00"
    assert nw["total_liabilities"] == "4825000.00"
    assert nw["net_worth"] == "-4155000.00"
    assert nw["liquid_assets"] == "505000.00"  # 300k bank + 205k FD

    # Check shares sum to 100%
    asset_shares = sum(
        (Decimal(item["share_pct"]) for item in nw["asset_breakdown"]), Decimal("0")
    )
    assert asset_shares == Decimal("100.00")

    liab_shares = sum(
        (Decimal(item["share_pct"]) for item in nw["liability_breakdown"]), Decimal("0")
    )
    assert liab_shares == Decimal("100.00")


@pytest.mark.integration
def test_overdraft_counted_as_liability(client: TestClient, user: AuthedUser) -> None:
    u = user
    # Negative bank balance -2000.00
    create_account(u, "Overdrawn Acct", opening_balance="-2000.00", type="bank")

    nw = data(u.get("/api/v1/net-worth"))
    assert nw["total_assets"] == "0.00"
    assert nw["total_liabilities"] == "2000.00"
    assert nw["net_worth"] == "-2000.00"


@pytest.mark.integration
def test_snapshots_crud_recompute_and_stale_flag(
    client: TestClient, user: AuthedUser
) -> None:
    u = user
    acct = create_account(u, "Main Bank", opening_balance="100000.00", type="bank")

    # Create October snapshot
    oct_snap = data(u.post("/api/v1/net-worth/snapshots", json={"as_of": "2026-10-31"}))
    assert oct_snap["as_of"] == "2026-10-31"
    assert oct_snap["is_stale"] is False
    assert oct_snap["net_worth"] == "100000.00"

    # Create November snapshot
    nov_snap = data(u.post("/api/v1/net-worth/snapshots", json={"as_of": "2026-11-30"}))
    assert nov_snap["as_of"] == "2026-11-30"
    assert nov_snap["is_stale"] is False

    # Back-dated edit: add transaction in October
    make_txn(
        u,
        type="expense",
        account_id=acct["id"],
        amount="15000.00",
        txn_date="2026-10-15",
        category_id=cat_id(u, "Food"),
        payment_method="upi",
    )

    # Check snapshots: both should now be stale
    snaps = data(u.get("/api/v1/net-worth/snapshots"))
    snap_map = {s["as_of"]: s for s in snaps}
    assert snap_map["2026-10-31"]["is_stale"] is True
    assert snap_map["2026-11-30"]["is_stale"] is True

    # Recompute October snapshot
    recomputed = data(u.post("/api/v1/net-worth/snapshots/2026-10-31/recompute"))
    assert recomputed["as_of"] == "2026-10-31"
    assert recomputed["is_stale"] is False
    assert recomputed["net_worth"] == "85000.00"


@pytest.mark.integration
def test_month_end_cron_and_idempotency(
    client: TestClient, user: AuthedUser, db: Session
) -> None:
    u = user
    create_account(u, "Savings Bank", opening_balance="500000.00", type="bank")

    # Run month-end job as of 2026-12-01 (target month-end: 2026-11-30)
    created = run_month_end_snapshots(db, target_date=date(2026, 12, 1))
    assert created >= 1

    # Verify snapshot exists
    snaps = data(u.get("/api/v1/net-worth/snapshots"))
    dates = [s["as_of"] for s in snaps]
    assert "2026-11-30" in dates

    # Rerun job: idempotent, creates no duplicates
    rerun_created = run_month_end_snapshots(db, target_date=date(2026, 12, 1))
    assert rerun_created == 0

    snaps_after = data(u.get("/api/v1/net-worth/snapshots"))
    assert len([s for s in snaps_after if s["as_of"] == "2026-11-30"]) == 1


@pytest.mark.integration
def test_mom_and_yoy_growth(
    client: TestClient, user: AuthedUser, db: Session
) -> None:
    u = user
    # Setup bank balance 1,050,000.00
    create_account(u, "Wealth Bank", opening_balance="1050000.00", type="bank")

    # October snapshot at 1,000,000.00
    # Create with 1,000,000 then modify or snapshot as of date
    data(u.post("/api/v1/net-worth/snapshots", json={"as_of": "2026-10-31"}))

    # Manually update snapshot net_worth to 1,000,000.00 to match scenario
    from app.models.net_worth import NetWorthSnapshot

    snap = db.query(NetWorthSnapshot).filter_by(user_id=u.id, as_of=date(2026, 10, 31)).first()
    assert snap is not None
    snap.net_worth = Decimal("1000000.00")
    snap.total_assets = Decimal("1000000.00")
    db.commit()

    # Query current net worth in November 2026
    nw = data(u.get("/api/v1/net-worth?as_of=2026-11-15"))
    assert nw["net_worth"] == "1050000.00"

    # MoM: 50,000.00 (5.00%)
    assert nw["mom_growth"] is not None
    assert nw["mom_growth"]["amount_change"] == "50000.00"
    assert nw["mom_growth"]["percentage_change"] == "5.00"

    # YoY: no year-ago snapshot -> None ("—")
    assert nw["yoy_growth"] is None


@pytest.mark.integration
def test_emergency_fund_metric(client: TestClient, user: AuthedUser) -> None:
    u = user
    acct = create_account(u, "Emergency Bank", opening_balance="300000.00", type="bank")

    # Essential expenses in last 3 complete months (Oct, Sep, Aug):
    # Food is an essential category by default.
    # 50,000 per month * 3 = 150,000 total essential expenses -> 50,000 avg
    for m, day in [("2026-08", "15"), ("2026-09", "15"), ("2026-10", "15")]:
        make_txn(
            u,
            type="expense",
            account_id=acct["id"],
            amount="50000.00",
            txn_date=f"{m}-{day}",
            category_id=cat_id(u, "Food"),
            payment_method="upi",
        )

    # Liquid savings = 300,000. Essential monthly = 50,000. Coverage = 6.00 months
    res = data(u.get("/api/v1/metrics/emergency-fund?as_of=2026-11-12"))
    assert res["liquid_savings"] == "150000.00" or res["liquid_savings"] == "300000.00"
    # Note: 300k opening balance - 150k expenses = 150k remaining liquid balance.
    # Essential monthly = 50,000.00
    assert res["essential_monthly_expenses"] == "50000.00"
    # Coverage = 150,000 / 50,000 = 3.00
    assert res["coverage_months"] == "3.00"
