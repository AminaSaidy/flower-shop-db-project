from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import get_current_user
from app.db.models import User
from app.db.session import get_db

router = APIRouter(prefix="/users", tags=["users"])

VALID_ROLES = ["admin", "manager", "customer"]


class RoleUpdate(BaseModel):
    role: str


async def require_admin(db: AsyncSession, user: dict) -> User:
    result = await db.execute(select(User).where(User.id == user["user_id"]))
    current = result.scalar_one_or_none()
    if not current or current.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current


def user_payload(user: User) -> dict:
    return {
        "id": str(user.id),
        "email": user.email,
        "full_name": user.full_name,
        "phone": user.phone,
        "role": user.role,
        "created_at": str(user.created_at),
    }


@router.get("/", summary="List users (admin)")
async def list_users(
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await require_admin(db, user)
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return {"users": [user_payload(item) for item in users]}


@router.patch("/{user_id}/role", summary="Update user role (admin)")
async def update_user_role(
    user_id: str,
    payload: RoleUpdate,
    db: AsyncSession = Depends(get_db),
    user: dict = Depends(get_current_user),
):
    await require_admin(db, user)
    if payload.role not in VALID_ROLES:
        raise HTTPException(status_code=400, detail=f"Invalid role. Use: {VALID_ROLES}")

    result = await db.execute(select(User).where(User.id == user_id))
    target = result.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="User not found")

    target.role = payload.role
    await db.commit()
    await db.refresh(target)
    return user_payload(target)
