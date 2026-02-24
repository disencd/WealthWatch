from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, or_
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import Settlement, User

router = APIRouter(prefix="/api/v1/settlements", tags=["settlements"])


class CreateSettlementRequest(BaseModel):
    to_user_id: int
    amount: float
    currency: str = "USD"
    payment_method: str = ""
    notes: str = ""


class UpdateStatusRequest(BaseModel):
    status: str


def _settle_dict(s: Settlement) -> dict:
    return {
        "id": s.id, "from_user_id": s.from_user_id, "to_user_id": s.to_user_id,
        "amount": s.amount, "currency": s.currency, "status": s.status,
        "payment_method": s.payment_method, "notes": s.notes,
        "created_at": str(s.created_at), "updated_at": str(s.updated_at),
    }


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_settlement(
    req: CreateSettlementRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = Settlement(
        from_user_id=current_user.user_id, to_user_id=req.to_user_id,
        amount=req.amount, currency=req.currency,
        payment_method=req.payment_method, notes=req.notes, status="pending",
    )
    db.add(s)
    await db.commit()
    await db.refresh(s)
    return _settle_dict(s)


@router.get("")
async def get_settlements(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Settlement).where(
            or_(Settlement.from_user_id == current_user.user_id,
                Settlement.to_user_id == current_user.user_id)
        ).order_by(Settlement.created_at.desc())
    )).scalars().all()
    return [_settle_dict(s) for s in rows]


@router.get("/{id}")
async def get_settlement(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = (await db.execute(select(Settlement).where(Settlement.id == id))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Settlement not found")
    return _settle_dict(s)


@router.put("/{id}/status")
async def update_settlement_status(
    id: int, req: UpdateStatusRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    s = (await db.execute(select(Settlement).where(Settlement.id == id))).scalar_one_or_none()
    if not s:
        raise HTTPException(404, "Settlement not found")
    if req.status not in ("pending", "completed", "cancelled"):
        raise HTTPException(400, "Invalid status")
    s.status = req.status
    await db.commit()
    await db.refresh(s)
    return _settle_dict(s)
