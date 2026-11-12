"""Assets and liabilities management: CRUD, valuations, closing, historical lookup."""

from __future__ import annotations

import uuid
from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.core.money import ZERO, round_money
from app.models.asset import Asset, AssetValuation, Liability, LiabilityBalance
from app.models.enums import AssetType
from app.repositories.base import OwnedRepository
from app.schemas.asset import (
    AssetCloseIn,
    AssetCreate,
    AssetOut,
    AssetUpdate,
    AssetValuationIn,
    AssetValuationOut,
    LiabilityBalanceIn,
    LiabilityBalanceOut,
    LiabilityCloseIn,
    LiabilityCreate,
    LiabilityOut,
    LiabilityUpdate,
)
from app.services import audit


class AssetRepository(OwnedRepository[Asset]):
    model = Asset
    entity_name = "Asset"


class LiabilityRepository(OwnedRepository[Liability]):
    model = Liability
    entity_name = "Liability"


def _to_asset_out(asset: Asset, as_of: date) -> AssetOut:
    if asset.closed_at is not None and as_of >= asset.closed_at:
        current_value = round_money(ZERO)
        latest_date = None
    else:
        valid_vals = [v for v in asset.valuations if v.as_of <= as_of]
        if valid_vals:
            latest = max(valid_vals, key=lambda v: v.as_of)
            current_value = round_money(latest.value)
            latest_date = latest.as_of
        else:
            current_value = round_money(ZERO)
            latest_date = None

    return AssetOut(
        id=asset.id,
        type=asset.type,
        name=asset.name,
        is_liquid=asset.is_liquid,
        details=asset.details,
        current_value=current_value,
        latest_valuation_date=latest_date,
        closed_at=asset.closed_at,
        created_at=asset.created_at,
        updated_at=asset.updated_at,
    )


def _to_liability_out(liability: Liability, as_of: date) -> LiabilityOut:
    if liability.closed_at is not None and as_of >= liability.closed_at:
        current_balance = round_money(ZERO)
        latest_date = None
    else:
        valid_bals = [b for b in liability.balances if b.as_of <= as_of]
        if valid_bals:
            latest = max(valid_bals, key=lambda b: b.as_of)
            current_balance = round_money(latest.balance)
            latest_date = latest.as_of
        else:
            current_balance = round_money(ZERO)
            latest_date = None

    return LiabilityOut(
        id=liability.id,
        name=liability.name,
        current_balance=current_balance,
        latest_balance_date=latest_date,
        notes=liability.notes,
        closed_at=liability.closed_at,
        created_at=liability.created_at,
        updated_at=liability.updated_at,
    )


# --- Assets ---


def create_asset(db: Session, user_id: uuid.UUID, payload: AssetCreate) -> AssetOut:
    asset_type = AssetType(payload.type)
    as_of = payload.as_of or date.today()

    asset = Asset(
        user_id=user_id,
        type=asset_type,
        name=payload.name,
        details=payload.details,
        is_liquid=payload.is_liquid,
    )
    db.add(asset)
    db.flush()

    valuation = AssetValuation(
        asset_id=asset.id,
        as_of=as_of,
        value=payload.current_value,
    )
    db.add(valuation)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="asset",
        entity_id=asset.id,
        changed_fields=["type", "name", "current_value", "is_liquid"],
    )
    db.commit()

    asset.valuations = [valuation]
    return _to_asset_out(asset, as_of=as_of)


def get_asset(
    db: Session, user_id: uuid.UUID, asset_id: uuid.UUID, as_of: date | None = None
) -> AssetOut:
    query_date = as_of or date.today()
    stmt = (
        select(Asset)
        .where(Asset.id == asset_id, Asset.user_id == user_id)
        .options(selectinload(Asset.valuations))
    )
    asset = db.scalar(stmt)
    if not asset:
        from app.core.errors import NotFoundError

        raise NotFoundError("Asset")
    return _to_asset_out(asset, as_of=query_date)


