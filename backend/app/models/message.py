import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Text, Boolean, Index, Float
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PortableUUID as UUID


class Channel(Base):
    """Chat channels for group messaging."""

    __tablename__ = "channels"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Channel type: regional, event, or direct
    channel_type = Column(String(20), default="regional", nullable=False)

    # For event-based channels
    event_id = Column(String(100), nullable=True)

    # Access control
    is_public = Column(Boolean, default=True, nullable=False)
    min_role = Column(String(20), default="spotter", nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_by_id = Column(UUID(), ForeignKey("users.id"), nullable=True)

    # Relationships
    messages = relationship("Message", back_populates="channel", cascade="all, delete-orphan")
    created_by = relationship("User")

    def __repr__(self):
        return f"<Channel {self.name}>"


class Message(Base):
    """Chat messages."""

    __tablename__ = "messages"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)

    # Sender
    sender_id = Column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Channel (for group messages)
    channel_id = Column(
        UUID(), ForeignKey("channels.id", ondelete="CASCADE"), nullable=True
    )

    # Direct message recipient (for DMs)
    recipient_id = Column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )

    # Message content
    content = Column(Text, nullable=False)

    # Optional location reference
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)

    # Optional report reference
    report_id = Column(
        UUID(), ForeignKey("reports.id", ondelete="SET NULL"), nullable=True
    )

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    edited_at = Column(DateTime, nullable=True)

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Relationships
    sender = relationship("User", back_populates="sent_messages", foreign_keys=[sender_id])
    recipient = relationship("User", foreign_keys=[recipient_id])
    channel = relationship("Channel", back_populates="messages")
    report = relationship("Report")

    # Indexes
    __table_args__ = (
        Index("idx_messages_channel_created", "channel_id", "created_at"),
        Index("idx_messages_dm", "sender_id", "recipient_id", "created_at"),
    )

    def __repr__(self):
        return f"<Message from {self.sender_id} @ {self.created_at}>"

    def to_dict(self, include_sender: bool = True) -> dict:
        """Convert message to dictionary."""
        data = {
            "id": str(self.id),
            "content": self.content,
            "channel_id": str(self.channel_id) if self.channel_id else None,
            "recipient_id": str(self.recipient_id) if self.recipient_id else None,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "report_id": str(self.report_id) if self.report_id else None,
            "created_at": self.created_at.isoformat(),
            "edited_at": self.edited_at.isoformat() if self.edited_at else None,
        }

        if include_sender and self.sender:
            data["sender"] = {
                "id": str(self.sender_id),
                "callsign": self.sender.callsign,
                "role": self.sender.role.value,
            }

        return data
