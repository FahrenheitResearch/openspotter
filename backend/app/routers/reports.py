from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
import os
import uuid as uuid_lib
import aiofiles
import httpx

from fastapi import APIRouter, Depends, HTTPException, status, Query, UploadFile, File, Form, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.database import get_db
from app.models.user import User
from app.models.report import Report, ReportType
from app.schemas.report import (
    ReportCreate,
    ReportUpdate,
    ReportVerify,
    ReportResponse,
    ReportListResponse,
    ReportGeoJSONResponse,
    ReporterInfo,
)
from app.utils.deps import get_current_user, require_coordinator
from app.config import get_settings
from app.services.wfo_twitter import format_report_tweet, get_wfo_mention

settings = get_settings()
router = APIRouter()


async def get_wfo_for_location(lat: float, lon: float) -> Optional[str]:
    """Get WFO code for a given lat/lon from NWS API."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"https://api.weather.gov/points/{lat},{lon}",
                headers={"User-Agent": "OpenSpotter/1.0"},
                timeout=5.0,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("properties", {}).get("cwa")
    except Exception as e:
        print(f"Failed to get WFO for location: {e}")
    return None


async def post_to_twitter(
    report: Report,
    wfo_code: Optional[str],
    media_urls: list[str],
):
    """Background task to post report to Twitter."""
    # Check if Twitter is configured
    if not settings.twitter_bearer_token:
        print("Twitter not configured - skipping post")
        return

    try:
        # Format tweet text
        tweet_text = format_report_tweet(
            report_type=report.type.value,
            description=report.description or "",
            latitude=report.latitude,
            longitude=report.longitude,
            wfo_code=wfo_code,
            severity=report.severity,
            hail_size=report.hail_size,
            wind_speed=report.wind_speed,
        )

        # Post to Twitter (simplified - full implementation would use OAuth)
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.twitter.com/2/tweets",
                headers={
                    "Authorization": f"Bearer {settings.twitter_bearer_token}",
                    "Content-Type": "application/json",
                },
                json={"text": tweet_text},
                timeout=10.0,
            )
            if response.status_code in [200, 201]:
                print(f"Posted report to Twitter: {response.json()}")
            else:
                print(f"Twitter post failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Twitter post error: {e}")


@router.post("/upload-media")
async def upload_media(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """Upload media file for a report."""
    # Validate file type
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp", "video/mp4", "video/quicktime"]
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(allowed_types)}",
        )

    # Check file size
    content = await file.read()
    if len(content) > settings.max_media_size_mb * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Max size: {settings.max_media_size_mb}MB",
        )

    # Create media directory if needed
    media_dir = settings.media_storage_path
    os.makedirs(media_dir, exist_ok=True)

    # Generate unique filename
    ext = os.path.splitext(file.filename)[1] if file.filename else ".jpg"
    filename = f"{uuid_lib.uuid4()}{ext}"
    filepath = os.path.join(media_dir, filename)

    # Save file
    async with aiofiles.open(filepath, "wb") as f:
        await f.write(content)

    # Return URL (in production, this would be a CDN/S3 URL)
    media_url = f"/media/{filename}"

    return {"url": media_url, "filename": filename, "size": len(content)}


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Submit a new weather report."""
    report = Report(
        user_id=user.id,
        type=data.type,
        title=data.title,
        description=data.description,
        latitude=data.latitude,
        longitude=data.longitude,
        location_description=data.location_description,
        severity=data.severity,
        hail_size=data.hail_size,
        wind_speed=data.wind_speed,
        tornado_rating=data.tornado_rating,
        event_time=data.event_time or datetime.utcnow(),
        media_urls=data.media_urls or [],
    )

    db.add(report)
    await db.flush()
    await db.refresh(report)

    # Get WFO for location and optionally post to Twitter
    if data.post_to_twitter:
        wfo_code = await get_wfo_for_location(data.latitude, data.longitude)
        background_tasks.add_task(
            post_to_twitter,
            report,
            wfo_code,
            data.media_urls or [],
        )

    # Load user relationship for response
    await db.refresh(report, ["user"])

    response = ReportResponse.model_validate(report)
    response.reporter = ReporterInfo(
        id=user.id,
        callsign=user.callsign,
        role=user.role.value,
    )

    return response


