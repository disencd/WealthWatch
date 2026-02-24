from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import Split, Expense, User

router = APIRouter(prefix="/api/v1/balances", tags=["balances"])


@router.get("")
async def get_balances(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.user_id

    # Money owed TO the current user (they paid, others owe splits)
    owed_to_me = (await db.execute(
        select(Split.user_id, func.coalesce(func.sum(Split.amount), 0))
        .join(Expense, Expense.id == Split.expense_id)
        .where(Expense.payer_id == uid, Split.user_id != uid)
        .group_by(Split.user_id)
    )).all()

    # Money the current user OWES (others paid, user has splits)
    i_owe = (await db.execute(
        select(Expense.payer_id, func.coalesce(func.sum(Split.amount), 0))
        .join(Expense, Expense.id == Split.expense_id)
        .where(Split.user_id == uid, Expense.payer_id != uid)
        .group_by(Expense.payer_id)
    )).all()

    balances: dict[int, float] = {}
    for other_id, amt in owed_to_me:
        balances[other_id] = balances.get(other_id, 0) + float(amt)
    for other_id, amt in i_owe:
        balances[other_id] = balances.get(other_id, 0) - float(amt)

    result = []
    for other_id, net in balances.items():
        user = (await db.execute(select(User).where(User.id == other_id))).scalar_one_or_none()
        name = f"{user.first_name} {user.last_name}" if user else f"User #{other_id}"
        result.append({"user_id": other_id, "name": name, "balance": net})

    return result


@router.get("/users/{user_id}")
async def get_balance_with_user(
    user_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    uid = current_user.user_id

    owed = (await db.execute(
        select(func.coalesce(func.sum(Split.amount), 0))
        .join(Expense, Expense.id == Split.expense_id)
        .where(Expense.payer_id == uid, Split.user_id == user_id)
    )).scalar() or 0

    owes = (await db.execute(
        select(func.coalesce(func.sum(Split.amount), 0))
        .join(Expense, Expense.id == Split.expense_id)
        .where(Expense.payer_id == user_id, Split.user_id == uid)
    )).scalar() or 0

    user = (await db.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    return {
        "user_id": user_id,
        "name": f"{user.first_name} {user.last_name}",
        "they_owe_you": float(owed),
        "you_owe_them": float(owes),
        "net_balance": float(owed) - float(owes),
    }
