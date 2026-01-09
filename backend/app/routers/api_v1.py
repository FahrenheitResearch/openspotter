"""
Public API v1 - Open API for third-party integrations

This API is designed to be freely accessible with API key authentication
for integration with weather applications like RadarScope alternatives.
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, func

from app.database import get_db
from app.models.user import User
from app.models.location import Location
from app.models.report import Report, ReportType
from app.config import get_settings

settings = get_settings()
router = APIRouter()


# Simple API key validation (in production, use database-backed API keys)
async def validate_api_key(x_api_key: Optional[str] = Header(None)):
    """Validate API key for public API access."""
    # For now, allow unauthenticated access with rate limiting
    # In production, implement proper API key management
    return x_api_key


@router.get("/spotters")
async def get_active_spotters(
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    api_key: Optional[str] = Depends(validate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get active spotter locations as GeoJSON.

    Returns spotters who have shared their location in the last 15 minutes.
    Only includes spotters with public visibility.

    ## Response Format
    GeoJSON FeatureCollection with Point features for each spotter.

    ## Optional Filters
    - Bounding box: min_lat, max_lat, min_lon, max_lon
    """
    since = datetime.utcnow() - timedelta(minutes=15)

    # Get most recent location per user (public only)
    subquery = (
        select(Location.user_id, func.max(Location.timestamp).label("max_timestamp"))
        .where(Location.timestamp >= since, Location.visibility == "public")
        .group_by(Location.user_id)
        .subquery()
    )

    query = select(Location).join(
        subquery,
        and_(
            Location.user_id == subquery.c.user_id,
            Location.timestamp == subquery.c.max_timestamp,
        ),
    )

    # Apply bounding box filter
    if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
        query = query.where(
            and_(
                Location.latitude >= min_lat,
                Location.latitude <= max_lat,
                Location.longitude >= min_lon,
                Location.longitude <= max_lon,
            )
        )

    result = await db.execute(query)
    locations = result.scalars().all()

    # Build GeoJSON
    features = []
    for loc in locations:
        await db.refresh(loc, ["user"])
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [loc.longitude, loc.latitude],
            },
            "properties": {
                "callsign": loc.user.callsign if loc.user else None,
                "role": loc.user.role.value if loc.user else None,
                "heading": loc.heading,
                "speed": loc.speed,
                "timestamp": loc.timestamp.isoformat(),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "count": len(features),
            "generated_at": datetime.utcnow().isoformat(),
            "api_version": "1.0",
        },
    }


@router.get("/reports")
async def get_reports(
    type: Optional[ReportType] = None,
    verified: Optional[bool] = None,
    hours: int = Query(24, ge=1, le=168),
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    limit: int = Query(100, ge=1, le=500),
    api_key: Optional[str] = Depends(validate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get weather reports as GeoJSON.

    ## Response Format
    GeoJSON FeatureCollection with Point features for each report.

    ## Filters
    - type: Filter by report type (tornado, hail, flooding, etc.)
    - verified: Filter by verification status
    - hours: Time window (1-168 hours, default 24)
    - Bounding box: min_lat, max_lat, min_lon, max_lon
    - limit: Maximum results (1-500, default 100)
    """
    since = datetime.utcnow() - timedelta(hours=hours)

    query = select(Report).where(
        Report.is_deleted == False,
        Report.created_at >= since,
    )

    if type:
        query = query.where(Report.type == type)

    if verified is not None:
        query = query.where(Report.is_verified == verified)

    if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
        query = query.where(
            and_(
                Report.latitude >= min_lat,
                Report.latitude <= max_lat,
                Report.longitude >= min_lon,
                Report.longitude <= max_lon,
            )
        )

    query = query.order_by(Report.created_at.desc()).limit(limit)
    result = await db.execute(query)
    reports = result.scalars().all()

    features = []
    for report in reports:
        await db.refresh(report, ["user"])
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [report.longitude, report.latitude],
            },
            "properties": {
                "id": str(report.id),
                "type": report.type.value,
                "title": report.title,
                "description": report.description,
                "severity": report.severity,
                "hail_size": report.hail_size,
                "wind_speed": report.wind_speed,
                "tornado_rating": report.tornado_rating,
                "is_verified": report.is_verified,
                "reporter_callsign": report.user.callsign if report.user else None,
                "event_time": report.event_time.isoformat() if report.event_time else None,
                "created_at": report.created_at.isoformat(),
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
        "metadata": {
            "count": len(features),
            "time_window_hours": hours,
            "generated_at": datetime.utcnow().isoformat(),
            "api_version": "1.0",
        },
    }


@router.get("/reports/{report_id}")
async def get_report(
    report_id: UUID,
    api_key: Optional[str] = Depends(validate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get a single report by ID.

    Returns detailed information about a specific weather report.
    """
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.is_deleted == False)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await db.refresh(report, ["user", "verified_by"])

    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [report.longitude, report.latitude],
        },
        "properties": {
            "id": str(report.id),
            "type": report.type.value,
            "title": report.title,
            "description": report.description,
            "location_description": report.location_description,
            "severity": report.severity,
            "hail_size": report.hail_size,
            "wind_speed": report.wind_speed,
            "tornado_rating": report.tornado_rating,
            "media_urls": report.media_urls,
            "is_verified": report.is_verified,
            "verified_at": report.verified_at.isoformat() if report.verified_at else None,
            "verification_notes": report.verification_notes,
            "reporter": {
                "callsign": report.user.callsign if report.user else None,
                "role": report.user.role.value if report.user else None,
            },
            "event_time": report.event_time.isoformat() if report.event_time else None,
            "created_at": report.created_at.isoformat(),
            "updated_at": report.updated_at.isoformat(),
        },
    }


@router.get("/report-types")
async def get_report_types():
    """
    Get list of available report types.

    Useful for building UI dropdowns or validating input.
    """
    return {
        "types": [
            {"value": t.value, "label": t.value.replace("_", " ").title()}
            for t in ReportType
        ]
    }


@router.get("/stats")
async def get_stats(
    hours: int = Query(24, ge=1, le=168),
    api_key: Optional[str] = Depends(validate_api_key),
    db: AsyncSession = Depends(get_db),
):
    """
    Get aggregate statistics.

    Returns counts of active spotters and reports by type.
    """
    since = datetime.utcnow() - timedelta(hours=hours)
    spotter_since = datetime.utcnow() - timedelta(minutes=15)

    # Count active spotters
    spotter_query = (
        select(func.count(func.distinct(Location.user_id)))
        .where(Location.timestamp >= spotter_since, Location.visibility == "public")
    )
    spotter_result = await db.execute(spotter_query)
    active_spotters = spotter_result.scalar()

    # Count reports by type
    report_query = (
        select(Report.type, func.count(Report.id))
        .where(Report.is_deleted == False, Report.created_at >= since)
        .group_by(Report.type)
    )
    report_result = await db.execute(report_query)
    reports_by_type = {row[0].value: row[1] for row in report_result}

    # Count verified vs unverified
    verified_query = (
        select(func.count(Report.id))
        .where(Report.is_deleted == False, Report.created_at >= since, Report.is_verified == True)
    )
    verified_result = await db.execute(verified_query)
    verified_count = verified_result.scalar()

    total_reports = sum(reports_by_type.values())

    return {
        "time_window_hours": hours,
        "active_spotters": active_spotters,
        "total_reports": total_reports,
        "verified_reports": verified_count,
        "reports_by_type": reports_by_type,
        "generated_at": datetime.utcnow().isoformat(),
    }
