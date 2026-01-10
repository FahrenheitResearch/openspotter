from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.models.report import ReportType


class ReportCreate(BaseModel):
    type: ReportType
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    location_description: Optional[str] = Field(None, max_length=500)
    severity: Optional[int] = Field(None, ge=1, le=5)
    hail_size: Optional[float] = Field(None, ge=0, le=10)  # inches
    wind_speed: Optional[int] = Field(None, ge=0, le=350)  # mph
    tornado_rating: Optional[str] = Field(None, pattern="^EF[0-5]$")
    event_time: Optional[datetime] = None
    media_urls: Optional[list[str]] = Field(default_factory=list)
    post_to_twitter: bool = False  # Whether to post to Twitter with WFO mention


class ReportUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    severity: Optional[int] = Field(None, ge=1, le=5)
    hail_size: Optional[float] = Field(None, ge=0, le=10)
    wind_speed: Optional[int] = Field(None, ge=0, le=350)
    tornado_rating: Optional[str] = Field(None, pattern="^EF[0-5]$")


class ReportVerify(BaseModel):
    is_verified: bool
    verification_notes: Optional[str] = Field(None, max_length=500)


class ReporterInfo(BaseModel):
    id: UUID
    callsign: Optional[str]
    role: str


class ReportResponse(BaseModel):
    id: UUID
    user_id: UUID
    type: ReportType
    title: Optional[str]
    description: Optional[str]
    latitude: float
    longitude: float
    location_description: Optional[str]
    severity: Optional[int]
    hail_size: Optional[float]
    wind_speed: Optional[int]
    tornado_rating: Optional[str]
    media_urls: list[str]
    is_verified: bool
    verified_by_id: Optional[UUID]
    verified_at: Optional[datetime]
    event_time: Optional[datetime]
    created_at: datetime
    updated_at: datetime
    reporter: Optional[ReporterInfo] = None

    class Config:
        from_attributes = True


class ReportListResponse(BaseModel):
    reports: list[ReportResponse]
    total: int
    page: int
    per_page: int


class ReportGeoJSONResponse(BaseModel):
    type: str = "FeatureCollection"
    features: list[dict]
    count: int
