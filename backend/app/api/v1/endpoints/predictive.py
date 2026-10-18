import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.models.enums import (
    UserRole,
    RiskStatus,
    RiskSeverity,
)
from app.schemas.predictive import (
    PredictiveOverviewResponse,
    TimeToHireForecastResponse,
    HiringDemandForecastResponse,
    BottleneckAnalysisResponse,
    RecruitmentRiskRead,
    RecruitmentRiskUpdate,
    RecruiterCapacityResponse,
    ModelVersionRead,
    RefreshPredictiveResponse,
)
from app.services.predictive_service import PredictiveService

router = APIRouter()


def require_owner_or_admin(user: User):
    if user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires OWNER or ADMIN role.",
        )


def require_recruiter_or_above(user: User):
    if user.role not in [UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires at least RECRUITER permissions.",
        )


@router.get("/overview", response_model=PredictiveOverviewResponse)
def get_predictive_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get executive predictive recruitment intelligence overview, key metric indicators,
    and high-priority risk warnings.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_overview()


@router.get("/time-to-hire", response_model=TimeToHireForecastResponse)
def get_time_to_hire_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get agency-level, department-level, and requisition-specific time-to-hire forecasts
    with confidence bounds.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_time_to_hire()


@router.get("/demand", response_model=HiringDemandForecastResponse)
def get_hiring_demand_forecast(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get 30, 60, and 90-day hiring demand and expected application inflow forecasts.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_demand()


@router.get("/bottlenecks", response_model=BottleneckAnalysisResponse)
def get_bottleneck_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Analyze stage cycle times, detect stagnation bottlenecks, and examine interview scheduling delays.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_bottlenecks()


@router.get("/risks", response_model=List[RecruitmentRiskRead])
def list_recruitment_risks(
    status: Optional[RiskStatus] = None,
    severity: Optional[RiskSeverity] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Query detected recruitment risks with optional status and severity filtering.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_risks(status_filter=status, severity_filter=severity)


@router.patch("/risks/{risk_id}", response_model=RecruitmentRiskRead)
def update_recruitment_risk(
    risk_id: uuid.UUID,
    payload: RecruitmentRiskUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update a risk status (ACKNOWLEDGE, MITIGATE, DISMISS) with optional resolution notes.
    """
    require_recruiter_or_above(current_user)
    service = PredictiveService(db, current_user.agency_id)
    return service.update_risk(
        risk_id=risk_id,
        new_status=payload.status,
        resolution_notes=payload.resolution_notes,
        user_id=current_user.id,
    )


@router.get("/capacity", response_model=RecruiterCapacityResponse)
def get_recruiter_capacity_planning(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Examine operational workload across recruiters, active applications, upcoming interviews,
    and advisory load-leveling recommendations.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_capacity()


@router.get("/models", response_model=List[ModelVersionRead])
def get_model_versions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve registered model versions, training sample sizes, and evaluation accuracy metrics.
    """
    service = PredictiveService(db, current_user.agency_id)
    return service.get_models()


@router.post("/refresh", response_model=RefreshPredictiveResponse)
def refresh_predictive_intelligence(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Trigger full recalculation of predictive models, forecasts, risks, and capacity planning.
    Requires OWNER or ADMIN role.
    """
    require_owner_or_admin(current_user)
    service = PredictiveService(db, current_user.agency_id)
    return service.refresh_predictive_intelligence(user_id=current_user.id)
