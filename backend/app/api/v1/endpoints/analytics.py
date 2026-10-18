import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.entities import User
from app.models.enums import UserRole, ExpenseCategory
from app.services.analytics_service import AnalyticsService
from app.services.analytics_ai_service import AnalyticsAIService
from app.schemas.analytics import (
    PeriodPreset,
    AnalyticsOverviewResponse,
    RecruitmentFunnelResponse,
    HiringPerformanceResponse,
    JobAnalyticsResponse,
    RecruiterAnalyticsResponse,
    SourceAnalyticsResponse,
    CostAnalyticsResponse,
    AnalyticsTrendsResponse,
    RecruitmentExpenseCreate,
    RecruitmentExpenseUpdate,
    RecruitmentExpenseRead,
    ExpenseListResponse,
    AIInsightsRequest,
    AIInsightsResponse,
)

router = APIRouter()


# ----------------------------------------------------------------------
# 1. Overview Metrics
# ----------------------------------------------------------------------
@router.get("/overview", response_model=AnalyticsOverviewResponse)
def get_analytics_overview(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS, description="Preset period"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD for CUSTOM period"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD for CUSTOM period"),
    job_id: Optional[uuid.UUID] = Query(None, description="Optional job filter"),
    recruiter_id: Optional[uuid.UUID] = Query(None, description="Optional recruiter filter"),
    source: Optional[str] = Query(None, description="Optional candidate source filter"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_overview(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
        recruiter_id=recruiter_id,
        source=source,
    )


# ----------------------------------------------------------------------
# 2. Recruitment Funnel
# ----------------------------------------------------------------------
@router.get("/funnel", response_model=RecruitmentFunnelResponse)
def get_recruitment_funnel(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    recruiter_id: Optional[uuid.UUID] = Query(None),
    source: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_funnel(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
        recruiter_id=recruiter_id,
        source=source,
    )


# ----------------------------------------------------------------------
# 3. Trends Time-Series
# ----------------------------------------------------------------------
@router.get("/trends", response_model=AnalyticsTrendsResponse)
def get_analytics_trends(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    recruiter_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_trends(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
        recruiter_id=recruiter_id,
    )


# ----------------------------------------------------------------------
# 4. Job Performance Analytics
# ----------------------------------------------------------------------
@router.get("/jobs", response_model=JobAnalyticsResponse)
def get_job_analytics(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    department: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_job_performance(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        department=department,
    )


# ----------------------------------------------------------------------
# 5. Recruiter Performance Analytics
# ----------------------------------------------------------------------
@router.get("/recruiters", response_model=RecruiterAnalyticsResponse)
def get_recruiter_analytics(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_recruiter_performance(
        preset=period,
        start_date=start_date,
        end_date=end_date,
    )


# ----------------------------------------------------------------------
# 6. Candidate Source Analytics
# ----------------------------------------------------------------------
@router.get("/sources", response_model=SourceAnalyticsResponse)
def get_source_analytics(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_source_performance(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
    )


# ----------------------------------------------------------------------
# 7. Hiring Performance & Time-To-Hire
# ----------------------------------------------------------------------
@router.get("/hiring-performance", response_model=HiringPerformanceResponse)
def get_hiring_performance(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    recruiter_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_hiring_performance(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
        recruiter_id=recruiter_id,
    )


# ----------------------------------------------------------------------
# 8. Cost Analytics & Cost-Per-Hire
# ----------------------------------------------------------------------
@router.get("/costs", response_model=CostAnalyticsResponse)
def get_cost_analytics(
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_cost_analytics(
        preset=period,
        start_date=start_date,
        end_date=end_date,
        job_id=job_id,
    )


# ----------------------------------------------------------------------
# 9. AI-Assisted Operational Insights
# ----------------------------------------------------------------------
@router.post("/insights", response_model=AIInsightsResponse)
def generate_recruitment_insights(
    payload: Optional[AIInsightsRequest] = None,
    period: PeriodPreset = Query(PeriodPreset.LAST_30_DAYS),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    overview = service.get_overview(preset=period, start_date=start_date, end_date=end_date, job_id=job_id)
    funnel = service.get_funnel(preset=period, start_date=start_date, end_date=end_date, job_id=job_id)
    hiring = service.get_hiring_performance(preset=period, start_date=start_date, end_date=end_date, job_id=job_id)
    jobs = service.get_job_performance(preset=period, start_date=start_date, end_date=end_date)
    sources = service.get_source_performance(preset=period, start_date=start_date, end_date=end_date, job_id=job_id)
    costs = service.get_cost_analytics(preset=period, start_date=start_date, end_date=end_date, job_id=job_id)

    analytics_bundle = {
        "reporting_period": overview.reporting_period.model_dump(),
        "overview": overview.model_dump(),
        "funnel": funnel.model_dump(),
        "hiring_performance": hiring.model_dump(),
        "jobs": jobs.model_dump(),
        "sources": sources.model_dump(),
        "costs": costs.model_dump(),
    }

    ai_service = AnalyticsAIService()
    return ai_service.generate_grounded_insights(analytics_bundle, payload)


# ----------------------------------------------------------------------
# 10. Recruitment Expenses CRUD (OWNER / ADMIN)
# ----------------------------------------------------------------------
@router.get("/expenses", response_model=ExpenseListResponse)
def list_recruitment_expenses(
    job_id: Optional[uuid.UUID] = Query(None),
    category: Optional[ExpenseCategory] = Query(None),
    currency: Optional[str] = Query(None),
    start_date: Optional[str] = Query(None),
    end_date: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.list_expenses(
        job_id=job_id,
        category=category,
        currency=currency,
        start_date=start_date,
        end_date=end_date,
        skip=skip,
        limit=limit,
    )


@router.post(
    "/expenses",
    response_model=RecruitmentExpenseRead,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN))],
)
def create_recruitment_expense(
    data: RecruitmentExpenseCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.create_expense(current_user, data)


@router.get("/expenses/{expense_id}", response_model=RecruitmentExpenseRead)
def get_recruitment_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.get_expense_by_id(expense_id)


@router.patch(
    "/expenses/{expense_id}",
    response_model=RecruitmentExpenseRead,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN))],
)
def update_recruitment_expense(
    expense_id: uuid.UUID,
    data: RecruitmentExpenseUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    return service.update_expense(current_user, expense_id, data)


@router.delete(
    "/expenses/{expense_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_roles(UserRole.OWNER, UserRole.ADMIN))],
)
def delete_recruitment_expense(
    expense_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = AnalyticsService(db, current_user.agency_id)
    service.delete_expense(current_user, expense_id)
    return None