@router.get("", response_model=ReportListResponse)
async def list_reports(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    report_type: Optional[ReportType] = None,
    verified_only: bool = False,
    hours: Optional[int] = Query(None, ge=1, le=168),  # Max 7 days
    min_lat: Optional[float] = Query(None, ge=-90, le=90),
    max_lat: Optional[float] = Query(None, ge=-90, le=90),
    min_lon: Optional[float] = Query(None, ge=-180, le=180),
    max_lon: Optional[float] = Query(None, ge=-180, le=180),
    db: AsyncSession = Depends(get_db),
):
    """List weather reports with filters."""
    query = select(Report).where(Report.is_deleted == False)

    if report_type:
        query = query.where(Report.type == report_type)

    if verified_only:
        query = query.where(Report.is_verified == True)

    if hours:
        since = datetime.utcnow() - timedelta(hours=hours)
        query = query.where(Report.created_at >= since)

    # Bounding box filter
    if all(v is not None for v in [min_lat, max_lat, min_lon, max_lon]):
        query = query.where(
            and_(
                Report.latitude >= min_lat,
                Report.latitude <= max_lat,
                Report.longitude >= min_lon,
                Report.longitude <= max_lon,
            )
        )

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()

    # Get paginated results
    query = query.order_by(Report.created_at.desc())
    query = query.offset((page - 1) * per_page).limit(per_page)
    result = await db.execute(query)
    reports = result.scalars().all()

    # Load user relationships
    report_responses = []
    for report in reports:
        await db.refresh(report, ["user"])
        resp = ReportResponse.model_validate(report)
        if report.user:
            resp.reporter = ReporterInfo(
                id=report.user_id,
                callsign=report.user.callsign,
                role=report.user.role.value,
            )
        report_responses.append(resp)

    return ReportListResponse(
        reports=report_responses,
        total=total,
        page=page,
        per_page=per_page,
    )


@router.get("/geojson", response_model=ReportGeoJSONResponse)
async def get_reports_geojson(
    report_type: Optional[ReportType] = None,
    verified_only: bool = False,
    hours: int = Query(24, ge=1, le=168),
    db: AsyncSession = Depends(get_db),
):
    """Get reports as GeoJSON FeatureCollection."""
    since = datetime.utcnow() - timedelta(hours=hours)

    query = select(Report).where(
        Report.is_deleted == False,
        Report.created_at >= since,
    )

    if report_type:
        query = query.where(Report.type == report_type)

    if verified_only:
        query = query.where(Report.is_verified == True)

    query = query.order_by(Report.created_at.desc()).limit(500)
    result = await db.execute(query)
    reports = result.scalars().all()

    features = []
    for report in reports:
        await db.refresh(report, ["user"])
        features.append(report.to_geojson_feature(include_user=True))

    return ReportGeoJSONResponse(
        features=features,
        count=len(features),
    )


@router.get("/{report_id}", response_model=ReportResponse)
async def get_report(
    report_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific report."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.is_deleted == False)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    await db.refresh(report, ["user"])
    response = ReportResponse.model_validate(report)
    if report.user:
        response.reporter = ReporterInfo(
            id=report.user_id,
            callsign=report.user.callsign,
            role=report.user.role.value,
        )

    return response


@router.patch("/{report_id}", response_model=ReportResponse)
async def update_report(
    report_id: UUID,
    data: ReportUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a report (owner or coordinator only)."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.is_deleted == False)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Check ownership or coordinator role
    if report.user_id != user.id and not user.is_coordinator_or_above:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to update this report",
        )

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(report, field, value)

    await db.flush()
    await db.refresh(report, ["user"])

    response = ReportResponse.model_validate(report)
    if report.user:
        response.reporter = ReporterInfo(
            id=report.user_id,
            callsign=report.user.callsign,
            role=report.user.role.value,
        )

    return response


@router.delete("/{report_id}")
async def delete_report(
    report_id: UUID,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a report (owner or coordinator only)."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.is_deleted == False)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    # Check ownership or coordinator role
    if report.user_id != user.id and not user.is_coordinator_or_above:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this report",
        )

    report.is_deleted = True
    report.deleted_at = datetime.utcnow()
    await db.flush()

    return {"message": "Report deleted successfully"}


@router.patch("/{report_id}/verify", response_model=ReportResponse)
async def verify_report(
    report_id: UUID,
    data: ReportVerify,
    coordinator: User = Depends(require_coordinator),
    db: AsyncSession = Depends(get_db),
):
    """Verify or unverify a report (coordinator only)."""
    result = await db.execute(
        select(Report).where(Report.id == report_id, Report.is_deleted == False)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Report not found",
        )

    report.is_verified = data.is_verified
    report.verified_by_id = coordinator.id if data.is_verified else None
    report.verified_at = datetime.utcnow() if data.is_verified else None
    report.verification_notes = data.verification_notes

    await db.flush()
    await db.refresh(report, ["user"])

    response = ReportResponse.model_validate(report)
    if report.user:
        response.reporter = ReporterInfo(
            id=report.user_id,
            callsign=report.user.callsign,
            role=report.user.role.value,
        )

    return response
