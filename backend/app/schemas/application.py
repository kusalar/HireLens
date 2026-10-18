import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import PipelineStageType
from app.schemas.job import JobRead
from app.schemas.candidate import CandidateRead
from app.schemas.matching import JobMatchResultRead, MatchEvidenceRead


class ApplicationCreate(BaseModel):
    candidate_id: uuid.UUID
    status: Optional[PipelineStageType] = PipelineStageType.APPLIED
    source: Optional[str] = "RECRUITER_SOURCED"
    assigned_recruiter_id: Optional[uuid.UUID] = None
    recruiter_summary: Optional[str] = None
    initial_note: Optional[str] = None


class ApplicationUpdate(BaseModel):
    assigned_recruiter_id: Optional[uuid.UUID] = None
    unassign_recruiter: Optional[bool] = False
    recruiter_summary: Optional[str] = None
    source: Optional[str] = None
    archived: Optional[bool] = None


class ApplicationStageTransition(BaseModel):
    new_stage: PipelineStageType
    reason: Optional[str] = None


class ApplicationStageHistoryRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    previous_stage: Optional[PipelineStageType] = None
    new_stage: PipelineStageType
    changed_by: Optional[uuid.UUID] = None
    changed_by_name: Optional[str] = None
    reason: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationNoteCreate(BaseModel):
    content: str = Field(..., min_length=1)


class ApplicationNoteUpdate(BaseModel):
    content: str = Field(..., min_length=1)


class ApplicationNoteRead(BaseModel):
    id: uuid.UUID
    application_id: uuid.UUID
    author_id: Optional[uuid.UUID] = None
    author_name: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationActivityRead(BaseModel):
    id: uuid.UUID
    action: str
    user_id: Optional[uuid.UUID] = None
    user_name: Optional[str] = None
    details: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ApplicationRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    status: PipelineStageType
    source: Optional[str] = None
    applied_at: datetime
    shortlisted_at: Optional[datetime] = None
    last_activity_at: datetime
    assigned_recruiter_id: Optional[uuid.UUID] = None
    assigned_recruiter_name: Optional[str] = None
    recruiter_summary: Optional[str] = None
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Denormalized / resolved for list and Kanban display
    candidate_name: Optional[str] = None
    candidate_title: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_location: Optional[str] = None
    total_experience_months: Optional[int] = 0
    job_title: Optional[str] = None
    latest_match_score: Optional[float] = None
    is_stale_match: Optional[bool] = False

    model_config = ConfigDict(from_attributes=True)


class ApplicationListResponse(BaseModel):
    items: List[ApplicationRead]
    total: int
    stage_counts: Dict[str, int]


class ApplicationDetailRead(BaseModel):
    application: ApplicationRead
    candidate: CandidateRead
    job: JobRead
    stage_history: List[ApplicationStageHistoryRead]
    notes: List[ApplicationNoteRead]
    activity: List[ApplicationActivityRead]
    latest_match_result: Optional[JobMatchResultRead] = None
    match_evidences: Optional[List[MatchEvidenceRead]] = None

    model_config = ConfigDict(from_attributes=True)


class CandidateComparisonItem(BaseModel):
    candidate_id: uuid.UUID
    candidate_name: str
    current_title: Optional[str] = None
    total_experience_months: int = 0
    application_id: Optional[uuid.UUID] = None
    application_status: Optional[PipelineStageType] = None
    overall_score: Optional[float] = None
    required_skills_score: Optional[float] = None
    experience_score: Optional[float] = None
    preferred_skills_score: Optional[float] = None
    project_relevance_score: Optional[float] = None
    other_criteria_score: Optional[float] = None
    matched_requirements_count: int = 0
    partial_requirements_count: int = 0
    missing_requirements_count: int = 0
    needs_verification_count: int = 0
    strengths: List[str] = Field(default_factory=list)
    skill_gaps: List[str] = Field(default_factory=list)
    verification_items: List[str] = Field(default_factory=list)
    is_stale: bool = False
    scoring_version: Optional[str] = None
    evaluated_at: Optional[datetime] = None


class CandidateComparisonResponse(BaseModel):
    job_id: uuid.UUID
    job_title: str
    candidates: List[CandidateComparisonItem]
    criteria_matrix: List[Dict[str, Any]] = Field(default_factory=list)


class PipelineDashboardStats(BaseModel):
    total_active_applications: int
    stage_counts: Dict[str, int]
    recent_activities: List[Dict[str, Any]]
    job_summaries: List[Dict[str, Any]]
