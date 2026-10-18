import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.entities import User
from app.models.enums import UserRole
from app.schemas.copilot import (
    CopilotConversationCreate,
    CopilotConversationRead,
    CopilotConversationDetail,
    CopilotMessageCreate,
    CopilotMessageRead,
    JobDescriptionGenerateRequest,
    JobDescriptionGenerateResponse,
    JobDescriptionImproveRequest,
    JobDescriptionImproveResponse,
    JobDescriptionQualityReport,
    CandidateComparisonRequest,
    CandidateComparisonResponse,
    InterviewPrepRequest,
    InterviewPrepResponse,
    AnalyticsExplainRequest,
    AnalyticsExplainResponse,
)
from app.services.copilot_service import CopilotService

router = APIRouter()


# -------------------------------------------------------------------
# Conversation & Chat Endpoints
# -------------------------------------------------------------------

@router.post("/conversations", response_model=CopilotConversationRead, status_code=status.HTTP_201_CREATED)
def create_conversation(
    data: CopilotConversationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """Creates a new persistent Copilot conversation session."""
    service = CopilotService(db, current_user.agency_id)
    return service.create_conversation(data, current_user)


@router.get("/conversations", response_model=List[CopilotConversationRead])
def list_conversations(
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Lists conversations accessible to the current user within their agency."""
    service = CopilotService(db, current_user.agency_id)
    return service.list_conversations(current_user, limit, offset)


@router.get("/conversations/{conversation_id}", response_model=CopilotConversationDetail)
def get_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves conversation history and message turns."""
    service = CopilotService(db, current_user.agency_id)
    return service.get_conversation(conversation_id, current_user)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_conversation(
    conversation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """Archives/deletes a conversation session."""
    service = CopilotService(db, current_user.agency_id)
    service.delete_conversation(conversation_id, current_user)
    return None


@router.post("/conversations/{conversation_id}/messages", response_model=CopilotMessageRead)
def send_message(
    conversation_id: uuid.UUID,
    data: CopilotMessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """Submits a user query and returns an evidence-grounded AI assistant response."""
    service = CopilotService(db, current_user.agency_id)
    return service.send_message(conversation_id, data, current_user)


# -------------------------------------------------------------------
# Job Description Assistant Endpoints
# -------------------------------------------------------------------

@router.post("/job-descriptions/generate", response_model=JobDescriptionGenerateResponse)
def generate_job_description(
    data: JobDescriptionGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """Generates a structured, inclusive job description draft from role parameters."""
    service = CopilotService(db, current_user.agency_id)
    return service.generate_job_description(data, current_user)


@router.post("/job-descriptions/improve", response_model=JobDescriptionImproveResponse)
def improve_job_description(
    data: JobDescriptionImproveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """Refines existing job descriptions to eliminate biased phrasing and clarify competencies."""
    service = CopilotService(db, current_user.agency_id)
    return service.improve_job_description(data, current_user)


@router.post("/job-descriptions/analyze", response_model=JobDescriptionQualityReport)
def analyze_job_description(
    job_id: Optional[uuid.UUID] = Query(None),
    raw_text: Optional[str] = Body(None, embed=True),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Performs an objective multi-dimensional quality check (clarity, completeness, inclusivity)."""
    service = CopilotService(db, current_user.agency_id)
    return service.analyze_job_description_quality(job_id, raw_text, current_user)


# -------------------------------------------------------------------
# Candidate Comparison Endpoint
# -------------------------------------------------------------------

@router.post("/candidates/compare", response_model=CandidateComparisonResponse)
def compare_candidates(
    data: CandidateComparisonRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """
    Performs evidence-grounded candidate comparison.
    Preserves Phase 4 deterministic match scores as the single source of truth.
    """
    service = CopilotService(db, current_user.agency_id)
    return service.compare_candidates(data, current_user)


# -------------------------------------------------------------------
# Interview Preparation Endpoint
# -------------------------------------------------------------------

@router.post("/interviews/{interview_id}/prepare", response_model=InterviewPrepResponse)
def prepare_interview(
    interview_id: uuid.UUID,
    req: Optional[InterviewPrepRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
):
    """Generates an evidence-grounded interview preparation brief and targeted questions."""
    service = CopilotService(db, current_user.agency_id)
    return service.prepare_interview(interview_id, current_user, req)


# -------------------------------------------------------------------
# Recruitment Analytics Intelligence Endpoint
# -------------------------------------------------------------------

@router.post("/analytics/explain", response_model=AnalyticsExplainResponse)
def explain_analytics(
    req: AnalyticsExplainRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generates natural-language operational explanations grounded in Phase 8 analytics metrics."""
    service = CopilotService(db, current_user.agency_id)
    return service.explain_analytics(req, current_user)
