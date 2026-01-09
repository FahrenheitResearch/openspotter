import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Boolean, DateTime, Enum, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PortableUUID as UUID


class UserRole(str, PyEnum):
    SPOTTER = "spotter"
    VERIFIED_SPOTTER = "verified_spotter"
    COORDINATOR = "coordinator"
    ADMIN = "admin"


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    callsign = Column(String(50), unique=True, nullable=True, index=True)
    display_name = Column(String(100), nullable=True)

    role = Column(
        Enum(UserRole, name="user_role"),
        default=UserRole.SPOTTER,
        nullable=False,
    )

    is_active = Column(Boolean, default=True, nullable=False)
    is_email_verified = Column(Boolean, default=False, nullable=False)

    # 2FA
    totp_secret = Column(String(32), nullable=True)
    totp_enabled = Column(Boolean, default=False, nullable=False)

    # Profile
    bio = Column(Text, nullable=True)
    location_city = Column(String(100), nullable=True)
    location_state = Column(String(50), nullable=True)

    # Privacy settings
    share_location_with = Column(
        String(20), default="public", nullable=False
    )  # public, verified, coordinators

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )
    last_login_at = Column(DateTime, nullable=True)

    # Email verification
    email_verification_token = Column(String(100), nullable=True)
    email_verification_sent_at = Column(DateTime, nullable=True)

    # Password reset
    password_reset_token = Column(String(100), nullable=True)
    password_reset_sent_at = Column(DateTime, nullable=True)

    # Relationships
    locations = relationship("Location", back_populates="user", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="user", foreign_keys="Report.user_id", cascade="all, delete-orphan")
    sent_messages = relationship(
        "Message", back_populates="sender", foreign_keys="Message.sender_id"
    )

    def __repr__(self):
        return f"<User {self.email} ({self.callsign})>"

    @property
    def is_coordinator_or_above(self) -> bool:
        return self.role in [UserRole.COORDINATOR, UserRole.ADMIN]

    @property
    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    @property
    def can_verify_reports(self) -> bool:
        return self.role in [UserRole.COORDINATOR, UserRole.ADMIN]

    @property
    def can_verify_users(self) -> bool:
        return self.role in [UserRole.COORDINATOR, UserRole.ADMIN]
