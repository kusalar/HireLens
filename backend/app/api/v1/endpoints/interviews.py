import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import (
    UserRole,
    InterviewStatus,
    InterviewMode,
    InterviewRoundType,
)
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    InterviewReschedule,
    InterviewCancel,
    InterviewComplete,
    InterviewRead,
    InterviewDetailRead,
    InterviewListResponse,
    InterviewFeedbackCreate,
    InterviewFeedbackUpdate,
    InterviewFeedbackRead,
    InterviewHistoryRead,
)
from app.services.interview_service import InterviewService
from app.api.deps import get_current_user, require_roles

# Main router mounted at /interviews
router = APIRouter()

# Router mounted at /applications for application-scoped interview routes
app_interview_router = APIRouter()

# Router mounted at /recruiters for recruiter-scoped interview routes
recruiter_interview_router = APIRouter()


# -------------------------------------------------------------
# /applications/{application_id}/interviews endpoints
# -------------------------------------------------------------

@app_interview_router.post(
    "/{application_id}/interviews",
    response_model=InterviewRead,
    status_code=status.HTTP_201_CREATED,
)
def create_application_interview(
    application_id: uuid.UUID,
    data: InterviewCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Schedule a new interview round for an application."""
    service = InterviewService(db, current_user.agency_id)
    return service.create_interview(application_id, current_user, data)


@app_interview_router.get(
    "/{application_id}/interviews",
    response_model=List[InterviewRead],
)
def list_application_interviews(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all interview rounds associated with an application."""
    service = InterviewService(db, current_user.agency_id)
    return service.list_application_interviews(application_id, current_user=current_user)


# -------------------------------------------------------------
# /interviews workspace endpoints
# -------------------------------------------------------------

@router.get("", response_model=InterviewListResponse)
def list_interviews(
    application_id: Optional[uuid.UUID] = Query(None),
    job_id: Optional[uuid.UUID] = Query(None),
    interviewer_id: Optional[uuid.UUID] = Query(None),
    status: Optional[InterviewStatus] = Query(None),
    round_type: Optional[InterviewRoundType] = Query(None),
    interview_mode: Optional[InterviewMode] = Query(None),
    timeframe: Optional[str] = Query(None, description="'upcoming', 'past', or 'today'"),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List agency interviews with filters for status, date range, interviewers, and jobs."""
    service = InterviewService(db, current_user.agency_id)
    return service.list_interviews(
        application_id=application_id,
        job_id=job_id,
        interviewer_id=interviewer_id,
        status=status,
        round_type=round_type,
        interview_mode=interview_mode,
        timeframe=timeframe,
        search=search,
        skip=skip,
        limit=limit,
        current_user=current_user,
    )


@router.get("/{interview_id}", response_model=InterviewDetailRead)
def get_interview_detail(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete interview detail, participants, privacy-filtered feedback, and history."""
    service = InterviewService(db, current_user.agency_id)
    return service.get_interview_detail(interview_id, current_user)


@router.patch("/{interview_id}", response_model=InterviewRead)
def update_interview(
    interview_id: uuid.UUID,
    data: InterviewUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Update interview general details (title, round, mode, location, meeting URL)."""
    service = InterviewService(db, current_user.agency_id)
    return service.update_interview(interview_id, current_user, data)


@router.post("/{interview_id}/confirm", response_model=InterviewRead)
def confirm_interview(
    interview_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Confirm a scheduled interview."""
    service = InterviewService(db, current_user.agency_id)
    return service.confirm_interview(interview_id, current_user)


@router.post("/{interview_id}/reschedule", response_model=InterviewRead)
def reschedule_interview(
    interview_id: uuid.UUID,
    data: InterviewReschedule,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Reschedule an interview with conflict checking and history preservation."""
    service = InterviewService(db, current_user.agency_id)
    return service.reschedule_interview(interview_id, current_user, data)


@router.post("/{interview_id}/cancel", response_model=InterviewRead)
def cancel_interview(
    interview_id: uuid.UUID,
    data: InterviewCancel,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Cancel an interview with reason, preserving audit history."""
    service = InterviewService(db, current_user.agency_id)
    return service.cancel_interview(interview_id, current_user, data)


@router.post("/{interview_id}/complete", response_model=InterviewRead)
def complete_interview(
    interview_id: uuid.UUID,
    data: InterviewComplete,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Mark an interview as completed."""
    service = InterviewService(db, current_user.agency_id)
    return service.complete_interview(interview_id, current_user, data)


@router.get("/{interview_id}/history", response_model=List[InterviewHistoryRead])
def get_interview_history(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve complete audit history for this interview."""
    service = InterviewService(db, current_user.agency_id)
    return service.get_interview_history(interview_id)


@router.get("/{interview_id}/feedback", response_model=List[InterviewFeedbackRead])
def get_interview_feedbacks(
    interview_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve all feedbacks for this interview (private feedbacks filtered per RBAC)."""
    service = InterviewService(db, current_user.agency_id)
    return service.get_interview_feedbacks(interview_id, current_user)


@router.post(
    "/{interview_id}/feedback",
    response_model=InterviewFeedbackRead,
    status_code=status.HTTP_201_CREATED,
)
def submit_interview_feedback(
    interview_id: uuid.UUID,
    data: InterviewFeedbackCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Submit structured reviewer evaluation and recommendation."""
    service = InterviewService(db, current_user.agency_id)
    return service.submit_feedback(interview_id, current_user, data)


@router.patch(
    "/{interview_id}/feedback/{feedback_id}",
    response_model=InterviewFeedbackRead,
)
def update_interview_feedback(
    interview_id: uuid.UUID,
    feedback_id: uuid.UUID,
    data: InterviewFeedbackUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Edit interview feedback (author or OWNER/ADMIN only)."""
    service = InterviewService(db, current_user.agency_id)
    return service.update_feedback(interview_id, feedback_id, current_user, data)


# -------------------------------------------------------------
# /recruiters/{recruiter_id}/interviews endpoint
# -------------------------------------------------------------

@recruiter_interview_router.get(
    "/{recruiter_id}/interviews",
    response_model=List[InterviewRead],
)
def list_recruiter_interviews(
    recruiter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all interviews assigned to or created by a specific recruiter."""
    service = InterviewService(db, current_user.agency_id)
    return service.list_recruiter_interviews(recruiter_id, current_user=current_user)
