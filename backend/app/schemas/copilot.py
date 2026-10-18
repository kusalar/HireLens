import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, ConfigDict, Field
from app.models.enums import (
    CopilotActionType,
    CopilotMessageRole,
    CopilotContextType,
)


class CopilotSourceRef(BaseModel):
    type: str  # "job", "candidate", "interview", "application", "analytics"
    id: Optional[str] = None
    label: str
    details: Optional[str] = None


class CopilotMessageCreate(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    context_type: Optional[CopilotContextType] = None
    context_id: Optional[uuid.UUID] = None


class CopilotMessageRead(BaseModel):
    id: uuid.UUID
    conversation_id: uuid.UUID
    role: CopilotMessageRole
    content: str
    sources: Optional[List[CopilotSourceRef]] = None
    context_snapshot: Optional[str] = None
    model_used: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CopilotConversationCreate(BaseModel):
    title: Optional[str] = "New Recruitment Conversation"
    context_type: CopilotContextType = CopilotContextType.AGENCY_OVERVIEW
    context_id: Optional[uuid.UUID] = None


class CopilotConversationRead(BaseModel):
    id: uuid.UUID
    agency_id: uuid.UUID
    user_id: uuid.UUID
    title: str
    context_type: CopilotContextType
    context_id: Optional[uuid.UUID]
    is_archived: bool
    created_at: datetime
    updated_at: datetime
    message_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class CopilotConversationDetail(CopilotConversationRead):
    messages: List[CopilotMessageRead] = []


# -------------------------------------------------------------------
# Job Description Assistant Schemas
# -------------------------------------------------------------------

class JobDescriptionGenerateRequest(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    department: Optional[str] = None
    seniority_level: Optional[str] = "Mid-Level"
    required_skills: List[str] = Field(..., min_length=1)
    preferred_skills: Optional[List[str]] = []
    experience_min: int = Field(0, ge=0)
    experience_max: Optional[int] = Field(None, ge=0)
    location: Optional[str] = None
    work_mode: str = "ONSITE"  # ONSITE, HYBRID, REMOTE
    employment_type: str = "FULL_TIME"
    responsibilities: Optional[List[str]] = []
    additional_context: Optional[str] = None


class JobDescriptionGenerateResponse(BaseModel):
    title: str
    department: Optional[str] = None
    overview: str
    responsibilities: List[str]
    required_qualifications: List[str]
    preferred_qualifications: List[str]
    skills: List[str]
    experience_expectations: str
    work_arrangement: str
    full_text: str
    is_draft: bool = True
    disclaimer: str = "Advisory AI draft. Must be reviewed, edited, and approved manually by an authorized recruiter."
    provider_used: str


class JobDescriptionImproveRequest(BaseModel):
    title: Optional[str] = None
    existing_description: str = Field(..., min_length=10, max_length=25000)
    focus_areas: Optional[List[str]] = []  # "clarity", "inclusivity", "skills", "grammar"


class JobDescriptionImproveResponse(BaseModel):
    improved_description: str
    changes_made: List[str]
    bias_findings: List[str]
    unrealistic_requirements_removed: List[str]
    is_draft: bool = True
    provider_used: str


class JobDescriptionQualityDimension(BaseModel):
    dimension: str  # "Clarity", "Completeness", "Skill Specificity", "Consistency", "Inclusivity"
    score: int  # 0 to 100
    status: str  # "EXCELLENT", "GOOD", "NEEDS_IMPROVEMENT"
    findings: List[str]
    suggestions: List[str]


class JobDescriptionQualityReport(BaseModel):
    job_id: Optional[uuid.UUID] = None
    overall_score: int  # 0 to 100
    dimensions: List[JobDescriptionQualityDimension]
    detected_biases: List[str]
    recommendations: List[str]


# -------------------------------------------------------------------
# Candidate Comparison Schemas
# -------------------------------------------------------------------

class CandidateComparisonRequest(BaseModel):
    job_id: uuid.UUID
    candidate_ids: List[uuid.UUID] = Field(..., min_length=2, max_length=6)


class CandidateComparisonItem(BaseModel):
    candidate_id: uuid.UUID
    candidate_name: str
    current_title: Optional[str] = None
    total_experience_months: int
    deterministic_match_score: Optional[float] = None
    demonstrated_skills: List[str]
    missing_or_partial_skills: List[str]
    verified_education: Optional[str] = None
    key_strengths: List[str]
    areas_for_verification: List[str]
    interview_readiness: str


class CandidateComparisonResponse(BaseModel):
    job_id: uuid.UUID
    job_title: str
    candidate_count: int
    candidates: List[CandidateComparisonItem]
    comparative_summary: str
    methodology_disclaimer: str = (
        "Deterministic scores originate from the Phase 4 matching engine and are never altered. "
        "AI provides grounded qualitative comparisons and does not make autonomous hiring decisions."
    )


# -------------------------------------------------------------------
# Interview Preparation Schemas
# -------------------------------------------------------------------

class InterviewPrepRequest(BaseModel):
    focus_skills: Optional[List[str]] = None


class InterviewPrepQuestion(BaseModel):
    category: str  # "TECHNICAL", "BEHAVIORAL", "SITUATIONAL", "ROLE_SPECIFIC"
    question: str
    target_skill_or_competency: str
    what_to_look_for: str


class InterviewPrepResponse(BaseModel):
    interview_id: uuid.UUID
    candidate_name: str
    job_title: str
    round_name: str
    round_type: str
    scheduled_time: str
    candidate_experience_summary: str
    skills_to_explore: List[str]
    questions: List[InterviewPrepQuestion]
    areas_requiring_clarification: List[str]
    suggested_structure: List[str]
    evaluation_guidance: List[str]
    disclaimer: str = (
        "Advisory preparation brief. Interviewers remain solely responsible for conducting the interview, "
        "evaluating candidates, and recording official feedback."
    )


# -------------------------------------------------------------------
# Recruitment Analytics Intelligence Schemas
# -------------------------------------------------------------------

class AnalyticsExplainRequest(BaseModel):
    preset: Optional[str] = "LAST_30_DAYS"
    focus_area: Optional[str] = "OVERALL"  # "FUNNEL", "CONVERSION", "SOURCING", "COST", "OVERALL"


class AnalyticsExplainResponse(BaseModel):
    reporting_period: Dict[str, Any]
    summary: str
    funnel_insights: List[str]
    time_to_hire_insights: List[str]
    sourcing_insights: List[str]
    operational_recommendations: List[str]
    verified_metrics_snapshot: Dict[str, Any]
    provider_used: str


# -------------------------------------------------------------------
# Copilot Audit Log Schemas
# -------------------------------------------------------------------

class CopilotAuditLogRead(BaseModel):
    id: uuid.UUID
    action_type: CopilotActionType
    target_entity_type: Optional[str]
    target_entity_id: Optional[uuid.UUID]
    provider_used: Optional[str]
    status: str
    duration_ms: Optional[int]
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