def list_assets(
    db: Session,
    user_id: uuid.UUID,
    as_of: date | None = None,
    include_closed: bool = False,
) -> list[AssetOut]:
    query_date = as_of or date.today()
    stmt = (
        select(Asset)
        .where(Asset.user_id == user_id)
        .options(selectinload(Asset.valuations))
        .order_by(Asset.created_at.desc())
    )
    assets = db.scalars(stmt).all()
    if not include_closed:
        assets = [
            a for a in assets if a.closed_at is None or a.closed_at > query_date
        ]
    return [_to_asset_out(a, as_of=query_date) for a in assets]


def update_asset(
    db: Session, user_id: uuid.UUID, asset_id: uuid.UUID, payload: AssetUpdate
) -> AssetOut:
    asset = AssetRepository(db, user_id).get_or_404(asset_id)
    changed: list[str] = []

    if payload.name is not None:
        asset.name = payload.name
        changed.append("name")
    if payload.is_liquid is not None:
        asset.is_liquid = payload.is_liquid
        changed.append("is_liquid")
    if payload.details is not None:
        asset.details = payload.details
        changed.append("details")

    db.flush()
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="asset",
            entity_id=asset.id,
            changed_fields=changed,
        )
        db.commit()

    return get_asset(db, user_id, asset_id)


def close_asset(
    db: Session, user_id: uuid.UUID, asset_id: uuid.UUID, payload: AssetCloseIn
) -> AssetOut:
    asset = AssetRepository(db, user_id).get_or_404(asset_id)
    asset.closed_at = payload.closed_at
    db.flush()
    audit.record(
        db,
        actor_user_id=user_id,
        action="update",
        entity_type="asset",
        entity_id=asset.id,
        changed_fields=["closed_at"],
    )
    db.commit()
    return get_asset(db, user_id, asset_id, as_of=payload.closed_at)


def add_valuation(
    db: Session, user_id: uuid.UUID, asset_id: uuid.UUID, payload: AssetValuationIn
) -> AssetValuationOut:
    asset = AssetRepository(db, user_id).get_or_404(asset_id)
    existing = db.scalar(
        select(AssetValuation).where(
            AssetValuation.asset_id == asset.id, AssetValuation.as_of == payload.as_of
        )
    )
    if existing:
        existing.value = payload.value
        val = existing
    else:
        val = AssetValuation(
            asset_id=asset.id,
            as_of=payload.as_of,
            value=payload.value,
        )
        db.add(val)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="update" if existing else "create",
        entity_type="asset_valuation",
        entity_id=val.id,
        changed_fields=["value", "as_of"],
    )
    from app.services.net_worth import mark_snapshots_stale

    mark_snapshots_stale(db, user_id, payload.as_of)
    db.commit()
    return AssetValuationOut(
        id=val.id,
        asset_id=val.asset_id,
        as_of=val.as_of,
        value=round_money(val.value),
        created_at=val.created_at,
    )


def list_valuations(
    db: Session, user_id: uuid.UUID, asset_id: uuid.UUID
) -> list[AssetValuationOut]:
    asset = AssetRepository(db, user_id).get_or_404(asset_id)
    vals = db.scalars(
        select(AssetValuation)
        .where(AssetValuation.asset_id == asset.id)
        .order_by(AssetValuation.as_of.desc(), AssetValuation.created_at.desc())
    ).all()
    return [
        AssetValuationOut(
            id=v.id,
            asset_id=v.asset_id,
            as_of=v.as_of,
            value=round_money(v.value),
            created_at=v.created_at,
        )
        for v in vals
    ]


# --- Liabilities ---


def create_liability(
    db: Session, user_id: uuid.UUID, payload: LiabilityCreate
) -> LiabilityOut:
    as_of = payload.as_of or date.today()
    liability = Liability(
        user_id=user_id,
        name=payload.name,
        notes=payload.notes,
    )
    db.add(liability)
    db.flush()

    balance = LiabilityBalance(
        liability_id=liability.id,
        as_of=as_of,
        balance=payload.current_balance,
    )
    db.add(balance)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="create",
        entity_type="liability",
        entity_id=liability.id,
        changed_fields=["name", "current_balance"],
    )
    db.commit()

    liability.balances = [balance]
    return _to_liability_out(liability, as_of=as_of)


