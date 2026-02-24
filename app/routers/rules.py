from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import AutoCategoryRule

router = APIRouter(prefix="/api/v1/rules", tags=["rules"])


class CreateRuleRequest(BaseModel):
    merchant_pattern: str
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    category_id: int
    sub_category_id: Optional[int] = None
    priority: int = 0


class UpdateRuleRequest(BaseModel):
    merchant_pattern: Optional[str] = None
    min_amount: Optional[float] = None
    max_amount: Optional[float] = None
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    is_active: Optional[bool] = None
    priority: Optional[int] = None


def _rule_dict(r: AutoCategoryRule) -> dict:
    return {
        "id": r.id, "family_id": r.family_id, "merchant_pattern": r.merchant_pattern,
        "min_amount": r.min_amount, "max_amount": r.max_amount,
        "category_id": r.category_id, "sub_category_id": r.sub_category_id,
        "is_active": r.is_active, "priority": r.priority,
        "created_at": str(r.created_at), "updated_at": str(r.updated_at),
    }


@router.get("")
async def list_rules(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(AutoCategoryRule).where(AutoCategoryRule.family_id == current_user.family_id)
        .order_by(AutoCategoryRule.priority.desc())
    )).scalars().all()
    return [_rule_dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_rule(
    req: CreateRuleRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rule = AutoCategoryRule(
        family_id=current_user.family_id, created_by_user_id=current_user.user_id,
        merchant_pattern=req.merchant_pattern, min_amount=req.min_amount,
        max_amount=req.max_amount, category_id=req.category_id,
        sub_category_id=req.sub_category_id, is_active=True, priority=req.priority,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return _rule_dict(rule)


@router.put("/{id}")
async def update_rule(
    id: int, req: UpdateRuleRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(AutoCategoryRule).where(AutoCategoryRule.id == id, AutoCategoryRule.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Rule not found")
    if req.merchant_pattern is not None: r.merchant_pattern = req.merchant_pattern
    if req.min_amount is not None: r.min_amount = req.min_amount
    if req.max_amount is not None: r.max_amount = req.max_amount
    if req.category_id is not None: r.category_id = req.category_id
    if req.sub_category_id is not None: r.sub_category_id = req.sub_category_id
    if req.is_active is not None: r.is_active = req.is_active
    if req.priority is not None: r.priority = req.priority
    await db.commit()
    await db.refresh(r)
    return _rule_dict(r)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_rule(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(AutoCategoryRule).where(AutoCategoryRule.id == id, AutoCategoryRule.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Rule not found")
    await db.delete(r)
    await db.commit()
