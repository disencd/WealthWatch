from datetime import datetime
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import Expense, Split, User

router = APIRouter(prefix="/api/v1/expenses", tags=["expenses"])


class SplitItem(BaseModel):
    user_id: int
    amount: float
    percentage: float = 0


class CreateExpenseRequest(BaseModel):
    title: str
    description: str = ""
    amount: float
    currency: str = "USD"
    date: str
    group_id: Optional[int] = None
    category: str = ""
    splits: List[SplitItem] = []


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_expense(
    req: CreateExpenseRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    expense = Expense(
        title=req.title, description=req.description, amount=req.amount,
        currency=req.currency, date=datetime.fromisoformat(req.date),
        payer_id=current_user.user_id, group_id=req.group_id, category=req.category,
    )
    db.add(expense)
    await db.flush()

    for s in req.splits:
        db.add(Split(expense_id=expense.id, user_id=s.user_id, amount=s.amount, percentage=s.percentage))

    await db.commit()
    await db.refresh(expense)
    return {"id": expense.id, "title": expense.title, "amount": expense.amount, "date": str(expense.date)}


@router.get("")
async def get_expenses(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Expense).options(selectinload(Expense.splits))
        .where(Expense.payer_id == current_user.user_id)
        .order_by(Expense.date.desc())
    )).scalars().all()
    return [
        {"id": e.id, "title": e.title, "amount": e.amount, "currency": e.currency,
         "date": str(e.date), "payer_id": e.payer_id, "group_id": e.group_id,
         "category": e.category, "splits": [
             {"id": s.id, "user_id": s.user_id, "amount": s.amount} for s in e.splits
         ]}
        for e in rows
    ]


@router.get("/{id}")
async def get_expense(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    e = (await db.execute(
        select(Expense).options(selectinload(Expense.splits)).where(Expense.id == id)
    )).scalar_one_or_none()
    if not e:
        raise HTTPException(404, "Expense not found")
    return {"id": e.id, "title": e.title, "amount": e.amount, "currency": e.currency,
            "date": str(e.date), "payer_id": e.payer_id, "group_id": e.group_id,
            "category": e.category, "splits": [
                {"id": s.id, "user_id": s.user_id, "amount": s.amount} for s in e.splits
            ]}
