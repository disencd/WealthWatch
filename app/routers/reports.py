from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, extract, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import BudgetExpense, Category, CategoryType

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


@router.get("/spending-trends")
async def spending_trends(
    months: int = Query(12, ge=1, le=60),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    yr = extract("year", BudgetExpense.date).label("year")
    mo = extract("month", BudgetExpense.date).label("month")
    rows = (await db.execute(
        select(yr, mo, func.coalesce(func.sum(BudgetExpense.amount), 0).label("total_spent"))
        .where(
            BudgetExpense.family_id == current_user.family_id,
            BudgetExpense.date >= func.now() - text(f"INTERVAL '{months} months'"),
        )
        .group_by(yr, mo)
        .order_by(yr, mo)
    )).all()
    return [{"year": int(r[0]), "month": int(r[1]), "total_spent": float(r[2])} for r in rows]


@router.get("/spending-by-merchant")
async def spending_by_merchant(
    year: Optional[int] = None, month: Optional[int] = None,
    limit: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (
        select(
            BudgetExpense.merchant,
            func.coalesce(func.sum(BudgetExpense.amount), 0).label("total_spent"),
            func.count().label("count"),
        )
        .where(BudgetExpense.family_id == current_user.family_id, BudgetExpense.merchant != "")
        .group_by(BudgetExpense.merchant)
        .order_by(func.sum(BudgetExpense.amount).desc())
    )
    if year:
        q = q.where(extract("year", BudgetExpense.date) == year)
    if month:
        q = q.where(extract("month", BudgetExpense.date) == month)
    if limit:
        q = q.limit(limit)
    rows = (await db.execute(q)).all()
    return [{"merchant": r[0], "total_spent": float(r[1]), "count": r[2]} for r in rows]


@router.get("/cashflow-sankey")
async def cashflow_sankey(
    year: int = Query(...), month: int = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fid = current_user.family_id

    income_rows = (await db.execute(
        select(Category.name, func.coalesce(func.sum(BudgetExpense.amount), 0))
        .join(Category, Category.id == BudgetExpense.category_id)
        .where(BudgetExpense.family_id == fid, Category.type == CategoryType.savings,
               extract("year", BudgetExpense.date) == year, extract("month", BudgetExpense.date) == month)
        .group_by(Category.name).order_by(func.sum(BudgetExpense.amount).desc())
    )).all()

    expense_rows = (await db.execute(
        select(Category.name, func.coalesce(func.sum(BudgetExpense.amount), 0))
        .join(Category, Category.id == BudgetExpense.category_id)
        .where(BudgetExpense.family_id == fid, Category.type == CategoryType.expense,
               extract("year", BudgetExpense.date) == year, extract("month", BudgetExpense.date) == month)
        .group_by(Category.name).order_by(func.sum(BudgetExpense.amount).desc())
    )).all()

    nodes = [{"id": "income", "name": "Income"}]
    links = []
    for name, amt in income_rows:
        nid = f"inc_{name}"
        nodes.append({"id": nid, "name": name})
        links.append({"source": nid, "target": "income", "value": float(amt)})

    total_expenses = sum(float(amt) for _, amt in expense_rows)
    nodes.append({"id": "expenses", "name": "Expenses"})
    links.append({"source": "income", "target": "expenses", "value": total_expenses})

    for name, amt in expense_rows:
        nid = f"exp_{name}"
        nodes.append({"id": nid, "name": name})
        links.append({"source": "expenses", "target": nid, "value": float(amt)})

    return {"nodes": nodes, "links": links}


@router.get("/savings-rate")
async def savings_rate(
    year: int = Query(...), month: int = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fid = current_user.family_id

    total_income = (await db.execute(
        select(func.coalesce(func.sum(BudgetExpense.amount), 0))
        .join(Category, Category.id == BudgetExpense.category_id)
        .where(BudgetExpense.family_id == fid, Category.type == CategoryType.savings,
               extract("year", BudgetExpense.date) == year, extract("month", BudgetExpense.date) == month)
    )).scalar() or 0

    total_expenses = (await db.execute(
        select(func.coalesce(func.sum(BudgetExpense.amount), 0))
        .join(Category, Category.id == BudgetExpense.category_id)
        .where(BudgetExpense.family_id == fid, Category.type == CategoryType.expense,
               extract("year", BudgetExpense.date) == year, extract("month", BudgetExpense.date) == month)
    )).scalar() or 0

    savings = float(total_income) - float(total_expenses)
    rate = (savings / float(total_income) * 100) if float(total_income) > 0 else 0

    return {
        "year": year, "month": month,
        "total_income": float(total_income), "total_expenses": float(total_expenses),
        "savings": savings, "savings_rate": rate,
    }
