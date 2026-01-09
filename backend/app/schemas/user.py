from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field

from app.models.user import UserRole


# Base schemas
class UserBase(BaseModel):
    email: EmailStr
    callsign: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, max_length=100)


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    callsign: Optional[str] = Field(None, min_length=2, max_length=50)
    display_name: Optional[str] = Field(None, max_length=100)
    bio: Optional[str] = Field(None, max_length=500)
    location_city: Optional[str] = Field(None, max_length=100)
    location_state: Optional[str] = Field(None, max_length=50)
    share_location_with: Optional[str] = Field(None, pattern="^(public|verified|coordinators)$")


class UserRoleUpdate(BaseModel):
    role: UserRole


# Response schemas
class UserPublic(BaseModel):
    id: UUID
    callsign: Optional[str]
    display_name: Optional[str]
    role: UserRole
    bio: Optional[str]
    location_city: Optional[str]
    location_state: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class UserPrivate(UserPublic):
    """Full user data for the user themselves."""
    email: EmailStr
    is_active: bool
    is_email_verified: bool
    totp_enabled: bool
    share_location_with: str
    last_login_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class UserList(BaseModel):
    users: list[UserPublic]
    total: int
    page: int
    per_page: int
