import uuid
from enum import Enum
from datetime import datetime, date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.enums import ExpenseCategory, PipelineStageType


class PeriodPreset(str, Enum):
    TODAY = "TODAY"
    LAST_7_DAYS = "LAST_7_DAYS"
    LAST_30_DAYS = "LAST_30_DAYS"
    LAST_90_DAYS = "LAST_90_DAYS"
    THIS_MONTH = "THIS_MONTH"
    PREVIOUS_MONTH = "PREVIOUS_MONTH"
    THIS_QUARTER = "THIS_QUARTER"
    CUSTOM = "CUSTOM"


class ReportingPeriodInfo(BaseModel):
    preset: PeriodPreset
    start_date: datetime
    end_date: datetime
    start_date_ist: str
    end_date_ist: str
    timezone: str = "Asia/Kolkata"


# --- Overview ---

class AnalyticsOverviewResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    total_active_jobs: int
    total_candidates: int
    total_applications: int
    applications_in_period: int
    interviews_scheduled: int
    interviews_completed: int
    active_applications: int
    successful_hires: int
    metric_tooltips: Dict[str, str] = Field(default_factory=dict)


# --- Funnel ---

class FunnelStageItem(BaseModel):
    stage: str
    label: str
    current_count: int
    entered_count: int
    drop_off_count: int
    conversion_from_previous_percent: Optional[float] = None
    conversion_from_applied_percent: Optional[float] = None


class RecruitmentFunnelResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    stages: List[FunnelStageItem]
    overall_application_to_hire_rate: float
    total_applications_evaluated: int
    funnel_methodology: str


# --- Hiring Performance ---

class TimeToHireStats(BaseModel):
    average_days: Optional[float] = None
    median_days: Optional[float] = None
    min_days: Optional[float] = None
    max_days: Optional[float] = None
    hired_sample_size: int = 0
    calculation_notes: str


class InterviewConversionStats(BaseModel):
    total_applications_considered: int
    total_interviews_conducted: int
    interviews_per_application: float
    applications_with_interviews: int
    interview_to_hire_count: int
    interview_to_hire_rate: float
    cancelled_interviews_excluded: int


class HiringPerformanceResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    time_to_hire: TimeToHireStats
    interview_conversion: InterviewConversionStats


# --- Job Analytics ---

class JobPerformanceItem(BaseModel):
    job_id: uuid.UUID
    job_title: str
    department: Optional[str] = None
    status: str
    applications_count: int
    interviews_count: int
    hires_count: int
    conversion_rate: float
    created_at: datetime


class JobAnalyticsResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    total_jobs_evaluated: int
    jobs_with_zero_applications: int
    jobs: List[JobPerformanceItem]


# --- Recruiter Analytics ---

class RecruiterPerformanceItem(BaseModel):
    recruiter_id: uuid.UUID
    recruiter_name: str
    recruiter_email: str
    role: str
    applications_handled: int
    active_workload: int
    interviews_coordinated: int
    attributable_hires: int
    avg_time_to_hire_days: Optional[float] = None


class RecruiterAnalyticsResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    recruiters: List[RecruiterPerformanceItem]
    attribution_rule: str


# --- Source Analytics ---

class SourcePerformanceItem(BaseModel):
    source: str
    candidates_count: int
    applications_count: int
    interviews_count: int
    hires_count: int
    conversion_rate: float


class SourceAnalyticsResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    sources: List[SourcePerformanceItem]
    unattributed_candidates_count: int
    unattributed_applications_count: int
    attribution_notes: str


# --- Cost Analytics & Expenses ---

class ExpenseCategoryItem(BaseModel):
    category: str
    amount: float
    currency: str
    percentage: float


class CostAnalyticsResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    has_cost_data: bool
    status_message: str
    cost_per_hire_by_currency: Dict[str, Optional[float]]
    total_expenses_by_currency: Dict[str, float]
    expenses_by_category: List[ExpenseCategoryItem]
    total_attributable_hires: int
    currency_notes: str


class RecruitmentExpenseBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    amount: float = Field(..., gt=0)
    currency: str = Field("INR", min_length=3, max_length=3)
    category: ExpenseCategory = ExpenseCategory.OTHER
    expense_date: datetime
    job_id: Optional[uuid.UUID] = None
    description: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: str) -> str:
        clean = v.strip().upper()
        if len(clean) != 3 or not clean.isalpha():
            raise ValueError("Currency must be an ISO 4217 3-letter code (e.g. INR, USD, EUR)")
        return clean


class RecruitmentExpenseCreate(RecruitmentExpenseBase):
    pass


class RecruitmentExpenseUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    amount: Optional[float] = Field(None, gt=0)
    currency: Optional[str] = Field(None, min_length=3, max_length=3)
    category: Optional[ExpenseCategory] = None
    expense_date: Optional[datetime] = None
    job_id: Optional[uuid.UUID] = None
    description: Optional[str] = None

    @field_validator("currency")
    @classmethod
    def validate_currency(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        clean = v.strip().upper()
        if len(clean) != 3 or not clean.isalpha():
            raise ValueError("Currency must be an ISO 4217 3-letter code (e.g. INR, USD, EUR)")
        return clean


class RecruitmentExpenseRead(RecruitmentExpenseBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    job_title: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    creator_name: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class ExpenseListResponse(BaseModel):
    items: List[RecruitmentExpenseRead]
    total: int
    skip: int
    limit: int


# --- Trends ---

class TrendPoint(BaseModel):
    date: str
    applications: int
    interviews_scheduled: int
    interviews_completed: int
    hires: int


class AnalyticsTrendsResponse(BaseModel):
    reporting_period: ReportingPeriodInfo
    data_points: List[TrendPoint]


# --- AI Insights ---

class AIInsightsRequest(BaseModel):
    focus_area: Optional[str] = Field(None, description="Optional focus area e.g. 'funnel_dropoff', 'cost_efficiency', 'recruiter_workload'")


class AIInsightsResponse(BaseModel):
    generated_at: datetime
    summary: str
    key_findings: List[str]
    bottlenecks: List[str]
    operational_recommendations: List[str]
    provider_used: str
    is_ai_available: bool
    grounding_disclaimer: str
