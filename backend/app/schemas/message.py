from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class ChannelCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = Field(None, max_length=500)
    channel_type: str = Field("regional", pattern="^(regional|event|direct)$")
    is_public: bool = True
    min_role: str = Field("spotter", pattern="^(spotter|verified_spotter|coordinator|admin)$")


class ChannelResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str]
    channel_type: str
    is_public: bool
    min_role: str
    created_at: datetime

    class Config:
        from_attributes = True


class ChannelListResponse(BaseModel):
    channels: list[ChannelResponse]
    count: int


class MessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=2000)
    channel_id: Optional[UUID] = None
    recipient_id: Optional[UUID] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    report_id: Optional[UUID] = None


class SenderInfo(BaseModel):
    id: UUID
    callsign: Optional[str]
    role: str


class MessageResponse(BaseModel):
    id: UUID
    content: str
    sender: SenderInfo
    channel_id: Optional[UUID]
    recipient_id: Optional[UUID]
    latitude: Optional[float]
    longitude: Optional[float]
    report_id: Optional[UUID]
    created_at: datetime
    edited_at: Optional[datetime]

    class Config:
        from_attributes = True


class MessageListResponse(BaseModel):
    messages: list[MessageResponse]
    count: int
    has_more: bool


class WebSocketMessage(BaseModel):
    """Message format for WebSocket communication."""
    type: str  # location_update, chat_message, report_new, etc.
    payload: dict
