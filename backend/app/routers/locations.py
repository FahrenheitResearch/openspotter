from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models.user import User, UserRole
from app.models.location import Location
from app.schemas.location import (
    LocationUpdate,
    LocationResponse,
    ActiveSpottersResponse,
    LocationHistoryResponse,
)
from app.utils.deps import get_current_user, get_current_user_optional
from app.websocket.manager import location_manager
from app.config import get_settings

settings = get_settings()
router = APIRouter()


@router.get("/active", response_model=ActiveSpottersResponse)
async def get_active_spotters(
    user: Optional[User] = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
):
    """Get all currently active spotters' locations as GeoJSON."""
    # Get locations from the last 15 minutes
    since = datetime.utcnow() - timedelta(minutes=15)

    # Build base query
    query = select(Location).where(Location.timestamp >= since)

    # Filter by visibility based on current user
    if user is None:
        query = query.where(Location.visibility == "public")
    elif user.role in [UserRole.COORDINATOR, UserRole.ADMIN]:
        pass  # Coordinators see all
    elif user.role == UserRole.VERIFIED_SPOTTER:
        query = query.where(Location.visibility.in_(["public", "verified"]))
    else:
        query = query.where(Location.visibility == "public")

    # Get the most recent location per user
    subquery = (
        select(Location.user_id, func.max(Location.timestamp).label("max_timestamp"))
        .where(Location.timestamp >= since)
        .group_by(Location.user_id)
        .subquery()
    )

    query = (
        select(Location)
        .join(
            subquery,
            and_(
                Location.user_id == subquery.c.user_id,
                Location.timestamp == subquery.c.max_timestamp,
            ),
        )
    )

    result = await db.execute(query)
    locations = result.scalars().all()

    # Build GeoJSON features
    features = []
    for loc in locations:
        await db.refresh(loc, ["user"])
        features.append(loc.to_geojson_feature(include_user=True))

    return ActiveSpottersResponse(
        features=features,
        count=len(features),
    )


@router.get("/history/{user_id}", response_model=LocationHistoryResponse)
async def get_location_history(
    user_id: UUID,
    hours: int = Query(24, ge=1, le=168),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get location history for a user."""
    # Users can see their own history, coordinators can see anyone's
    if user_id != current_user.id and not current_user.is_coordinator_or_above:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this user's history",
        )

    since = datetime.utcnow() - timedelta(hours=hours)

    query = (
        select(Location)
        .where(Location.user_id == user_id, Location.timestamp >= since)
        .order_by(Location.timestamp.desc())
        .limit(1000)
    )

    result = await db.execute(query)
    locations = result.scalars().all()

    return LocationHistoryResponse(
        locations=[LocationResponse.model_validate(loc) for loc in locations],
        count=len(locations),
    )


@router.post("/update", response_model=LocationResponse)
async def update_location(
    data: LocationUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update current user's location (HTTP fallback for WebSocket)."""
    location = Location(
        user_id=user.id,
        latitude=data.latitude,
        longitude=data.longitude,
        altitude=data.altitude,
        accuracy=data.accuracy,
        heading=data.heading,
        speed=data.speed,
        visibility=data.visibility or user.share_location_with,
    )

    db.add(location)
    await db.flush()
    await db.refresh(location)

    # Broadcast to WebSocket clients
    await location_manager.broadcast_location(user, location)

    return LocationResponse.model_validate(location)


@router.delete("/history")
async def clear_location_history(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear all location history for current user."""
    from sqlalchemy import delete

    await db.execute(delete(Location).where(Location.user_id == user.id))
    await db.flush()

    return {"message": "Location history cleared"}


@router.websocket("/ws")
async def websocket_location(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time location updates."""
    await websocket.accept()

    # Authenticate via token in first message
    try:
        auth_message = await websocket.receive_json()
        token = auth_message.get("token")

        if not token:
            await websocket.close(code=4001, reason="Authentication required")
            return

        from app.services.auth import decode_token

        payload = decode_token(token)
        if not payload or payload.get("type") != "access":
            await websocket.close(code=4001, reason="Invalid token")
            return

        user_id = payload.get("sub")
        result = await db.execute(select(User).where(User.id == UUID(user_id)))
        user = result.scalar_one_or_none()

        if not user or not user.is_active:
            await websocket.close(code=4001, reason="User not found")
            return

    except Exception:
        await websocket.close(code=4001, reason="Authentication failed")
        return

    # Register connection
    await location_manager.connect(websocket, user)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "location_update":
                # Save and broadcast location
                location = Location(
                    user_id=user.id,
                    latitude=data["latitude"],
                    longitude=data["longitude"],
                    altitude=data.get("altitude"),
                    accuracy=data.get("accuracy"),
                    heading=data.get("heading"),
                    speed=data.get("speed"),
                    visibility=data.get("visibility", user.share_location_with),
                )

                db.add(location)
                await db.flush()

                await location_manager.broadcast_location(user, location)

            elif data.get("type") == "stop_sharing":
                # Remove from active spotters
                await location_manager.stop_sharing(user)

    except WebSocketDisconnect:
        location_manager.disconnect(websocket, user)
    except Exception as e:
        print(f"WebSocket error: {e}")
        location_manager.disconnect(websocket, user)
