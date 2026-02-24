from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import TokenData, get_current_user, require_role
from app.database import get_db
from app.models import Family, FamilyMembership, FamilyRole, User

router = APIRouter(prefix="/api/v1/families", tags=["families"])


class CreateFamilyRequest(BaseModel):
    name: str
    currency: str = "USD"


class AddMemberRequest(BaseModel):
    email: str
    role: str = "member"


class UpdateRoleRequest(BaseModel):
    role: str


@router.get("")
async def list_my_families(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Family)
        .join(FamilyMembership, FamilyMembership.family_id == Family.id)
        .where(FamilyMembership.user_id == current_user.user_id, FamilyMembership.status == "active")
    )
    families = result.scalars().all()
    return [{"id": f.id, "name": f.name, "currency": f.currency, "owner_user_id": f.owner_user_id} for f in families]


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_family(
    req: CreateFamilyRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    family = Family(name=req.name, currency=req.currency, owner_user_id=current_user.user_id)
    db.add(family)
    await db.flush()
    db.add(FamilyMembership(family_id=family.id, user_id=current_user.user_id, role=FamilyRole.superadmin, status="active"))
    await db.commit()
    await db.refresh(family)
    return {"id": family.id, "name": family.name, "currency": family.currency}


@router.get("/members")
async def list_members(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(FamilyMembership, User)
        .join(User, User.id == FamilyMembership.user_id)
        .where(FamilyMembership.family_id == current_user.family_id)
    )
    rows = result.all()
    return [
        {"id": m.id, "user_id": m.user_id, "role": m.role.value, "status": m.status,
         "user": {"id": u.id, "first_name": u.first_name, "last_name": u.last_name, "email": u.email}}
        for m, u in rows
    ]


@router.post("/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    req: AddMemberRequest,
    current_user: TokenData = Depends(require_role("superadmin", "admin")),
    db: AsyncSession = Depends(get_db),
):
    user = (await db.execute(select(User).where(User.email == req.email))).scalar_one_or_none()
    if not user:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "User not found")
    existing = (await db.execute(
        select(FamilyMembership).where(FamilyMembership.family_id == current_user.family_id, FamilyMembership.user_id == user.id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status.HTTP_409_CONFLICT, "User already a member")
    role = FamilyRole(req.role) if req.role in [r.value for r in FamilyRole] else FamilyRole.member
    mem = FamilyMembership(family_id=current_user.family_id, user_id=user.id, role=role, status="active")
    db.add(mem)
    await db.commit()
    return {"id": mem.id, "user_id": user.id, "role": mem.role.value}


@router.put("/members/{member_id}/role")
async def update_member_role(
    member_id: int,
    req: UpdateRoleRequest,
    current_user: TokenData = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    mem = (await db.execute(
        select(FamilyMembership).where(FamilyMembership.id == member_id, FamilyMembership.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not mem:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    mem.role = FamilyRole(req.role)
    await db.commit()
    return {"id": mem.id, "role": mem.role.value}


@router.delete("/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    member_id: int,
    current_user: TokenData = Depends(require_role("superadmin")),
    db: AsyncSession = Depends(get_db),
):
    mem = (await db.execute(
        select(FamilyMembership).where(FamilyMembership.id == member_id, FamilyMembership.family_id == current_user.family_id)
    )).scalar_one_or_none()
    if not mem:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Member not found")
    await db.delete(mem)
    await db.commit()
