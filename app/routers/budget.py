import csv
import io
import re
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status
from pydantic import BaseModel
from sqlalchemy import select, func, extract
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import TokenData, get_current_user, require_role
from app.database import get_db
from app.models import (
    Budget, BudgetExpense, BudgetPeriod, Category, CategoryType, SubCategory,
)

router = APIRouter(prefix="/api/v1/budget", tags=["budget"])


# ── Schemas ────────────────────────────────────────────────────────

class CreateCategoryRequest(BaseModel):
    type: str
    name: str
    description: str = ""


class CreateSubCategoryRequest(BaseModel):
    category_id: int
    name: str
    description: str = ""


class CreateBudgetRequest(BaseModel):
    category_id: Optional[int] = None
    sub_category_id: Optional[int] = None
    period: str
    year: int
    month: Optional[int] = None
    amount: float


class CreateBudgetExpenseRequest(BaseModel):
    category_id: int
    sub_category_id: int
    title: str
    description: str = ""
    amount: float
    currency: str = "USD"
    date: str
    merchant: str = ""
    notes: str = ""


# ── Helpers ────────────────────────────────────────────────────────

def _cat_dict(c: Category) -> dict:
    return {"id": c.id, "family_id": c.family_id, "type": c.type.value, "name": c.name,
            "description": c.description, "is_active": c.is_active,
            "created_at": str(c.created_at), "updated_at": str(c.updated_at)}


def _sub_dict(s: SubCategory, cat: Optional[Category] = None) -> dict:
    d = {"id": s.id, "family_id": s.family_id, "category_id": s.category_id,
         "name": s.name, "description": s.description, "is_active": s.is_active,
         "created_at": str(s.created_at), "updated_at": str(s.updated_at)}
    if cat:
        d["category"] = _cat_dict(cat)
    return d


def _budget_dict(b: Budget) -> dict:
    d = {"id": b.id, "family_id": b.family_id, "created_by_user_id": b.created_by_user_id,
         "category_id": b.category_id, "sub_category_id": b.sub_category_id,
         "period": b.period.value, "year": b.year, "month": b.month,
         "amount": b.amount, "is_active": b.is_active,
         "created_at": str(b.created_at), "updated_at": str(b.updated_at)}
    if b.category_id and hasattr(b, "category") and b.category:
        d["category"] = _cat_dict(b.category)
    if b.sub_category_id and hasattr(b, "sub_category") and b.sub_category:
        d["sub_category"] = _sub_dict(b.sub_category)
    return d


def _expense_dict(e: BudgetExpense) -> dict:
    d = {"id": e.id, "family_id": e.family_id, "created_by_user_id": e.created_by_user_id,
         "category_id": e.category_id, "sub_category_id": e.sub_category_id,
         "title": e.title, "description": e.description, "amount": e.amount,
         "currency": e.currency, "date": str(e.date), "merchant": e.merchant,
         "notes": e.notes, "created_at": str(e.created_at), "updated_at": str(e.updated_at)}
    if hasattr(e, "category") and e.category:
        d["category"] = _cat_dict(e.category)
    if hasattr(e, "sub_category") and e.sub_category:
        d["sub_category"] = _sub_dict(e.sub_category)
    return d


