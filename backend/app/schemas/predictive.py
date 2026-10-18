import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import (
    ModelType,
    PredictionAlgorithm,
    ForecastType,
    ConfidenceLevel,
    RecruitmentRiskType,
    RiskSeverity,
    RiskStatus,
    RecruiterUtilizationStatus,
)


class ModelVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    model_type: ModelType
    algorithm: PredictionAlgorithm
    version_tag: str
    training_sample_size: int
    evaluation_metrics: Optional[Dict[str, Any]] = None
    hyperparameters: Optional[Dict[str, Any]] = None
    feature_names: Optional[List[str]] = None
    is_active: bool
    trained_at: datetime
    created_at: datetime


class ForecastRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    department: Optional[str] = None
    forecast_type: ForecastType
    predicted_value: float
    confidence_lower: float
    confidence_upper: float
    confidence_level: ConfidenceLevel
    is_baseline_fallback: bool
    explanation: Optional[str] = None
    factors: Optional[List[str]] = None
    model_version_id: Optional[uuid.UUID] = None
    horizon_days: int
    forecast_date: datetime
    created_at: datetime


class RecruitmentRiskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    risk_type: RecruitmentRiskType
    severity: RiskSeverity
    status: RiskStatus
    title: str
    description: str
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    recruiter_id: Optional[uuid.UUID] = None
    recruiter_name: Optional[str] = None
    evidence_payload: Optional[Dict[str, Any]] = None
    recommended_action: str
    confidence_score: float
    acknowledged_by_user_id: Optional[uuid.UUID] = None
    resolution_notes: Optional[str] = None
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    created_at: datetime


class RecruitmentRiskUpdate(BaseModel):
    status: Optional[RiskStatus] = None
    resolution_notes: Optional[str] = None


class CapacitySnapshotRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    recruiter_id: uuid.UUID
    recruiter_name: Optional[str] = None
    recruiter_email: Optional[str] = None
    active_applications_count: int
    upcoming_interviews_count: int
    open_requisitions_count: int
    workload_index: float
    utilization_status: RecruiterUtilizationStatus
    recommendations: Optional[List[str]] = None
    snapshot_date: datetime
    created_at: datetime


class PredictiveOverviewResponse(BaseModel):
    active_jobs_count: int
    active_applications_count: int
    average_predicted_time_to_hire_days: float
    demand_next_30d_hires: int
    open_risks_count: int
    critical_risks_count: int
    top_risks: List[RecruitmentRiskRead]
    capacity_summary: Dict[str, Any]
    model_governance: Dict[str, Any]
    ai_strategic_brief: Optional[str] = None
    last_refreshed_at: str
    timezone: str = "Asia/Kolkata"


class DepartmentTimeToHire(BaseModel):
    department: str
    predicted_days: float
    confidence_lower: float
    confidence_upper: float
    sample_size: int
    is_fallback: bool


class TimeToHireForecastResponse(BaseModel):
    overall_agency_predicted_days: float
    historical_average_days: float
    sample_size: int
    is_baseline_fallback: bool
    confidence_interval: Dict[str, float]
    by_department: List[DepartmentTimeToHire]
    by_job: List[ForecastRead]
    explanation: Optional[str] = None


class DepartmentDemand(BaseModel):
    department: str
    demand_30d: int
    demand_60d: int
    demand_90d: int
    expected_applications_30d: int


class HiringDemandForecastResponse(BaseModel):
    demand_30d: int
    demand_60d: int
    demand_90d: int
    expected_application_volume_30d: int
    historical_trend_direction: str
    department_breakdown: List[DepartmentDemand]
    confidence_level: ConfidenceLevel
    historical_vs_predicted_data: List[Dict[str, Any]]
    explanation: Optional[str] = None


class StageCycleTime(BaseModel):
    stage: str
    stage_label: str
    median_duration_days: float
    average_duration_days: float
    p90_duration_days: float
    current_active_candidates: int
    is_bottleneck: bool
    benchmark_days: float


class BottleneckAnalysisResponse(BaseModel):
    stagnant_stages: List[StageCycleTime]
    interview_scheduling_delays: List[Dict[str, Any]]
    recommendations: List[str]
    ai_explanation: Optional[str] = None


class RecruiterCapacityResponse(BaseModel):
    recruiters: List[CapacitySnapshotRead]
    agency_average_workload: float
    imbalance_detected: bool
    redistribution_recommendations: List[str]


class RefreshPredictiveResponse(BaseModel):
    status: str
    forecasts_generated: int
    risks_detected: int
    capacity_snapshots_updated: int
    timestamp: str
