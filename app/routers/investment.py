from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import InvestmentHolding, InvestmentType

router = APIRouter(prefix="/api/v1/investments", tags=["investments"])


class CreateHoldingRequest(BaseModel):
    account_id: int
    symbol: str
    name: str
    investment_type: str
    quantity: float = 0
    cost_basis: float = 0
    current_price: float = 0


class UpdateHoldingRequest(BaseModel):
    quantity: Optional[float] = None
    current_price: Optional[float] = None
    cost_basis: Optional[float] = None


def _holding_dict(h: InvestmentHolding) -> dict:
    return {
        "id": h.id, "account_id": h.account_id, "family_id": h.family_id,
        "symbol": h.symbol, "name": h.name, "investment_type": h.investment_type.value,
        "quantity": h.quantity, "cost_basis": h.cost_basis,
        "current_price": h.current_price, "current_value": h.current_value,
        "gain_loss": h.gain_loss, "gain_loss_percent": h.gain_loss_percent,
        "last_updated_at": str(h.last_updated_at) if h.last_updated_at else None,
        "created_at": str(h.created_at), "updated_at": str(h.updated_at),
    }


@router.get("")
async def list_holdings(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(InvestmentHolding).where(InvestmentHolding.family_id == current_user.family_id)
        .order_by(InvestmentHolding.symbol)
    )).scalars().all()
    return [_holding_dict(h) for h in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_holding(
    req: CreateHoldingRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    current_value = req.quantity * req.current_price
    total_cost = req.quantity * req.cost_basis
    gain_loss = current_value - total_cost
    gain_loss_pct = (gain_loss / total_cost * 100) if total_cost else 0

    h = InvestmentHolding(
        account_id=req.account_id, family_id=current_user.family_id,
        symbol=req.symbol, name=req.name, investment_type=InvestmentType(req.investment_type),
        quantity=req.quantity, cost_basis=req.cost_basis, current_price=req.current_price,
        current_value=current_value, gain_loss=gain_loss, gain_loss_percent=gain_loss_pct,
    )
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return _holding_dict(h)


@router.get("/portfolio")
async def get_portfolio_summary(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(InvestmentHolding).where(InvestmentHolding.family_id == current_user.family_id)
    )).scalars().all()
    total_value = sum(h.current_value for h in rows)
    total_cost = sum(h.quantity * h.cost_basis for h in rows)
    by_type: dict[str, float] = {}
    for h in rows:
        by_type[h.investment_type.value] = by_type.get(h.investment_type.value, 0) + h.current_value
    return {
        "total_value": total_value, "total_cost": total_cost,
        "total_gain_loss": total_value - total_cost,
        "total_gain_loss_percent": ((total_value - total_cost) / total_cost * 100) if total_cost else 0,
        "by_type": by_type, "holding_count": len(rows),
    }


@router.put("/{id}")
async def update_holding(
    id: int, req: UpdateHoldingRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h = (await db.execute(
        select(InvestmentHolding).where(InvestmentHolding.id == id, InvestmentHolding.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not h:
        raise HTTPException(404, "Holding not found")
    if req.quantity is not None:
        h.quantity = req.quantity
    if req.current_price is not None:
        h.current_price = req.current_price
    if req.cost_basis is not None:
        h.cost_basis = req.cost_basis
    h.current_value = h.quantity * h.current_price
    total_cost = h.quantity * h.cost_basis
    h.gain_loss = h.current_value - total_cost
    h.gain_loss_percent = (h.gain_loss / total_cost * 100) if total_cost else 0
    await db.commit()
    await db.refresh(h)
    return _holding_dict(h)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_holding(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    h = (await db.execute(
        select(InvestmentHolding).where(InvestmentHolding.id == id, InvestmentHolding.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not h:
        raise HTTPException(404, "Holding not found")
    await db.delete(h)
    await db.commit()