def get_liability(
    db: Session, user_id: uuid.UUID, liability_id: uuid.UUID, as_of: date | None = None
) -> LiabilityOut:
    query_date = as_of or date.today()
    stmt = (
        select(Liability)
        .where(Liability.id == liability_id, Liability.user_id == user_id)
        .options(selectinload(Liability.balances))
    )
    liability = db.scalar(stmt)
    if not liability:
        from app.core.errors import NotFoundError

        raise NotFoundError("Liability")
    return _to_liability_out(liability, as_of=query_date)


def list_liabilities(
    db: Session,
    user_id: uuid.UUID,
    as_of: date | None = None,
    include_closed: bool = False,
) -> list[LiabilityOut]:
    query_date = as_of or date.today()
    stmt = (
        select(Liability)
        .where(Liability.user_id == user_id)
        .options(selectinload(Liability.balances))
        .order_by(Liability.created_at.desc())
    )
    liabilities = db.scalars(stmt).all()
    if not include_closed:
        liabilities = [
            item for item in liabilities if item.closed_at is None or item.closed_at > query_date
        ]
    return [_to_liability_out(item, as_of=query_date) for item in liabilities]


def update_liability(
    db: Session, user_id: uuid.UUID, liability_id: uuid.UUID, payload: LiabilityUpdate
) -> LiabilityOut:
    liability = LiabilityRepository(db, user_id).get_or_404(liability_id)
    changed: list[str] = []

    if payload.name is not None:
        liability.name = payload.name
        changed.append("name")
    if payload.notes is not None:
        liability.notes = payload.notes
        changed.append("notes")

    db.flush()
    if changed:
        audit.record(
            db,
            actor_user_id=user_id,
            action="update",
            entity_type="liability",
            entity_id=liability.id,
            changed_fields=changed,
        )
        db.commit()

    return get_liability(db, user_id, liability_id)


def close_liability(
    db: Session, user_id: uuid.UUID, liability_id: uuid.UUID, payload: LiabilityCloseIn
) -> LiabilityOut:
    liability = LiabilityRepository(db, user_id).get_or_404(liability_id)
    liability.closed_at = payload.closed_at
    db.flush()
    audit.record(
        db,
        actor_user_id=user_id,
        action="update",
        entity_type="liability",
        entity_id=liability.id,
        changed_fields=["closed_at"],
    )
    db.commit()
    return get_liability(db, user_id, liability_id, as_of=payload.closed_at)


def add_balance(
    db: Session,
    user_id: uuid.UUID,
    liability_id: uuid.UUID,
    payload: LiabilityBalanceIn,
) -> LiabilityBalanceOut:
    liability = LiabilityRepository(db, user_id).get_or_404(liability_id)
    existing = db.scalar(
        select(LiabilityBalance).where(
            LiabilityBalance.liability_id == liability.id,
            LiabilityBalance.as_of == payload.as_of,
        )
    )
    if existing:
        existing.balance = payload.balance
        bal = existing
    else:
        bal = LiabilityBalance(
            liability_id=liability.id,
            as_of=payload.as_of,
            balance=payload.balance,
        )
        db.add(bal)
    db.flush()

    audit.record(
        db,
        actor_user_id=user_id,
        action="update" if existing else "create",
        entity_type="liability_balance",
        entity_id=bal.id,
        changed_fields=["balance", "as_of"],
    )
    from app.services.net_worth import mark_snapshots_stale

    mark_snapshots_stale(db, user_id, payload.as_of)
    db.commit()
    return LiabilityBalanceOut(
        id=bal.id,
        liability_id=bal.liability_id,
        as_of=bal.as_of,
        balance=round_money(bal.balance),
        created_at=bal.created_at,
    )


def list_balances(
    db: Session, user_id: uuid.UUID, liability_id: uuid.UUID
) -> list[LiabilityBalanceOut]:
    liability = LiabilityRepository(db, user_id).get_or_404(liability_id)
    bals = db.scalars(
        select(LiabilityBalance)
        .where(LiabilityBalance.liability_id == liability.id)
        .order_by(LiabilityBalance.as_of.desc(), LiabilityBalance.created_at.desc())
    ).all()
    return [
        LiabilityBalanceOut(
            id=b.id,
            liability_id=b.liability_id,
            as_of=b.as_of,
            balance=round_money(b.balance),
            created_at=b.created_at,
        )
        for b in bals
    ]
