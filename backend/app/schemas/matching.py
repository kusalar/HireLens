import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict
from app.models.enums import JobMatchRunStatus, MatchStatus, VerificationStatus


class MatchExplanationSchema(BaseModel):
    summary: str = Field(..., description="Concise 2-3 sentence overview of candidate evidence alignment.")
    strengths: List[str] = Field(default_factory=list, description="Key demonstrated requirements with concrete evidence.")
    skill_gaps: List[str] = Field(default_factory=list, description="Requirements with missing or partial evidence.")
    verification_items: List[str] = Field(default_factory=list, description="Points that recruiter should probe or verify.")
    suggested_interview_questions: List[str] = Field(default_factory=list, description="Targeted interview questions grounded in requirements.")


class MatchEvidenceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    match_result_id: uuid.UUID
    job_requirement_id: Optional[uuid.UUID] = None
    criterion_name: str
    criterion_type: str
    expected_requirement: str
    evidence_status: MatchStatus
    candidate_evidence: Optional[str] = None
    source_resume_id: Optional[uuid.UUID] = None
    source_page: Optional[int] = None
    source_excerpt: Optional[str] = None
    semantic_similarity: Optional[float] = None
    score_contribution: float
    explanation: Optional[str] = None
    verification_status: VerificationStatus
    created_at: datetime


class JobMatchResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    job_id: uuid.UUID
    candidate_id: uuid.UUID
    match_run_id: uuid.UUID
    overall_score: float
    required_skills_score: float
    experience_score: float
    preferred_skills_score: float
    project_relevance_score: float
    other_criteria_score: float
    matched_requirements_count: int
    partial_requirements_count: int
    missing_requirements_count: int
    needs_verification_count: int
    explanation: Optional[str] = None
    strengths: Optional[List[str]] = Field(default_factory=list)
    skill_gaps: Optional[List[str]] = Field(default_factory=list)
    verification_items: Optional[List[str]] = Field(default_factory=list)
    suggested_questions: Optional[List[str]] = Field(default_factory=list)
    scoring_version: str
    status: str
    created_at: datetime
    updated_at: datetime
    candidate_name: Optional[str] = None
    candidate_title: Optional[str] = None
    candidate_email: Optional[str] = None
    candidate_location: Optional[str] = None
    job_title: Optional[str] = None
    source_fingerprint: Optional[str] = None
    is_stale: bool = False




class JobMatchRunRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    job_id: uuid.UUID
    initiated_by: Optional[uuid.UUID] = None
    scoring_version: str
    matching_provider: str
    embedding_model: Optional[str] = None
    candidate_count: int
    completed_count: int
    failed_count: int
    status: JobMatchRunStatus
    started_at: datetime
    completed_at: Optional[datetime] = None
    duration_ms: Optional[int] = None
    created_at: datetime


class JobMatchListResponse(BaseModel):
    items: List[JobMatchResultRead]
    total: int
    page: int
    page_size: int
    latest_run: Optional[JobMatchRunRead] = None


class JobMatchResultDetailResponse(BaseModel):
    result: JobMatchResultRead
    evidences: List[MatchEvidenceRead]
    run: Optional[JobMatchRunRead] = None
    source_resumes: List[Dict[str, Any]] = Field(default_factory=list)


class RecalculateMatchRequest(BaseModel):
    scoring_version: Optional[str] = "v1.0"
