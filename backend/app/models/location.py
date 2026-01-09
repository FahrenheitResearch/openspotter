import uuid
from datetime import datetime
from sqlalchemy import Column, Float, DateTime, ForeignKey, String, Index
from sqlalchemy.orm import relationship

from app.database import Base
from app.models.base import PortableUUID as UUID


class Location(Base):
    __tablename__ = "locations"

    id = Column(UUID(), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )

    # Geographic coordinates
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    altitude = Column(Float, nullable=True)  # meters above sea level
    accuracy = Column(Float, nullable=True)  # meters

    # Movement
    heading = Column(Float, nullable=True)  # degrees (0-360)
    speed = Column(Float, nullable=True)  # meters per second

    # Visibility setting at time of update
    visibility = Column(String(20), default="public", nullable=False)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationship
    user = relationship("User", back_populates="locations")

    # Indexes for efficient querying
    __table_args__ = (
        Index("idx_locations_user_timestamp", "user_id", "timestamp"),
        Index("idx_locations_geo", "latitude", "longitude"),
    )

    def __repr__(self):
        return f"<Location {self.latitude}, {self.longitude} @ {self.timestamp}>"

    def to_geojson_feature(self, include_user: bool = False) -> dict:
        """Convert location to GeoJSON Feature format."""
        properties = {
            "timestamp": self.timestamp.isoformat(),
            "altitude": self.altitude,
            "accuracy": self.accuracy,
            "heading": self.heading,
            "speed": self.speed,
        }

        if include_user and self.user:
            properties["user_id"] = str(self.user_id)
            properties["callsign"] = self.user.callsign
            properties["role"] = self.user.role.value

        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.longitude, self.latitude],
            },
            "properties": properties,
        }
