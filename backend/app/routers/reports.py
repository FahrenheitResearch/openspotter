from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
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

router = APIRouter()


@router.post("", response_model=ReportResponse, status_code=status.HTTP_201_CREATED)
async def create_report(
    data: ReportCreate,
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
    )

    db.add(report)
    await db.flush()
    await db.refresh(report)

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
