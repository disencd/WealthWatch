import os
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import Receipt

router = APIRouter(prefix="/api/v1/receipts", tags=["receipts"])

RECEIPTS_DIR = os.environ.get("RECEIPTS_DIR", "./receipts")


def _receipt_dict(r: Receipt) -> dict:
    return {
        "id": r.id, "family_id": r.family_id, "created_by_user_id": r.created_by_user_id,
        "budget_expense_id": r.budget_expense_id, "file_name": r.file_name,
        "file_path": r.file_path, "file_size": r.file_size, "mime_type": r.mime_type,
        "merchant": r.merchant, "amount": r.amount,
        "date": str(r.date) if r.date else None, "notes": r.notes,
        "created_at": str(r.created_at), "updated_at": str(r.updated_at),
    }


@router.get("")
async def list_receipts(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Receipt).where(Receipt.family_id == current_user.family_id)
        .order_by(Receipt.created_at.desc())
    )).scalars().all()
    return [_receipt_dict(r) for r in rows]


@router.post("", status_code=status.HTTP_201_CREATED)
async def upload_receipt(
    file: UploadFile = File(...),
    merchant: str = Form(""),
    amount: Optional[float] = Form(None),
    notes: str = Form(""),
    budget_expense_id: Optional[int] = Form(None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    os.makedirs(RECEIPTS_DIR, exist_ok=True)
    ext = os.path.splitext(file.filename or "")[1]
    unique_name = f"{uuid.uuid4().hex}{ext}"
    path = os.path.join(RECEIPTS_DIR, unique_name)
    content = await file.read()
    with open(path, "wb") as f:
        f.write(content)

    receipt = Receipt(
        family_id=current_user.family_id, created_by_user_id=current_user.user_id,
        budget_expense_id=budget_expense_id, file_name=file.filename or unique_name,
        file_path=path, file_size=len(content), mime_type=file.content_type or "",
        merchant=merchant, amount=amount, notes=notes,
    )
    db.add(receipt)
    await db.commit()
    await db.refresh(receipt)
    return _receipt_dict(receipt)


@router.get("/{id}")
async def get_receipt(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(Receipt).where(Receipt.id == id, Receipt.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Receipt not found")
    return _receipt_dict(r)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_receipt(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    r = (await db.execute(
        select(Receipt).where(Receipt.id == id, Receipt.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not r:
        raise HTTPException(404, "Receipt not found")
    if os.path.exists(r.file_path):
        os.remove(r.file_path)
    await db.delete(r)
    await db.commit()