def _parse_date(s: str) -> datetime:
    for fmt in ("%Y-%m-%d", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%SZ", "%m/%d/%Y"):
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    raise ValueError(f"Invalid date: {s}")


# ── Categories ─────────────────────────────────────────────────────

@router.get("/categories")
async def list_categories(
    type: Optional[str] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(Category).where(Category.family_id == current_user.family_id).order_by(Category.type, Category.name)
    if type:
        q = q.where(Category.type == type)
    rows = (await db.execute(q)).scalars().all()
    return [_cat_dict(c) for c in rows]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(
    req: CreateCategoryRequest,
    current_user: TokenData = Depends(require_role("superadmin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if req.type not in ("expense", "savings"):
        raise HTTPException(400, "Invalid category type")
    cat = Category(family_id=current_user.family_id, type=CategoryType(req.type),
                   name=req.name, description=req.description, is_active=True)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return _cat_dict(cat)


# ── Sub-categories ─────────────────────────────────────────────────

@router.get("/subcategories")
async def list_subcategories(
    category_id: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = select(SubCategory).options(selectinload(SubCategory.category)).where(
        SubCategory.family_id == current_user.family_id
    ).order_by(SubCategory.name)
    if category_id:
        q = q.where(SubCategory.category_id == category_id)
    rows = (await db.execute(q)).scalars().all()
    return [_sub_dict(s, s.category) for s in rows]


@router.post("/subcategories", status_code=status.HTTP_201_CREATED)
async def create_subcategory(
    req: CreateSubCategoryRequest,
    current_user: TokenData = Depends(require_role("superadmin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    cat = (await db.execute(
        select(Category).where(Category.id == req.category_id, Category.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not cat:
        raise HTTPException(400, "Invalid category")
    sub = SubCategory(family_id=current_user.family_id, category_id=req.category_id,
                      name=req.name, description=req.description, is_active=True)
    db.add(sub)
    await db.commit()
    await db.refresh(sub)
    return _sub_dict(sub, cat)


# ── Budgets ────────────────────────────────────────────────────────

@router.get("/budgets")
async def list_budgets(
    year: Optional[int] = None, month: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (select(Budget)
         .options(selectinload(Budget.category), selectinload(Budget.sub_category))
         .where(Budget.family_id == current_user.family_id)
         .order_by(Budget.year.desc(), Budget.month.desc()))
    if year:
        q = q.where(Budget.year == year)
    if month:
        q = q.where(Budget.month == month)
    rows = (await db.execute(q)).scalars().all()
    return [_budget_dict(b) for b in rows]


@router.post("/budgets", status_code=status.HTTP_201_CREATED)
async def create_budget(
    req: CreateBudgetRequest,
    current_user: TokenData = Depends(require_role("superadmin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    if req.period not in ("monthly", "yearly"):
        raise HTTPException(400, "Invalid period")
    if req.period == "monthly" and (req.month is None or req.month < 1 or req.month > 12):
        raise HTTPException(400, "month is required for monthly budgets")
    if req.category_id is None and req.sub_category_id is None:
        raise HTTPException(400, "category_id or sub_category_id is required")
    budget = Budget(
        family_id=current_user.family_id, created_by_user_id=current_user.user_id,
        category_id=req.category_id, sub_category_id=req.sub_category_id,
        period=BudgetPeriod(req.period), year=req.year, month=req.month,
        amount=req.amount, is_active=True,
    )
    db.add(budget)
    await db.commit()
    result = await db.execute(
        select(Budget).options(selectinload(Budget.category), selectinload(Budget.sub_category))
        .where(Budget.id == budget.id)
    )
    return _budget_dict(result.scalar_one())


# ── Budget Expenses ────────────────────────────────────────────────

@router.get("/expenses")
async def list_budget_expenses(
    year: Optional[int] = None, month: Optional[int] = None,
    category_id: Optional[int] = None, sub_category_id: Optional[int] = None,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    q = (select(BudgetExpense)
         .options(selectinload(BudgetExpense.category), selectinload(BudgetExpense.sub_category))
         .where(BudgetExpense.family_id == current_user.family_id)
         .order_by(BudgetExpense.date.desc(), BudgetExpense.created_at.desc()))
    if year:
        q = q.where(extract("year", BudgetExpense.date) == year)
    if month:
        q = q.where(extract("month", BudgetExpense.date) == month)
    if category_id:
        q = q.where(BudgetExpense.category_id == category_id)
    if sub_category_id:
        q = q.where(BudgetExpense.sub_category_id == sub_category_id)
    rows = (await db.execute(q)).scalars().all()
    return [_expense_dict(e) for e in rows]


@router.post("/expenses", status_code=status.HTTP_201_CREATED)
async def create_budget_expense(
    req: CreateBudgetExpenseRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    date = _parse_date(req.date)
    sub = (await db.execute(
        select(SubCategory).where(SubCategory.id == req.sub_category_id, SubCategory.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not sub:
        raise HTTPException(400, "Invalid subcategory")
    if sub.category_id != req.category_id:
        raise HTTPException(400, "subcategory does not belong to category")
    exp = BudgetExpense(
        family_id=current_user.family_id, created_by_user_id=current_user.user_id,
        category_id=req.category_id, sub_category_id=req.sub_category_id,
        title=req.title, description=req.description, amount=req.amount,
        currency=req.currency or "USD", date=date, merchant=req.merchant, notes=req.notes,
    )
    db.add(exp)
    await db.commit()
    result = await db.execute(
        select(BudgetExpense).options(selectinload(BudgetExpense.category), selectinload(BudgetExpense.sub_category))
        .where(BudgetExpense.id == exp.id)
    )
    return _expense_dict(result.scalar_one())


# ── Monthly Summary ────────────────────────────────────────────────

@router.get("/summary/monthly")
async def monthly_summary(
    year: int = Query(...), month: int = Query(...),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    fid = current_user.family_id

    cat_totals = (await db.execute(
        select(BudgetExpense.category_id, Category.name, func.coalesce(func.sum(BudgetExpense.amount), 0))
        .join(Category, Category.id == BudgetExpense.category_id)
        .where(BudgetExpense.family_id == fid,
               extract("year", BudgetExpense.date) == year,
               extract("month", BudgetExpense.date) == month)
        .group_by(BudgetExpense.category_id, Category.name)
        .order_by(func.sum(BudgetExpense.amount).desc())
    )).all()

    sub_totals = (await db.execute(
        select(BudgetExpense.category_id, BudgetExpense.sub_category_id,
               SubCategory.name, func.coalesce(func.sum(BudgetExpense.amount), 0))
        .join(SubCategory, SubCategory.id == BudgetExpense.sub_category_id)
        .where(BudgetExpense.family_id == fid,
               extract("year", BudgetExpense.date) == year,
               extract("month", BudgetExpense.date) == month)
        .group_by(BudgetExpense.category_id, BudgetExpense.sub_category_id, SubCategory.name)
        .order_by(func.sum(BudgetExpense.amount).desc())
    )).all()

    total_row = (await db.execute(
        select(func.coalesce(func.sum(BudgetExpense.amount), 0))
        .where(BudgetExpense.family_id == fid,
               extract("year", BudgetExpense.date) == year,
               extract("month", BudgetExpense.date) == month)
    )).scalar()

    return {
        "year": year, "month": month, "total_spent": float(total_row or 0),
        "by_category": [{"category_id": r[0], "category_name": r[1], "total_amount": float(r[2])} for r in cat_totals],
        "by_subcategory": [{"category_id": r[0], "sub_category_id": r[1], "sub_category_name": r[2], "total_amount": float(r[3])} for r in sub_totals],
        "generated_at": datetime.utcnow().isoformat(),
    }


# ── CSV Import: Categories ─────────────────────────────────────────

@router.post("/import/categories-csv")
async def import_categories_csv(
    file: UploadFile = File(...),
    current_user: TokenData = Depends(require_role("superadmin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    fid = current_user.family_id
    content = (await file.read()).decode("utf-8-sig")
    reader = csv.reader(io.StringIO(content))

    section = "none"
    last_expense_cat = ""
    created_cats = created_subs = skipped = 0

    async def upsert_cat(cat_type: CategoryType, name: str):
        name = name.strip()
        if not name:
            return None, False
        existing = (await db.execute(
            select(Category).where(Category.family_id == fid, Category.type == cat_type, Category.name == name)
        )).scalar_one_or_none()
        if existing:
            return existing, False
        cat = Category(family_id=fid, type=cat_type, name=name, is_active=True)
        db.add(cat)
        await db.flush()
        return cat, True

    async def upsert_sub(category_id: int, name: str):
        name = name.strip()
        if not name:
            return False
        existing = (await db.execute(
            select(SubCategory).where(SubCategory.family_id == fid, SubCategory.category_id == category_id, SubCategory.name == name)
        )).scalar_one_or_none()
        if existing:
            return False
        db.add(SubCategory(family_id=fid, category_id=category_id, name=name, is_active=True))
        await db.flush()
        return True

    for row in reader:
        col0 = row[0].strip() if len(row) > 0 else ""
        col2 = row[2].strip() if len(row) > 2 else ""

        if col0.lower() == "income categories":
            section = "income"; last_expense_cat = ""; continue
        if col0.lower().startswith("expense categories"):
            section = "expense"; last_expense_cat = ""; continue
        if col0.lower() == "savings categories":
            section = "savings"; last_expense_cat = ""; continue
        if col0.lower() == "yearly saving goal":
            section = "none"; continue

        if not col0 and not col2:
            continue
        if col0.startswith("READ THIS FIRST") or col0.startswith("I WILL NO LONGER") or col0.startswith("-"):
            continue

        if section in ("income", "savings"):
            cat, created = await upsert_cat(CategoryType.savings, col0)
            if cat and created:
                created_cats += 1
            elif not cat:
                skipped += 1
        elif section == "expense":
            if col0:
                last_expense_cat = col0
                cat, created = await upsert_cat(CategoryType.expense, col0)
                if cat and created:
                    created_cats += 1
            if col2 and last_expense_cat:
                cat, _ = await upsert_cat(CategoryType.expense, last_expense_cat)
                if cat:
                    if await upsert_sub(cat.id, col2):
                        created_subs += 1
                else:
                    skipped += 1
        else:
            skipped += 1

    await db.commit()
    return {"created_categories": created_cats, "created_sub_categories": created_subs, "skipped": skipped}


# ── CSV Import: Monthly ────────────────────────────────────────────

YEAR_RE = re.compile(r"\b(\d{4})\b")


@router.post("/import/monthly-csv")
async def import_monthly_csv(
    files: list[UploadFile] = File(None),
    file: UploadFile = File(None),
    current_user: TokenData = Depends(require_role("superadmin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    uploads = files or ([file] if file else [])
    if not uploads:
        raise HTTPException(400, "files is required")

    total_created = total_skipped = total_cats = total_subs = 0
    fid = current_user.family_id
    uid = current_user.user_id

    for upload in uploads:
        c, s, cc, cs = await _import_one_monthly(db, fid, uid, upload)
        total_created += c; total_skipped += s; total_cats += cc; total_subs += cs

    await db.commit()
    return {"created_budget_expenses": total_created, "skipped": total_skipped,
            "created_categories": total_cats, "created_sub_categories": total_subs}


async def _import_one_monthly(db: AsyncSession, fid: int, uid: int, upload: UploadFile):
    content = (await upload.read()).decode("utf-8-sig")
    reader = csv.reader(io.StringIO(content))
    year = datetime.now().year
    date_idx = cost_idx = cat_idx = notes_idx = -1
    in_expenses = False
    created = skipped = created_cats = created_subs = 0

    def parse_money(s: str):
        s = s.strip().replace("$", "").replace(",", "").strip()
        try:
            return float(s)
        except ValueError:
            return None

    async def ensure_imported_cat():
        existing = (await db.execute(
            select(Category).where(Category.family_id == fid, Category.type == CategoryType.expense, Category.name == "Imported")
        )).scalar_one_or_none()
        if existing:
            return existing, False
        cat = Category(family_id=fid, type=CategoryType.expense, name="Imported", is_active=True)
        db.add(cat)
        await db.flush()
        return cat, True

    async def resolve_cat_sub(name: str):
        name = name.strip()
        if not name:
            return 0, 0, False, False
        sub = (await db.execute(
            select(SubCategory).where(SubCategory.family_id == fid, SubCategory.name == name)
        )).scalar_one_or_none()
        if sub:
            return sub.category_id, sub.id, False, False
        imp_cat, new_cat = await ensure_imported_cat()
        existing = (await db.execute(
            select(SubCategory).where(SubCategory.family_id == fid, SubCategory.category_id == imp_cat.id, SubCategory.name == name)
        )).scalar_one_or_none()
        if existing:
            return existing.category_id, existing.id, new_cat, False
        new_sub = SubCategory(family_id=fid, category_id=imp_cat.id, name=name, is_active=True)
        db.add(new_sub)
        await db.flush()
        return imp_cat.id, new_sub.id, new_cat, True

    def parse_date(s: str):
        parts = s.strip().split()
        if len(parts) < 2:
            return None
        try:
            mon = datetime.strptime(parts[0].capitalize(), "%b").month
            day = int(parts[1])
            return datetime(year, mon, day)
        except (ValueError, IndexError):
            return None

    for row in reader:
        if not in_expenses:
            for col in row:
                m = YEAR_RE.search(col)
                if m:
                    y = int(m.group(1))
                    if 2000 <= y <= 2100:
                        year = y; break

        if not in_expenses:
            for i, cell in enumerate(row):
                cell = cell.strip().lower()
                if cell == "date": date_idx = i
                if cell == "cost": cost_idx = i
                if cell == "category": cat_idx = i
                if cell == "notes": notes_idx = i
            if date_idx >= 0 and cost_idx >= 0 and cat_idx >= 0:
                in_expenses = True
            continue

        if date_idx >= len(row):
            continue
        date_str = row[date_idx].strip()
        if not date_str:
            continue
        if date_str.lower() in ("summary", "income", "savings"):
            break

        dt = parse_date(date_str)
        if not dt:
            skipped += 1; continue

        amt_str = row[cost_idx].strip() if cost_idx < len(row) else ""
        amt = parse_money(amt_str)
        if amt is None or amt <= 0:
            skipped += 1; continue

        cat_name = row[cat_idx].strip() if cat_idx < len(row) else ""
        cat_id, sub_id, new_c, new_s = await resolve_cat_sub(cat_name)
        if new_c: created_cats += 1
        if new_s: created_subs += 1

        merchant = row[notes_idx].strip() if notes_idx >= 0 and notes_idx < len(row) else ""
        title = cat_name or "Imported"

        db.add(BudgetExpense(
            family_id=fid, created_by_user_id=uid, category_id=cat_id,
            sub_category_id=sub_id, title=title, amount=amt, currency="USD",
            date=dt, merchant=merchant,
        ))
        created += 1

    return created, skipped, created_cats, created_subs
