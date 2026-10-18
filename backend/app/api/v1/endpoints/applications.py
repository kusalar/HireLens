import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status, Body
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole, PipelineStageType
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStageTransition,
    ApplicationRead,
    ApplicationListResponse,
    ApplicationDetailRead,
    ApplicationStageHistoryRead,
    ApplicationNoteCreate,
    ApplicationNoteUpdate,
    ApplicationNoteRead,
    CandidateComparisonResponse,
    PipelineDashboardStats,
)
from app.services.application_service import ApplicationService
from app.api.deps import get_current_user, require_roles

# Main application router: mounted at /applications
router = APIRouter()

# Job-scoped application router: mounted at /jobs
job_router = APIRouter()

# Candidate-scoped application router: mounted at /candidates
candidate_router = APIRouter()

# Recruiter-scoped application router: mounted at /recruiters
recruiter_router = APIRouter()


# -------------------------------------------------------------
# /applications endpoints
# -------------------------------------------------------------

@router.get("/dashboard/stats", response_model=PipelineDashboardStats)
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve aggregate recruitment workspace and pipeline analytics for the agency."""
    service = ApplicationService(db, current_user.agency_id)
    return service.get_pipeline_dashboard_stats()


@router.get("/{application_id}", response_model=ApplicationDetailRead)
def get_application_detail(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fetch complete application detail with job, candidate, stage history, notes, and match evidence."""
    service = ApplicationService(db, current_user.agency_id)
    return service.get_application_detail(application_id)


@router.patch("/{application_id}", response_model=ApplicationRead)
def update_application(
    application_id: uuid.UUID,
    data: ApplicationUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Update application details, recruiter assignment, or archive status."""
    service = ApplicationService(db, current_user.agency_id)
    return service.update_application(application_id, current_user, data)


@router.post("/{application_id}/transition", response_model=ApplicationRead)
def transition_application_stage(
    application_id: uuid.UUID,
    data: ApplicationStageTransition,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Execute validated transactional stage change with audit log and immutable history."""
    service = ApplicationService(db, current_user.agency_id)
    return service.transition_stage(application_id, current_user, data)


@router.get("/{application_id}/history", response_model=List[ApplicationStageHistoryRead])
def get_application_stage_history(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve complete stage transition history for this application."""
    service = ApplicationService(db, current_user.agency_id)
    return service.get_stage_history(application_id)


@router.get("/{application_id}/notes", response_model=List[ApplicationNoteRead])
def get_application_notes(
    application_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Retrieve recruiter notes for this application."""
    service = ApplicationService(db, current_user.agency_id)
    return service.get_notes(application_id)


@router.post("/{application_id}/notes", response_model=ApplicationNoteRead, status_code=status.HTTP_201_CREATED)
def add_application_note(
    application_id: uuid.UUID,
    data: ApplicationNoteCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Add a new recruiter note to the application."""
    service = ApplicationService(db, current_user.agency_id)
    return service.add_note(application_id, current_user, data)


@router.patch("/{application_id}/notes/{note_id}", response_model=ApplicationNoteRead)
def update_application_note(
    application_id: uuid.UUID,
    note_id: uuid.UUID,
    data: ApplicationNoteUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Update an existing recruiter note (author or owner/admin only)."""
    service = ApplicationService(db, current_user.agency_id)
    return service.update_note(application_id, note_id, current_user, data)


# -------------------------------------------------------------
# /jobs/{job_id}/applications and compare endpoints
# -------------------------------------------------------------

@job_router.post("/{job_id}/applications", response_model=ApplicationRead, status_code=status.HTTP_201_CREATED)
def create_job_application(
    job_id: uuid.UUID,
    data: ApplicationCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """Create a new job-specific application for a candidate."""
    service = ApplicationService(db, current_user.agency_id)
    return service.create_application(job_id, current_user, data)


@job_router.get("/{job_id}/applications", response_model=ApplicationListResponse)
def list_job_applications(
    job_id: uuid.UUID,
    status: Optional[PipelineStageType] = Query(None),
    assigned_recruiter_id: Optional[uuid.UUID] = Query(None),
    search: Optional[str] = Query(None),
    include_archived: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List applications for a job opening with filtering, search, and stage counts."""
    service = ApplicationService(db, current_user.agency_id)
    return service.list_job_applications(
        job_id=job_id,
        status=status,
        assigned_recruiter_id=assigned_recruiter_id,
        search=search,
        include_archived=include_archived,
        skip=skip,
        limit=limit,
    )


@job_router.get("/{job_id}/compare", response_model=CandidateComparisonResponse)
def compare_job_candidates_get(
    job_id: uuid.UUID,
    candidate_ids: List[uuid.UUID] = Query(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare multiple candidates side-by-side for a specific job."""
    service = ApplicationService(db, current_user.agency_id)
    return service.compare_candidates(job_id=job_id, candidate_ids=candidate_ids)


@job_router.post("/{job_id}/compare", response_model=CandidateComparisonResponse)
def compare_job_candidates_post(
    job_id: uuid.UUID,
    candidate_ids: List[uuid.UUID] = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Compare multiple candidates side-by-side for a specific job via POST body."""
    service = ApplicationService(db, current_user.agency_id)
    return service.compare_candidates(job_id=job_id, candidate_ids=candidate_ids)


# -------------------------------------------------------------
# /candidates/{candidate_id}/applications endpoint
# -------------------------------------------------------------

@candidate_router.get("/{candidate_id}/applications", response_model=List[ApplicationRead])
def list_candidate_applications(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all applications across jobs for a specific candidate."""
    service = ApplicationService(db, current_user.agency_id)
    return service.list_candidate_applications(candidate_id)


# -------------------------------------------------------------
# /recruiters/{recruiter_id}/applications endpoint
# -------------------------------------------------------------

@recruiter_router.get("/{recruiter_id}/applications", response_model=List[ApplicationRead])
def list_recruiter_applications(
    recruiter_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all active applications assigned to a specific recruiter."""
    service = ApplicationService(db, current_user.agency_id)
    return service.list_recruiter_applications(recruiter_id)
