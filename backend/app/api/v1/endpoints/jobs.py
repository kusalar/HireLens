import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole, JobStatus, WorkMode
from app.schemas.job import (
    JobCreate,
    JobUpdate,
    JobRead,
    JobListRead,
    JobRequirementCreate,
    JobRequirementUpdate,
    JobRequirementRead,
)
from app.services.job_service import JobService
from app.services.matching_service import MatchingService
from app.schemas.matching import (
    JobMatchRunRead,
    JobMatchResultRead,
    JobMatchListResponse,
    JobMatchResultDetailResponse,
    MatchEvidenceRead,
)
from app.api.v1.endpoints.matching import serialize_result
from app.api.deps import get_current_user, require_roles, require_non_demo_mutation


router = APIRouter()

@router.get("", response_model=List[JobListRead])
def list_jobs(
    status: Optional[JobStatus] = Query(None),
    work_mode: Optional[WorkMode] = Query(None),
    search: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.list_jobs(
        status=status,
        work_mode=work_mode,
        search=search,
        skip=skip,
        limit=limit,
    )

@router.post("", response_model=JobRead, status_code=status.HTTP_201_CREATED)
def create_job(
    data: JobCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.create_job(current_user, data)

@router.get("/{job_id}", response_model=JobRead)
def get_job(
    job_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.get_job(job_id)

@router.patch("/{job_id}", response_model=JobRead)
def update_job(
    job_id: uuid.UUID,
    data: JobUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.update_job(current_user, job_id, data)

@router.delete("/{job_id}")
def delete_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    service.delete_job(current_user, job_id)
    return {"message": "Job successfully deleted."}

@router.post("/{job_id}/archive", response_model=JobRead)
def archive_job(
    job_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.archive_job(current_user, job_id)

@router.post("/{job_id}/requirements", response_model=JobRequirementRead, status_code=status.HTTP_201_CREATED)
def add_job_requirement(
    job_id: uuid.UUID,
    data: JobRequirementCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.add_requirement(current_user, job_id, data)

@router.patch("/{job_id}/requirements/{requirement_id}", response_model=JobRequirementRead)
def update_job_requirement(
    job_id: uuid.UUID,
    requirement_id: uuid.UUID,
    data: JobRequirementUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    return service.update_requirement(current_user, job_id, requirement_id, data)

@router.delete("/{job_id}/requirements/{requirement_id}")
def delete_job_requirement(
    job_id: uuid.UUID,
    requirement_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    _: User = Depends(require_non_demo_mutation),
    db: Session = Depends(get_db),
):
    service = JobService(db, current_user.agency_id)
    service.delete_requirement(current_user, job_id, requirement_id)
    return {"message": "Job requirement successfully deleted."}


# ==========================================
# Matching Endpoints
# ==========================================

@router.post("/{job_id}/match", response_model=JobMatchRunRead, status_code=status.HTTP_201_CREATED)
def start_job_matching(
    job_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    """
    Executes a deterministic matching run for the job across agency candidates.
    Generates deterministic dimension scores, retrieves evidence, and produces AI explanations.
    """
    service = MatchingService(db, current_user.agency_id)
    run = service.run_matching_for_job(job_id, current_user)
    return JobMatchRunRead.model_validate(run)


@router.get("/{job_id}/matches", response_model=JobMatchListResponse)
def list_job_matches(
    job_id: uuid.UUID,
    min_score: Optional[float] = Query(None, ge=0.0, le=100.0),
    search: Optional[str] = Query(None),
    run_id: Optional[uuid.UUID] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieves match results for the given job with filtering, candidate search, and pagination.
    """
    service = MatchingService(db, current_user.agency_id)
    skip = (page - 1) * page_size
    results, total, latest_run = service.list_matches_for_job(
        job_id=job_id,
        min_score=min_score,
        search=search,
        run_id=run_id,
        skip=skip,
        limit=page_size,
    )
    items = [serialize_result(r) for r in results]
    latest_run_read = JobMatchRunRead.model_validate(latest_run) if latest_run else None
    return JobMatchListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        latest_run=latest_run_read,
    )


@router.get("/{job_id}/matches/{candidate_id}", response_model=JobMatchResultDetailResponse)
def get_job_candidate_match(
    job_id: uuid.UUID,
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns detailed match result for a candidate on a job, including all criterion-level evidence records.
    """
    service = MatchingService(db, current_user.agency_id)
    # Validate job belongs to agency
    service.job_repo.get_detail(job_id)
    result = service.get_candidate_match_detail(job_id, candidate_id)
    evidences = [MatchEvidenceRead.model_validate(ev) for ev in (result.evidences or [])]
    run_read = JobMatchRunRead.model_validate(result.match_run) if result.match_run else None
    return JobMatchResultDetailResponse(
        result=serialize_result(result),
        evidences=evidences,
        run=run_read,
    )

