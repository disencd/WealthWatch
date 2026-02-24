from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import RecurringTransaction, RecurringFrequency

router = APIRouter(prefix="/api/v1/recurring", tags=["recurring"])


class CreateRecurringRequest(BaseModel):
    merchant: str
    amount: float
    currency: str = "USD"
    frequency: str
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    next_due_date: str
    notes: str = ""


class UpdateRecurringRequest(BaseModel):
    merchant: Optional[str] = None
    amount: Optional[float] = None
    frequency: Optional[str] = None
    next_due_date: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None


def _rec_dict(r: RecurringTransaction) -> dict:
    return {
        "id": r.id, "family_id": r.family_id, "merchant": r.merchant,
        "amount": r.amount, "currency": r.currency, "frequency": r.frequency.value,
        "category_id": r.category_id, "sub_category_id": r.sub_category_id,
        "next_due_date": str(r.next_due_date), "is_active": r.is_active,
        "auto_detected": r.auto_detected, "notes": r.notes,
        "created_at": str(r.created_at), "updated_at": str(r.updated_at),
    }


@router.get("")
async def list_recurring(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(RecurringTransaction).where(RecurringTransaction.family_id == current_user.family_id)
        .order_by(RecurringTransaction.next_due_date)
    )).scalars().all()
    return [_rec_dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_recurring(
    req: CreateRecurringRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = RecurringTransaction(
        family_id=current_user.family_id, created_by_user_id=current_user.user_id,
        merchant=req.merchant, amount=req.amount, currency=req.currency,
        frequency=RecurringFrequency(req.frequency),
        category_id=req.category_id, sub_category_id=req.sub_category_id,
        next_due_date=datetime.fromisoformat(req.next_due_date),
        is_active=True, notes=req.notes,
    )
    db.add(r)
    await db.commit()
    await db.refresh(r)
    return _rec_dict(r)


@router.get("/upcoming")
async def get_upcoming(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cutoff = datetime.utcnow() + timedelta(days=30)
    rows = (await db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.family_id == current_user.family_id,
            RecurringTransaction.is_active == True,
            RecurringTransaction.next_due_date <= cutoff,
        ).order_by(RecurringTransaction.next_due_date)
    )).scalars().all()
    return [_rec_dict(r) for r in rows]


@router.put("/{id}")
async def update_recurring(
    id: int, req: UpdateRecurringRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == id, RecurringTransaction.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Not found")
    if req.merchant is not None: r.merchant = req.merchant
    if req.amount is not None: r.amount = req.amount
    if req.frequency is not None: r.frequency = RecurringFrequency(req.frequency)
    if req.next_due_date is not None: r.next_due_date = datetime.fromisoformat(req.next_due_date)
    if req.is_active is not None: r.is_active = req.is_active
    if req.notes is not None: r.notes = req.notes
    await db.commit()
    await db.refresh(r)
    return _rec_dict(r)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_recurring(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(RecurringTransaction).where(
            RecurringTransaction.id == id, RecurringTransaction.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Not found")
    await db.delete(r)
    await db.commit()
