import uuid
from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, Text, Enum, Index, JSON
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PortableUUID as UUID


class ReportType(str, PyEnum):
    TORNADO = "tornado"
    FUNNEL_CLOUD = "funnel_cloud"
    WALL_CLOUD = "wall_cloud"
    ROTATION = "rotation"
    HAIL = "hail"
    WIND_DAMAGE = "wind_damage"
    FLOODING = "flooding"
    FLASH_FLOOD = "flash_flood"
    HEAVY_RAIN = "heavy_rain"
    LIGHTNING = "lightning"
    DUST_STORM = "dust_storm"
    WILDFIRE = "wildfire"
    OTHER = "other"


class Report(Base):
    __tablename__ = "reports"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Report type and details
    type = Column(Enum(ReportType, name="report_type"), nullable=False, index=True)
    title = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)

    # Location
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    location_description = Column(String(500), nullable=True)  # "2 miles NW of Springfield"

    # Severity (1-5 scale)
    severity = Column(Integer, nullable=True)

    # Type-specific data
    hail_size = Column(Float, nullable=True)  # inches
    wind_speed = Column(Integer, nullable=True)  # mph estimated
    tornado_rating = Column(String(10), nullable=True)  # EF0-EF5

    # Media attachments
    media_urls = Column(JSON, default=list, nullable=False)

    # Verification
    is_verified = Column(Boolean, default=False, nullable=False)
    verified_by_id = Column(
        UUID(), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    verified_at = Column(DateTime, nullable=True)
    verification_notes = Column(Text, nullable=True)

    # Timestamps
    event_time = Column(DateTime, nullable=True)  # When the event occurred
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(
        DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    # Soft delete
    is_deleted = Column(Boolean, default=False, nullable=False)
    deleted_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="reports", foreign_keys=[user_id])
    verified_by = relationship("User", foreign_keys=[verified_by_id])

    # Indexes
    __table_args__ = (
        Index("idx_reports_type_created", "type", "created_at"),
        Index("idx_reports_geo", "latitude", "longitude"),
        Index("idx_reports_user_created", "user_id", "created_at"),
    )

    def __repr__(self):
        return f"<Report {self.type.value} @ {self.latitude}, {self.longitude}>"

    def to_geojson_feature(self, include_user: bool = False) -> dict:
        """Convert report to GeoJSON Feature format."""
        properties = {
            "id": str(self.id),
            "type": self.type.value,
            "title": self.title,
            "description": self.description,
            "severity": self.severity,
            "hail_size": self.hail_size,
            "wind_speed": self.wind_speed,
            "tornado_rating": self.tornado_rating,
            "is_verified": self.is_verified,
            "event_time": self.event_time.isoformat() if self.event_time else None,
            "created_at": self.created_at.isoformat(),
            "media_urls": self.media_urls,
        }

        if include_user and self.user:
            properties["reporter"] = {
                "id": str(self.user_id),
                "callsign": self.user.callsign,
                "role": self.user.role.value,
            }

        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            },
            "properties": properties,
        }

    @property
    def severity_label(self) -> str:
        """Get human-readable severity label."""
        labels = {
            1: "Minor",
            2: "Moderate",
            3: "Significant",
            4: "Severe",
            5: "Extreme",
        }
        return labels.get(self.severity, "Unknown")
