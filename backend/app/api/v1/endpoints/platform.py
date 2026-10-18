import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.entities import User
from app.api.deps import require_platform_admin
from app.schemas.agency import AgencyRead
from app.schemas.platform import (
    PlatformOverviewResponse,
    PlatformAgencyListResponse,
    PlatformAgencyDetailResponse,
    PlatformAgencyStatusUpdate,
    PlatformAuditLogListResponse,
    PlatformSystemHealthResponse,
)
from app.services.platform_service import PlatformService

router = APIRouter()


@router.get("/overview", response_model=PlatformOverviewResponse)
def get_platform_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Returns platform-wide KPI telemetry: registered agencies, active users,
    total jobs, candidates, subscription breakdown, MRR/ARR, and gross revenue.
    Strictly restricted to PLATFORM_SUPER_ADMIN.
    """
    service = PlatformService(db)
    return service.get_overview()


@router.get("/agencies", response_model=PlatformAgencyListResponse)
def list_agencies(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="ACTIVE or SUSPENDED"),
    country: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Paginated directory of all registered agencies with live metrics and subscription status.
    """
    service = PlatformService(db)
    return service.list_agencies(
        page=page,
        page_size=page_size,
        search=search,
        status_filter=status,
        country=country,
    )


@router.get("/agencies/{agency_id}", response_model=PlatformAgencyDetailResponse)
def get_agency_detail(
    agency_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Inspect detailed tenant configuration, member roster, subscription entitlements,
    billing profile, and recent invoices for any agency.
    """
    service = PlatformService(db)
    return service.get_agency_detail(agency_id)


@router.patch("/agencies/{agency_id}/status", response_model=AgencyRead)
def update_agency_status(
    agency_id: uuid.UUID,
    data: PlatformAgencyStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Platform Super Admin control: suspend or reactivate an agency tenant.
    All actions are immutably logged to SecurityAuditEvent.
    """
    service = PlatformService(db)
    return service.update_agency_status(
        agency_id=agency_id,
        is_active=data.is_active,
        reason=data.reason,
        admin_user=current_user,
    )


@router.get("/audit-logs", response_model=PlatformAuditLogListResponse)
def list_platform_audit_logs(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    agency_id: Optional[uuid.UUID] = Query(None),
    event_category: Optional[str] = Query(None),
    severity: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Cross-agency security and administrative audit event explorer.
    """
    service = PlatformService(db)
    return service.list_audit_logs(
        page=page,
        page_size=page_size,
        agency_id=agency_id,
        event_category=event_category,
        severity=severity,
        search=search,
    )


@router.get("/health", response_model=PlatformSystemHealthResponse)
def get_system_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_platform_admin),
):
    """
    Deep operational probe inspecting Database query latency, Redis/Celery broker,
    and storage disk availability.
    """
    service = PlatformService(db)
    return service.get_system_health()
