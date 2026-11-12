"""Net worth service: aggregation, snapshots, stale tracking, and metrics."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import func, or_, select, update
from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.core.money import ZERO, round_money
from app.models.account import Account
from app.models.asset import Asset, AssetValuation, Liability, LiabilityBalance
from app.models.category import Category
from app.models.enums import (
    AccountType,
    AssetType,
    LoanStatus,
    TransactionStatus,
    TransactionType,
)
from app.models.loan import Loan, LoanPayment
from app.models.net_worth import NetWorthSnapshot
from app.models.transaction import Transaction
from app.models.user import User
from app.repositories.balances import account_balances
from app.repositories.base import OwnedRepository
from app.schemas.net_worth import (
    BreakdownItemOut,
    EmergencyFundMetricsOut,
    GrowthOut,
    NetWorthOut,
    NetWorthSnapshotOut,
)
from app.services import audit
from app.services.calculations.net_worth import (
    NetWorthResult,
    compute_growth,
    compute_net_worth_figures,
    default_investment_value_provider,
)
from app.services.calculations.periods import month_end
from app.services.calculations.planning import emergency_fund_coverage
from app.services.loans import get_loans_summary


class NetWorthSnapshotRepository(OwnedRepository[NetWorthSnapshot]):
    model = NetWorthSnapshot
    entity_name = "NetWorthSnapshot"


def _map_asset_type_category(atype: AssetType | str) -> str:
    val = atype.value if isinstance(atype, AssetType) else str(atype)
    if val in ("ppf", "epf", "nps", "retirement_scheme"):
        return "retirement_schemes"
    if val == "fixed_deposit":
        return "fixed_deposits"
    if val == "mutual_fund":
        return "mutual_funds"
    if val in ("gold", "real_estate"):
        return val
    return "other"


def mark_snapshots_stale(db: Session, user_id: uuid.UUID, since_date: date) -> int:
    """Mark all snapshots on or after since_date as stale."""
    stmt = (
        update(NetWorthSnapshot)
        .where(
            NetWorthSnapshot.user_id == user_id,
            NetWorthSnapshot.as_of >= since_date,
            NetWorthSnapshot.is_stale.is_(False),
        )
        .values(is_stale=True)
    )
    res = db.execute(stmt)
    count = getattr(res, "rowcount", 0)
    return int(count) if count is not None else 0


def compute_net_worth_for_date(
    db: Session,
    user_id: uuid.UUID,
    as_of: date,
) -> NetWorthResult:
    """Aggregate accounts, assets, liabilities, and loans to compute NetWorthResult."""
    # 1. Accounts
    accounts = (
        db.scalars(
            select(Account).where(
                Account.user_id == user_id,
                Account.archived_at.is_(None),
            )
        )
        .all()
    )
    bals = account_balances(db, user_id, as_of=as_of)
    bank_and_cash: list[tuple[str, Decimal]] = []
    credit_cards: list[tuple[str, Decimal]] = []

    for acct in accounts:
        bal = bals.get(acct.id, acct.opening_balance)
        if acct.type == AccountType.credit_card:
            credit_cards.append((acct.name, bal))
        elif acct.type in (AccountType.bank, AccountType.cash, AccountType.wallet):
            bank_and_cash.append((acct.name, bal))

    # 2. Assets (unclosed or closed after as_of)
    asset_stmt = select(Asset).where(
        Asset.user_id == user_id,
        or_(Asset.closed_at.is_(None), Asset.closed_at > as_of),
    )
    assets = db.scalars(asset_stmt).all()
    asset_valuations: list[tuple[str, str, Decimal, bool]] = []
    for asset in assets:
        val_stmt = (
            select(AssetValuation)
            .where(
                AssetValuation.asset_id == asset.id,
                AssetValuation.as_of <= as_of,
            )
            .order_by(AssetValuation.as_of.desc(), AssetValuation.created_at.desc())
            .limit(1)
        )
        val = db.scalars(val_stmt).first()
        if val is not None:
            cat = _map_asset_type_category(asset.type)
            asset_valuations.append((asset.name, cat, val.value, asset.is_liquid))

    # 3. Liabilities (unclosed or closed after as_of)
    liab_stmt = select(Liability).where(
        Liability.user_id == user_id,
        or_(Liability.closed_at.is_(None), Liability.closed_at > as_of),
    )
    liabilities = db.scalars(liab_stmt).all()
    other_liabilities: list[tuple[str, Decimal]] = []
    for liab in liabilities:
        bal_stmt = (
            select(LiabilityBalance)
            .where(
                LiabilityBalance.liability_id == liab.id,
                LiabilityBalance.as_of <= as_of,
            )
            .order_by(LiabilityBalance.as_of.desc(), LiabilityBalance.created_at.desc())
            .limit(1)
        )
        lbal = db.scalars(bal_stmt).first()
        if lbal is not None:
            other_liabilities.append((liab.name, lbal.balance))

    # 4. Loans
    loan_stmt = select(Loan).where(Loan.user_id == user_id)
    loans = db.scalars(loan_stmt).all()
    loan_outstandings: list[tuple[str, Decimal]] = []

    if loans:
        paid_stmt = (
            select(
                LoanPayment.loan_id,
                func.coalesce(func.sum(LoanPayment.principal), ZERO),
            )
            .join(Transaction, Transaction.id == LoanPayment.transaction_id)
            .where(
                LoanPayment.loan_id.in_([loan_elem.id for loan_elem in loans]),
                Transaction.txn_date <= as_of,
            )
            .group_by(LoanPayment.loan_id)
        )
        paid_by_loan: dict[uuid.UUID, Decimal] = dict(db.execute(paid_stmt).all())
    else:
        paid_by_loan = {}

    for loan in loans:
        if loan.start_date > as_of:
            continue
        if loan.status == LoanStatus.closed and loan.updated_at.date() <= as_of:
            continue

        starting_principal = (
            loan.baseline_outstanding
            if loan.baseline_outstanding is not None
            else loan.original_principal
        )
        paid_principal = paid_by_loan.get(loan.id, ZERO)
        outstanding = round_money(max(ZERO, starting_principal - paid_principal))
        if outstanding > ZERO:
            loan_outstandings.append((loan.lender, outstanding))

    return compute_net_worth_figures(
        as_of=as_of,
        bank_and_cash_balances=bank_and_cash,
        asset_valuations=asset_valuations,
        loan_outstandings=loan_outstandings,
        other_liabilities=other_liabilities,
        credit_card_outstandings=credit_cards,
        investment_provider=default_investment_value_provider,
        user_id=user_id,
    )


def get_net_worth(
    db: Session,
    user_id: uuid.UUID,
    as_of: date | None = None,
) -> NetWorthOut:
    target_date = as_of or date.today()
    result = compute_net_worth_for_date(db, user_id, target_date)

    # Check stale status from snapshot if exists
    snap = db.scalars(
        select(NetWorthSnapshot).where(
            NetWorthSnapshot.user_id == user_id,
            NetWorthSnapshot.as_of == target_date,
        )
    ).first()
    is_stale = snap.is_stale if snap is not None else False

    # Compute MoM growth
    if target_date.month == 1:
        prev_y = target_date.year - 1
        prev_m = 12
    else:
        prev_y = target_date.year
        prev_m = target_date.month - 1

    prev_snap = db.scalars(
        select(NetWorthSnapshot)
        .where(
            NetWorthSnapshot.user_id == user_id,
            func.extract("year", NetWorthSnapshot.as_of) == prev_y,
            func.extract("month", NetWorthSnapshot.as_of) == prev_m,
        )
        .order_by(NetWorthSnapshot.as_of.desc())
        .limit(1)
    ).first()

    mom_growth: GrowthOut | None = None
    if prev_snap is not None:
        amt, pct = compute_growth(result.net_worth, prev_snap.net_worth)
        mom_growth = GrowthOut(amount_change=amt, percentage_change=pct)

    # Compute YoY growth
    yoy_y = target_date.year - 1
    yoy_m = target_date.month
    yoy_snap = db.scalars(
        select(NetWorthSnapshot)
        .where(
            NetWorthSnapshot.user_id == user_id,
            func.extract("year", NetWorthSnapshot.as_of) == yoy_y,
            func.extract("month", NetWorthSnapshot.as_of) == yoy_m,
        )
        .order_by(NetWorthSnapshot.as_of.desc())
        .limit(1)
    ).first()

    yoy_growth: GrowthOut | None = None
    if yoy_snap is not None:
        amt, pct = compute_growth(result.net_worth, yoy_snap.net_worth)
        yoy_growth = GrowthOut(amount_change=amt, percentage_change=pct)

    return NetWorthOut(
        as_of=result.as_of,
        total_assets=result.total_assets,
        total_liabilities=result.total_liabilities,
        net_worth=result.net_worth,
        liquid_assets=result.liquid_assets,
        asset_breakdown=[
            BreakdownItemOut(
                category=item.category,
                amount=item.amount,
                share_pct=item.share_pct,
            )
            for item in result.asset_breakdown
        ],
        liability_breakdown=[
            BreakdownItemOut(
                category=item.category,
                amount=item.amount,
                share_pct=item.share_pct,
            )
            for item in result.liability_breakdown
        ],
        mom_growth=mom_growth,
        yoy_growth=yoy_growth,
        is_stale=is_stale,
    )


def _serialize_breakdown(result: NetWorthResult) -> dict[str, Any]:
    return {
        "assets": [
            {
                "category": item.category,
                "amount": str(item.amount),
                "share_pct": str(item.share_pct),
            }
            for item in result.asset_breakdown
        ],
        "liabilities": [
            {
                "category": item.category,
                "amount": str(item.amount),
                "share_pct": str(item.share_pct),
            }
            for item in result.liability_breakdown
        ],
        "liquid_assets": str(result.liquid_assets),
    }


def list_snapshots(db: Session, user_id: uuid.UUID) -> list[NetWorthSnapshotOut]:
    snaps = (
        db.scalars(
            select(NetWorthSnapshot)
            .where(NetWorthSnapshot.user_id == user_id)
            .order_by(NetWorthSnapshot.as_of.desc())
        )
        .all()
    )
    return [NetWorthSnapshotOut.model_validate(s) for s in snaps]


def create_snapshot(
    db: Session,
    user_id: uuid.UUID,
    as_of: date | None = None,
) -> NetWorthSnapshotOut:
    target_date = as_of or date.today()
    result = compute_net_worth_for_date(db, user_id, target_date)
    breakdown_data = _serialize_breakdown(result)

    snap = db.scalars(
        select(NetWorthSnapshot).where(
            NetWorthSnapshot.user_id == user_id,
            NetWorthSnapshot.as_of == target_date,
        )
    ).first()

    now = datetime.now(UTC)
    if snap is None:
        snap = NetWorthSnapshot(
            user_id=user_id,
            as_of=target_date,
            total_assets=result.total_assets,
            total_liabilities=result.total_liabilities,
            net_worth=result.net_worth,
            breakdown=breakdown_data,
            computed_at=now,
            is_stale=False,
        )
        db.add(snap)
        db.flush()
        audit.record(
            db,
            actor_user_id=user_id,
            action="create",
            entity_type="net_worth_snapshot",
            entity_id=snap.id,
        )
    else:
        snap.total_assets = result.total_assets
        snap.total_liabilities = result.total_liabilities
        snap.net_worth = result.net_worth
        snap.breakdown = breakdown_data
        snap.computed_at = now
        snap.is_stale = False
        db.flush()
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="net_worth_snapshot",
            entity_id=snap.id,
            changed_fields=[
                "total_assets",
                "total_liabilities",
                "net_worth",
                "breakdown",
                "is_stale",
            ],
        )

    db.commit()
    db.refresh(snap)
    return NetWorthSnapshotOut.model_validate(snap)


def recompute_snapshot(
    db: Session,
    user_id: uuid.UUID,
    as_of: date,
) -> NetWorthSnapshotOut:
    snap = db.scalars(
        select(NetWorthSnapshot).where(
            NetWorthSnapshot.user_id == user_id,
            NetWorthSnapshot.as_of == as_of,
        )
    ).first()
    if snap is None:
        raise NotFoundError("Snapshot")

    result = compute_net_worth_for_date(db, user_id, as_of)
    snap.total_assets = result.total_assets
    snap.total_liabilities = result.total_liabilities
    snap.net_worth = result.net_worth
    snap.breakdown = _serialize_breakdown(result)
    snap.computed_at = datetime.now(UTC)
    snap.is_stale = False

    audit.record(
        db,
        actor_user_id=user_id,
        action="update",
        entity_type="net_worth_snapshot",
        entity_id=snap.id,
        changed_fields=[
            "total_assets",
            "total_liabilities",
            "net_worth",
            "breakdown",
            "is_stale",
        ],
    )
    db.commit()
    db.refresh(snap)
    return NetWorthSnapshotOut.model_validate(snap)


def get_emergency_fund_metrics(
    db: Session,
    user_id: uuid.UUID,
    as_of: date | None = None,
) -> EmergencyFundMetricsOut:
    target_date = as_of or date.today()
    res = compute_net_worth_for_date(db, user_id, target_date)
    liquid_savings = res.liquid_assets

    # Last 3 complete months before target_date
    # E.g. target_date = 2026-11-12 -> Oct, Sep, Aug
    months: list[tuple[int, int]] = []
    cur_y, cur_m = target_date.year, target_date.month
    for _ in range(3):
        if cur_m == 1:
            cur_y -= 1
            cur_m = 12
        else:
            cur_m -= 1
        months.append((cur_y, cur_m))

    # Query essential expenses across those complete months
    earliest_start = date(months[-1][0], months[-1][1], 1)
    latest_end = month_end(months[0][0], months[0][1])

    stmt = (
        select(
            Transaction.type,
            func.coalesce(func.sum(Transaction.amount), ZERO),
        )
        .join(Category, Category.id == Transaction.category_id)
        .where(
            Transaction.user_id == user_id,
            Transaction.status == TransactionStatus.posted,
            Transaction.txn_date >= earliest_start,
            Transaction.txn_date <= latest_end,
            Category.is_essential.is_(True),
            Category.name != "Loan Interest",
        )
        .group_by(Transaction.type)
    )
    by_type = dict(db.execute(stmt).all())
    exp = by_type.get(TransactionType.expense, ZERO)
    ref = by_type.get(TransactionType.refund, ZERO)
    net_essential = exp - ref

    # Average per complete month (divided by 3)
    avg_monthly_essential = round_money(max(net_essential / Decimal(3), ZERO))

    # Add monthly EMI commitment
    loan_summary = get_loans_summary(db, user_id)
    essential_monthly = round_money(
        avg_monthly_essential + loan_summary.total_monthly_emi_commitment
    )

    coverage = emergency_fund_coverage(liquid_savings, essential_monthly)
    return EmergencyFundMetricsOut(
        liquid_savings=liquid_savings,
        essential_monthly_expenses=essential_monthly,
        coverage_months=coverage,
    )


def run_month_end_snapshots(db: Session, target_date: date | None = None) -> int:
    """Take month-end snapshots for all users who don't have one for recent month-ends.

    Idempotent: skips if snapshot already exists for that user and date.
    """
    ref_date = target_date or date.today()
    # Most recent complete month end
    if ref_date.month == 1:
        last_m_end = month_end(ref_date.year - 1, 12)
    else:
        last_m_end = month_end(ref_date.year, ref_date.month - 1)

    # Check all active users
    users = db.scalars(select(User).where(User.is_active.is_(True))).all()
    created_count = 0

    for user in users:
        # Check existing snapshot
        existing = db.scalars(
            select(NetWorthSnapshot.id).where(
                NetWorthSnapshot.user_id == user.id,
                NetWorthSnapshot.as_of == last_m_end,
            )
        ).first()
        if existing is not None:
            continue

        result = compute_net_worth_for_date(db, user.id, last_m_end)
        snap = NetWorthSnapshot(
            user_id=user.id,
            as_of=last_m_end,
            total_assets=result.total_assets,
            total_liabilities=result.total_liabilities,
            net_worth=result.net_worth,
            breakdown=_serialize_breakdown(result),
            computed_at=datetime.now(UTC),
            is_stale=False,
        )
        db.add(snap)
        created_count += 1

    db.commit()
    return created_count
