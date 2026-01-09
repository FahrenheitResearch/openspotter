from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


class LocationUpdate(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    altitude: Optional[float] = None
    accuracy: Optional[float] = Field(None, ge=0)
    heading: Optional[float] = Field(None, ge=0, lt=360)
    speed: Optional[float] = Field(None, ge=0)
    visibility: Optional[str] = Field("public", pattern="^(public|verified|coordinators)$")


class LocationResponse(BaseModel):
    id: UUID
    user_id: UUID
    latitude: float
    longitude: float
    altitude: Optional[float]
    accuracy: Optional[float]
    heading: Optional[float]
    speed: Optional[float]
    visibility: str
    timestamp: datetime

    class Config:
        from_attributes = True


class SpotterLocation(BaseModel):
    """Active spotter location for map display."""
    user_id: UUID
    callsign: Optional[str]
    role: str
    latitude: float
    longitude: float
    heading: Optional[float]
    speed: Optional[float]
    timestamp: datetime


class ActiveSpottersResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]
    count: int


class LocationHistoryResponse(BaseModel):
    locations: list[LocationResponse]
    count: int
