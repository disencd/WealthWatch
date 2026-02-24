from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import Account, AccountType, AccountOwnership, NetWorthSnapshot

router = APIRouter(prefix="/api/v1", tags=["accounts"])


class CreateAccountRequest(BaseModel):
    institution_name: str
    account_name: str
    account_type: str
    ownership: str = "ours"
    balance: float = 0
    currency: str = "USD"
    is_asset: Optional[bool] = None


class UpdateAccountRequest(BaseModel):
    account_name: Optional[str] = None
    balance: Optional[float] = None
    ownership: Optional[str] = None
    is_active: Optional[bool] = None


def _acc_dict(a: Account) -> dict:
    return {
        "id": a.id, "family_id": a.family_id, "created_by_user_id": a.created_by_user_id,
        "institution_name": a.institution_name, "account_name": a.account_name,
        "account_type": a.account_type.value, "ownership": a.ownership.value,
        "balance": a.balance, "currency": a.currency,
        "is_asset": a.is_asset, "is_active": a.is_active,
        "last_synced_at": str(a.last_synced_at) if a.last_synced_at else None,
        "created_at": str(a.created_at), "updated_at": str(a.updated_at),
    }


# ── Accounts ───────────────────────────────────────────────────────

@router.get("/accounts")
async def list_accounts(
    type: Optional[str] = None, ownership: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Account).where(Account.family_id == current_user.family_id, Account.is_active == True).order_by(Account.account_type, Account.account_name)
    if type:
        q = q.where(Account.account_type == type)
    if ownership:
        q = q.where(Account.ownership == ownership)
    rows = (await db.execute(q)).scalars().all()
    return [_acc_dict(a) for a in rows]


@router.post("/accounts", status_code=status.HTTP_201_CREATED)
async def create_account(
    req: CreateAccountRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    is_asset = req.is_asset if req.is_asset is not None else True
    if req.account_type in ("credit_card", "loan", "mortgage"):
        is_asset = False
    account = Account(
        family_id=current_user.family_id, created_by_user_id=current_user.user_id,
        institution_name=req.institution_name, account_name=req.account_name,
        account_type=AccountType(req.account_type),
        ownership=AccountOwnership(req.ownership),
        balance=req.balance, currency=req.currency,
        is_asset=is_asset, is_active=True,
    )
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return _acc_dict(account)


@router.get("/accounts/{id}")
async def get_account(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acc = (await db.execute(
        select(Account).where(Account.id == id, Account.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not acc:
        raise HTTPException(404, "Account not found")
    return _acc_dict(acc)


@router.put("/accounts/{id}")
async def update_account(
    id: int, req: UpdateAccountRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acc = (await db.execute(
        select(Account).where(Account.id == id, Account.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not acc:
        raise HTTPException(404, "Account not found")
    if req.account_name is not None:
        acc.account_name = req.account_name
    if req.balance is not None:
        acc.balance = req.balance
    if req.ownership is not None:
        acc.ownership = AccountOwnership(req.ownership)
    if req.is_active is not None:
        acc.is_active = req.is_active
    await db.commit()
    await db.refresh(acc)
    return _acc_dict(acc)


@router.delete("/accounts/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    acc = (await db.execute(
        select(Account).where(Account.id == id, Account.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not acc:
        raise HTTPException(404, "Account not found")
    await db.delete(acc)
    await db.commit()


# ── Net Worth ──────────────────────────────────────────────────────

@router.get("/networth/summary")
async def get_networth_summary(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts = (await db.execute(
        select(Account).where(Account.family_id == current_user.family_id, Account.is_active == True)
    )).scalars().all()

    total_assets = total_liabilities = 0.0
    assets_by_type: dict[str, float] = {}
    liabilities_by_type: dict[str, float] = {}
    for a in accounts:
        if a.is_asset:
            total_assets += a.balance
            assets_by_type[a.account_type.value] = assets_by_type.get(a.account_type.value, 0) + a.balance
        else:
            total_liabilities += a.balance
            liabilities_by_type[a.account_type.value] = liabilities_by_type.get(a.account_type.value, 0) + a.balance

    return {
        "total_assets": total_assets, "total_liabilities": total_liabilities,
        "net_worth": total_assets - total_liabilities,
        "assets_by_type": assets_by_type, "liabilities_by_type": liabilities_by_type,
        "account_count": len(accounts),
    }


@router.get("/networth/history")
async def get_networth_history(
    limit: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(NetWorthSnapshot).where(
        NetWorthSnapshot.family_id == current_user.family_id
    ).order_by(NetWorthSnapshot.date)
    if limit:
        q = q.limit(limit)
    rows = (await db.execute(q)).scalars().all()
    return [{"id": s.id, "date": str(s.date), "total_assets": s.total_assets,
             "total_liabilities": s.total_liabilities, "net_worth": s.net_worth} for s in rows]


@router.post("/networth/snapshot", status_code=status.HTTP_201_CREATED)
async def snapshot_networth(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    accounts = (await db.execute(
        select(Account).where(Account.family_id == current_user.family_id, Account.is_active == True)
    )).scalars().all()
    total_assets = sum(a.balance for a in accounts if a.is_asset)
    total_liabilities = sum(a.balance for a in accounts if not a.is_asset)
    snapshot = NetWorthSnapshot(
        family_id=current_user.family_id, date=datetime.now(timezone.utc),
        total_assets=total_assets, total_liabilities=total_liabilities,
        net_worth=total_assets - total_liabilities,
    )
    db.add(snapshot)
    await db.commit()
    await db.refresh(snapshot)
    return {"id": snapshot.id, "date": str(snapshot.date), "total_assets": snapshot.total_assets,
            "total_liabilities": snapshot.total_liabilities, "net_worth": snapshot.net_worth}
