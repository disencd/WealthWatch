from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.auth import TokenData, get_current_user
from app.database import get_db
from app.models import Group, GroupMember, User

router = APIRouter(prefix="/api/v1/groups", tags=["groups"])


class CreateGroupRequest(BaseModel):
    name: str
    description: str = ""


class AddMemberRequest(BaseModel):
    user_id: int


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_group(
    req: CreateGroupRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    group = Group(name=req.name, description=req.description, created_by=current_user.user_id)
    db.add(group)
    await db.flush()
    db.add(GroupMember(group_id=group.id, user_id=current_user.user_id))
    await db.commit()
    await db.refresh(group)
    return {"id": group.id, "name": group.name, "description": group.description}


@router.get("")
async def get_groups(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    rows = (await db.execute(
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.user_id == current_user.user_id)
        .options(selectinload(Group.members))
    )).scalars().unique().all()
    return [
        {"id": g.id, "name": g.name, "description": g.description,
         "created_by": g.created_by, "members": [
             {"id": m.id, "first_name": m.first_name, "last_name": m.last_name, "email": m.email}
             for m in g.members
         ]}
        for g in rows
    ]


@router.get("/{id}")
async def get_group(
    id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = (await db.execute(
        select(Group).options(selectinload(Group.members)).where(Group.id == id)
    )).scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Group not found")
    return {"id": g.id, "name": g.name, "description": g.description,
            "created_by": g.created_by, "members": [
                {"id": m.id, "first_name": m.first_name, "last_name": m.last_name, "email": m.email}
                for m in g.members
            ]}


@router.post("/{id}/members", status_code=status.HTTP_201_CREATED)
async def add_member(
    id: int, req: AddMemberRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    g = (await db.execute(select(Group).where(Group.id == id))).scalar_one_or_none()
    if not g:
        raise HTTPException(404, "Group not found")
    existing = (await db.execute(
        select(GroupMember).where(GroupMember.group_id == id, GroupMember.user_id == req.user_id)
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(409, "User already a member")
    db.add(GroupMember(group_id=id, user_id=req.user_id))
    await db.commit()
    return {"group_id": id, "user_id": req.user_id}


@router.delete("/{id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_member(
    id: int, member_id: int,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    gm = (await db.execute(
        select(GroupMember).where(GroupMember.group_id == id, GroupMember.user_id == member_id)
    )).scalar_one_or_none()
    if not gm:
        raise HTTPException(404, "Member not found")
    await db.delete(gm)
    await db.commit()
