from datetime import datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_, and_

from app.database import get_db
from app.models.user import User, UserRole
from app.models.message import Message, Channel
from app.schemas.message import (
    ChannelCreate,
    ChannelResponse,
    ChannelListResponse,
    MessageCreate,
    MessageResponse,
    MessageListResponse,
    SenderInfo,
)
from app.utils.deps import get_current_user, require_coordinator
from app.websocket.manager import chat_manager

router = APIRouter()


# Channel endpoints
@router.get("/channels", response_model=ChannelListResponse)
async def list_channels(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List available chat channels."""
    role_hierarchy = {
        "spotter": 0,
        "verified_spotter": 1,
        "coordinator": 2,
        "admin": 3,
    }
    user_level = role_hierarchy.get(user.role.value, 0)

    # Get channels the user can access
    query = select(Channel).where(
        or_(
            Channel.is_public == True,
            Channel.created_by_id == user.id,
        )
    )

    result = await db.execute(query)
    channels = result.scalars().all()

    # Filter by role
    accessible_channels = [
        c for c in channels if role_hierarchy.get(c.min_role, 0) <= user_level
    ]

    return ChannelListResponse(
        channels=[ChannelResponse.model_validate(c) for c in accessible_channels],
        count=len(accessible_channels),
    )


@router.post("/channels", response_model=ChannelResponse, status_code=status.HTTP_201_CREATED)
async def create_channel(
    data: ChannelCreate,
    user: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
):
    """Create a new chat channel (coordinator only)."""
    # Check for duplicate name
    result = await db.execute(select(Channel).where(Channel.name == data.name))
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Channel name already exists",
        )

    channel = Channel(
        name=data.name,
        description=data.description,
        channel_type=data.channel_type,
        is_public=data.is_public,
        min_role=data.min_role,
        created_by_id=user.id,
    )

    db.add(channel)
    await db.flush()
    await db.refresh(channel)

    return ChannelResponse.model_validate(channel)


@router.get("/channels/{channel_id}/messages", response_model=MessageListResponse)
async def get_channel_messages(
    channel_id: UUID,
    before: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get messages from a channel."""
    # Check channel access
    result = await db.execute(select(Channel).where(Channel.id == channel_id))
    channel = result.scalar_one_or_none()

    if not channel:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Channel not found",
        )

    role_hierarchy = {"spotter": 0, "verified_spotter": 1, "coordinator": 2, "admin": 3}
    if role_hierarchy.get(user.role.value, 0) < role_hierarchy.get(channel.min_role, 0):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to access this channel",
        )

    # Get messages
    query = select(Message).where(
        Message.channel_id == channel_id,
        Message.is_deleted == False,
    )

    if before:
        query = query.where(Message.created_at < before)

    query = query.order_by(Message.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    messages = result.scalars().all()

    has_more = len(messages) > limit
    messages = messages[:limit]

    # Build response with sender info
    message_responses = []
    for msg in messages:
        await db.refresh(msg, ["sender"])
        resp = MessageResponse(
            id=msg.id,
            content=msg.content,
            sender=SenderInfo(
                id=msg.sender_id,
                callsign=msg.sender.callsign if msg.sender else None,
                role=msg.sender.role.value if msg.sender else "unknown",
            ),
            channel_id=msg.channel_id,
            recipient_id=msg.recipient_id,
            latitude=msg.latitude,
            longitude=msg.longitude,
            report_id=msg.report_id,
            created_at=msg.created_at,
            edited_at=msg.edited_at,
        )
        message_responses.append(resp)

    return MessageListResponse(
        messages=message_responses,
        count=len(message_responses),
        has_more=has_more,
    )


# Direct message endpoints
@router.get("/dm/{user_id}", response_model=MessageListResponse)
async def get_direct_messages(
    user_id: UUID,
    before: Optional[datetime] = None,
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get direct messages with another user."""
    query = select(Message).where(
        Message.is_deleted == False,
        Message.channel_id == None,
        or_(
            and_(Message.sender_id == current_user.id, Message.recipient_id == user_id),
            and_(Message.sender_id == user_id, Message.recipient_id == current_user.id),
        ),
    )

    if before:
        query = query.where(Message.created_at < before)

    query = query.order_by(Message.created_at.desc()).limit(limit + 1)
    result = await db.execute(query)
    messages = result.scalars().all()

    has_more = len(messages) > limit
    messages = messages[:limit]

    message_responses = []
    for msg in messages:
        await db.refresh(msg, ["sender"])
        resp = MessageResponse(
            id=msg.id,
            content=msg.content,
            sender=SenderInfo(
                id=msg.sender_id,
                callsign=msg.sender.callsign if msg.sender else None,
                role=msg.sender.role.value if msg.sender else "unknown",
            ),
            channel_id=msg.channel_id,
            recipient_id=msg.recipient_id,
            latitude=msg.latitude,
            longitude=msg.longitude,
            report_id=msg.report_id,
            created_at=msg.created_at,
            edited_at=msg.edited_at,
        )
        message_responses.append(resp)

    return MessageListResponse(
        messages=message_responses,
        count=len(message_responses),
        has_more=has_more,
    )


# Send message (HTTP fallback)
@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def send_message(
    data: MessageCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Send a message (HTTP fallback for WebSocket)."""
    if not data.channel_id and not data.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must specify either channel_id or recipient_id",
        )

    if data.channel_id and data.recipient_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot specify both channel_id and recipient_id",
        )

    # Verify channel access if sending to channel
    if data.channel_id:
        result = await db.execute(select(Channel).where(Channel.id == data.channel_id))
        channel = result.scalar_one_or_none()

        if not channel:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Channel not found",
            )

        role_hierarchy = {"spotter": 0, "verified_spotter": 1, "coordinator": 2, "admin": 3}
        if role_hierarchy.get(user.role.value, 0) < role_hierarchy.get(channel.min_role, 0):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to send to this channel",
            )

    message = Message(
        sender_id=user.id,
        channel_id=data.channel_id,
        recipient_id=data.recipient_id,
        content=data.content,
        latitude=data.latitude,
        longitude=data.longitude,
        report_id=data.report_id,
    )

    db.add(message)
    await db.flush()
    await db.refresh(message)

    # Broadcast via WebSocket
    await chat_manager.broadcast_message(user, message)

    return MessageResponse(
        id=message.id,
        content=message.content,
        sender=SenderInfo(id=user.id, callsign=user.callsign, role=user.role.value),
        channel_id=message.channel_id,
        recipient_id=message.recipient_id,
        latitude=message.latitude,
        longitude=message.longitude,
        report_id=message.report_id,
        created_at=message.created_at,
        edited_at=message.edited_at,
    )


@router.websocket("/ws")
async def websocket_chat(
    websocket: WebSocket,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()

    # Authenticate
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
    await chat_manager.connect(websocket, user)

    try:
        while True:
            data = await websocket.receive_json()

            if data.get("type") == "message":
                message = Message(
                    sender_id=user.id,
                    channel_id=UUID(data["channel_id"]) if data.get("channel_id") else None,
                    recipient_id=UUID(data["recipient_id"]) if data.get("recipient_id") else None,
                    content=data["content"],
                    latitude=data.get("latitude"),
                    longitude=data.get("longitude"),
                )

                db.add(message)
                await db.flush()
                await db.refresh(message)

                await chat_manager.broadcast_message(user, message)

            elif data.get("type") == "join_channel":
                await chat_manager.join_channel(websocket, UUID(data["channel_id"]))

            elif data.get("type") == "leave_channel":
                await chat_manager.leave_channel(websocket, UUID(data["channel_id"]))

    except WebSocketDisconnect:
        chat_manager.disconnect(websocket, user)
    except Exception as e:
        print(f"WebSocket error: {e}")
        chat_manager.disconnect(websocket, user)
