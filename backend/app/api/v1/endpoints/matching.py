import uuid
import json
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, status, HTTPException
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.api.deps import get_current_user, require_roles
from app.models.entities import User
from app.models.enums import UserRole
from app.models.matching import JobMatchResult, JobMatchRun
from app.services.matching_service import MatchingService
from app.schemas.matching import (
    JobMatchRunRead,
    JobMatchResultRead,
    MatchEvidenceRead,
    JobMatchListResponse,
    JobMatchResultDetailResponse,
    RecalculateMatchRequest,
)

router = APIRouter()

MUTATION_ROLES = [UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER]


def serialize_result(res: JobMatchResult) -> JobMatchResultRead:
    return JobMatchResultRead(
        id=res.id,
        agency_id=res.agency_id,
        job_id=res.job_id,
        candidate_id=res.candidate_id,
        match_run_id=res.match_run_id,
        overall_score=res.overall_score,
        required_skills_score=res.required_skills_score,
        experience_score=res.experience_score,
        preferred_skills_score=res.preferred_skills_score,
        project_relevance_score=res.project_relevance_score,
        other_criteria_score=res.other_criteria_score,
        matched_requirements_count=res.matched_requirements_count,
        partial_requirements_count=res.partial_requirements_count,
        missing_requirements_count=res.missing_requirements_count,
        needs_verification_count=res.needs_verification_count,
        explanation=res.explanation,
        strengths=json.loads(res.strengths) if res.strengths else [],
        skill_gaps=json.loads(res.skill_gaps) if res.skill_gaps else [],
        verification_items=json.loads(res.verification_items) if res.verification_items else [],
        suggested_questions=json.loads(res.suggested_questions) if res.suggested_questions else [],
        scoring_version=res.scoring_version,
        status=res.status,
        created_at=res.created_at,
        updated_at=res.updated_at,
        candidate_name=res.candidate.full_name if res.candidate else None,
        candidate_title=res.candidate.current_title if res.candidate else None,
        candidate_email=res.candidate.email if res.candidate else None,
        candidate_location=res.candidate.current_location if res.candidate else None,
        job_title=res.job.title if res.job else None,
        source_fingerprint=res.source_fingerprint,
        is_stale=(
            res.status in ("STALE", "HISTORICAL")
            or bool(res.job and res.job.updated_at and res.created_at and res.job.updated_at > res.created_at)
            or bool(res.candidate and res.candidate.updated_at and res.created_at and res.candidate.updated_at > res.created_at)
        ),
    )




# ==========================================
# Matching Runs
# ==========================================

@router.get("/runs/{run_id}", response_model=JobMatchRunRead)
def get_run_status(
    run_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MatchingService(db, current_user.agency_id)
    run = service.get_run_status(run_id)
    return JobMatchRunRead.model_validate(run)


@router.get("/runs/{run_id}/results", response_model=List[JobMatchResultRead])
def get_run_results(
    run_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    service = MatchingService(db, current_user.agency_id)
    # Validate run belongs to agency
    service.get_run_status(run_id)
    results, _ = service.repo.list_results_for_run(run_id, skip=skip, limit=limit)
    return [serialize_result(r) for r in results]


# ==========================================
# Match Result Actions
# ==========================================

@router.post("/results/{result_id}/refresh-explanation", response_model=JobMatchResultRead)
def refresh_match_explanation(
    result_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = MatchingService(db, current_user.agency_id)
    updated = service.refresh_explanation(result_id, current_user)
    return serialize_result(updated)


@router.post("/results/{result_id}/recalculate", response_model=JobMatchResultRead)
def recalculate_match_result(
    result_id: uuid.UUID,
    req: RecalculateMatchRequest = RecalculateMatchRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(*MUTATION_ROLES)),
):
    service = MatchingService(db, current_user.agency_id)
    updated = service.recalculate_result(result_id, current_user, scoring_version=req.scoring_version or "v1.0")
    return serialize_result(updated)
