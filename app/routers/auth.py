from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import (
    TokenData, create_token, get_current_user, hash_password, verify_password,
)
from app.database import get_db
from app.models import (
    Category, CategoryType, Family, FamilyMembership, FamilyRole,
    SubCategory, User,
)

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    first_name: str
    last_name: str
    email: EmailStr
    password: str
    phone: str = ""


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    token: str
    user: dict


DEFAULT_EXPENSE_CATEGORIES = [
    "Housing", "Utilities", "Food", "Transportation",
    "Medical & Healthcare", "DayCare", "Church",
]

DEFAULT_SUBCATEGORIES: dict[str, list[str]] = {
    "Housing": ["ADU", "Home Improvement", "Movie", "Camping", "Hair"],
    "Utilities": ["PGNE", "Water Dept", "Internet + Phone"],
    "Food": ["Restaurant", "Grocery", "Indian Grocery"],
    "Transportation": ["Gas"],
    "Medical & Healthcare": ["Medical Expense", "Insurance"],
    "DayCare": ["DayCare"],
    "Church": ["Church"],
}


def _user_dict(u: User) -> dict:
    return {
        "id": u.id, "first_name": u.first_name, "last_name": u.last_name,
        "email": u.email, "phone": u.phone, "avatar": u.avatar,
        "created_at": str(u.created_at), "updated_at": str(u.updated_at),
    }


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User with this email already exists")

    user = User(
        first_name=req.first_name, last_name=req.last_name,
        email=req.email, password=hash_password(req.password), phone=req.phone,
    )
    db.add(user)
    await db.flush()

    family = Family(name=f"{req.first_name} {req.last_name} Family", currency="USD", owner_user_id=user.id)
    db.add(family)
    await db.flush()

    # Seed default expense categories
    cat_map: dict[str, int] = {}
    for name in DEFAULT_EXPENSE_CATEGORIES:
        exists = (await db.execute(
            select(Category).where(Category.family_id == family.id, Category.type == CategoryType.expense, Category.name == name)
        )).scalar_one_or_none()
        if exists:
            cat_map[name] = exists.id
        else:
            cat = Category(family_id=family.id, type=CategoryType.expense, name=name, is_active=True)
            db.add(cat)
            await db.flush()
            cat_map[name] = cat.id

    # Seed default subcategories
    for cat_name, sub_names in DEFAULT_SUBCATEGORIES.items():
        cat_id = cat_map.get(cat_name)
        if not cat_id:
            continue
        for sub_name in sub_names:
            exists = (await db.execute(
                select(SubCategory).where(
                    SubCategory.family_id == family.id,
                    SubCategory.category_id == cat_id,
                    SubCategory.name == sub_name,
                )
            )).scalar_one_or_none()
            if not exists:
                db.add(SubCategory(family_id=family.id, category_id=cat_id, name=sub_name, is_active=True))

    membership = FamilyMembership(
        family_id=family.id, user_id=user.id,
        role=FamilyRole.superadmin, status="active",
    )
    db.add(membership)
    await db.commit()
    await db.refresh(user)

    token = create_token(user.id, user.email, family.id, membership.role.value)
    return AuthResponse(token=token, user=_user_dict(user))


@router.post("/login")
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user or not verify_password(req.password, user.password):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid credentials")

    membership = (await db.execute(
        select(FamilyMembership).where(
            FamilyMembership.user_id == user.id, FamilyMembership.status == "active"
        ).order_by(FamilyMembership.id)
    )).scalars().first()
    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is not part of any active family")

    token = create_token(user.id, user.email, membership.family_id, membership.role.value)
    return AuthResponse(token=token, user=_user_dict(user))


@router.get("/profile")
async def get_profile(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.id == current_user.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    return _user_dict(user)
