from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.user import UserPublic, UserPrivate, UserUpdate, UserRoleUpdate, UserList
from app.utils.deps import get_current_user, require_coordinator, require_admin

router = APIRouter()


@router.get("/me", response_model=UserPrivate)
async def get_current_user_profile(
    user: User = Depends(get_current_user),
):
    """Get current user's profile."""
    return user


@router.patch("/me", response_model=UserPrivate)
async def update_current_user(
    data: UserUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's profile."""
    update_data = data.model_dump(exclude_unset=True)

    # Check callsign uniqueness if updating
    if "callsign" in update_data and update_data["callsign"]:
        result = await db.execute(
            select(User).where(
                User.callsign == update_data["callsign"],
                User.id != user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Callsign already taken",
            )

    for field, value in update_data.items():
        setattr(user, field, value)

    await db.flush()
    await db.refresh(user)

    return user


@router.delete("/me")
async def delete_current_user(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete current user's account (soft delete)."""
    user.is_active = False
    await db.flush()

    return {"message": "Account deleted successfully"}


@router.get("/me/export")
async def export_user_data(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export all user data (GDPR compliance)."""
    # Get all user's data
    from app.models.location import Location
    from app.models.report import Report
    from app.models.message import Message

    locations_result = await db.execute(
        select(Location).where(Location.user_id == user.id)
    )
    locations = locations_result.scalars().all()

    reports_result = await db.execute(
        select(Report).where(Report.user_id == user.id)
    )
    reports = reports_result.scalars().all()

    messages_result = await db.execute(
        select(Message).where(Message.sender_id == user.id)
    )
    messages = messages_result.scalars().all()

    return {
        "user": {
            "id": str(user.id),
            "email": user.email,
            "callsign": user.callsign,
            "display_name": user.display_name,
            "role": user.role.value,
            "bio": user.bio,
            "location_city": user.location_city,
            "location_state": user.location_state,
            "created_at": user.created_at.isoformat(),
        },
        "locations": [
            {
                "latitude": loc.latitude,
                "longitude": loc.longitude,
                "timestamp": loc.timestamp.isoformat(),
            }
            for loc in locations
        ],
        "reports": [
            {
                "id": str(r.id),
                "type": r.type.value,
                "description": r.description,
                "latitude": r.latitude,
                "longitude": r.longitude,
                "created_at": r.created_at.isoformat(),
            }
            for r in reports
        ],
        "messages": [
            {
                "content": m.content,
                "created_at": m.created_at.isoformat(),
            }
            for m in messages
        ],
    }


@router.get("/{user_id}", response_model=UserPublic)
async def get_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a user's public profile."""
    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return user


@router.get("", response_model=UserList)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    role: Optional[UserRole] = None,
    search: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    """List users (public profiles only)."""
    query = select(User).where(User.is_active == True)

    if role:
        query = query.where(User.role == role)

    if search:
        query = query.where(
            (User.callsign.ilike(f"%{search}%")) | (User.display_name.ilike(f"%{search}%"))
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    users = result.scalars().all()

    return UserList(
        users=users,
        total=total,
        page=page,
        per_page=per_page,
    )


# Coordinator endpoints
@router.patch("/{user_id}/verify", response_model=UserPublic)
async def verify_user(
    user_id: UUID,
    coordinator: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
):
    """Verify a spotter (upgrade to verified_spotter role)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.role != UserRole.SPOTTER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User is already verified or has a higher role",
        )

    user.role = UserRole.VERIFIED_SPOTTER
    await db.flush()
    await db.refresh(user)

    return user


# Admin endpoints
@router.patch("/{user_id}/role", response_model=UserPublic)
async def update_user_role(
    user_id: UUID,
    data: UserRoleUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Update a user's role (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role",
        )

    user.role = data.role
    await db.flush()
    await db.refresh(user)

    return user


@router.delete("/{user_id}")
async def admin_delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Delete a user (admin only)."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    if user.id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    user.is_active = False
    await db.flush()

    return {"message": "User deleted successfully"}
