import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.models.entities import User
from app.models.enums import UserRole, CandidateProfileStatus
from app.schemas.candidate import (
    CandidateCreate,
    CandidateUpdate,
    CandidateRead,
    CandidateListRead,
    CandidateExperienceCreate,
    CandidateExperienceRead,
    CandidateEducationCreate,
    CandidateEducationRead,
    CandidateSkillCreate,
    CandidateSkillRead,
    RecruiterNoteCreate,
    RecruiterNoteUpdate,
    RecruiterNoteRead,
)
from app.services.candidate_service import CandidateService
from app.services.matching_service import MatchingService
from app.schemas.matching import JobMatchResultRead
from app.api.v1.endpoints.matching import serialize_result
from app.api.deps import get_current_user, require_roles


router = APIRouter()

@router.get("", response_model=List[CandidateListRead])
def list_candidates(
    search: Optional[str] = Query(None),
    skill: Optional[str] = Query(None),
    location: Optional[str] = Query(None),
    min_experience_months: Optional[int] = Query(None, ge=0),
    status: Optional[CandidateProfileStatus] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.list_candidates(
        search=search,
        skill=skill,
        location=location,
        min_experience_months=min_experience_months,
        status=status,
        skip=skip,
        limit=limit,
    )

@router.post("", response_model=CandidateRead, status_code=status.HTTP_201_CREATED)
def create_candidate(
    data: CandidateCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.create_candidate(current_user, data)

@router.get("/{candidate_id}", response_model=CandidateRead)
def get_candidate(
    candidate_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.get_candidate_profile(candidate_id)

@router.patch("/{candidate_id}", response_model=CandidateRead)
def update_candidate(
    candidate_id: uuid.UUID,
    data: CandidateUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.update_candidate(current_user, candidate_id, data)

@router.post("/{candidate_id}/archive", response_model=CandidateRead)
def archive_candidate(
    candidate_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.archive_candidate(current_user, candidate_id)

# --- Recruiter Notes ---

@router.post("/{candidate_id}/notes", response_model=RecruiterNoteRead, status_code=status.HTTP_201_CREATED)
def add_recruiter_note(
    candidate_id: uuid.UUID,
    data: RecruiterNoteCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.add_recruiter_note(current_user, candidate_id, data)

@router.patch("/{candidate_id}/notes/{note_id}", response_model=RecruiterNoteRead)
def update_recruiter_note(
    candidate_id: uuid.UUID,
    note_id: uuid.UUID,
    data: RecruiterNoteUpdate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.update_recruiter_note(current_user, candidate_id, note_id, data)

@router.delete("/{candidate_id}/notes/{note_id}")
def delete_recruiter_note(
    candidate_id: uuid.UUID,
    note_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    service.delete_recruiter_note(current_user, candidate_id, note_id)
    return {"message": "Recruiter note deleted."}

# --- Sub-entity endpoints ---

@router.post("/{candidate_id}/experiences", response_model=CandidateExperienceRead, status_code=status.HTTP_201_CREATED)
def add_experience(
    candidate_id: uuid.UUID,
    data: CandidateExperienceCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.add_experience(current_user, candidate_id, data)

@router.delete("/{candidate_id}/experiences/{exp_id}")
def delete_experience(
    candidate_id: uuid.UUID,
    exp_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    service.delete_experience(current_user, candidate_id, exp_id)
    return {"message": "Experience record deleted."}

@router.post("/{candidate_id}/educations", response_model=CandidateEducationRead, status_code=status.HTTP_201_CREATED)
def add_education(
    candidate_id: uuid.UUID,
    data: CandidateEducationCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.add_education(current_user, candidate_id, data)

@router.delete("/{candidate_id}/educations/{edu_id}")
def delete_education(
    candidate_id: uuid.UUID,
    edu_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    service.delete_education(current_user, candidate_id, edu_id)
    return {"message": "Education record deleted."}

@router.post("/{candidate_id}/skills", response_model=CandidateSkillRead, status_code=status.HTTP_201_CREATED)
def add_skill(
    candidate_id: uuid.UUID,
    data: CandidateSkillCreate,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    return service.add_skill(current_user, candidate_id, data)

@router.delete("/{candidate_id}/skills/{skill_id}")
def delete_skill(
    candidate_id: uuid.UUID,
    skill_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)),
    db: Session = Depends(get_db),
):
    service = CandidateService(db, current_user.agency_id)
    service.delete_skill(current_user, candidate_id, skill_id)
    return {"message": "Skill record deleted."}


@router.get("/{candidate_id}/matches", response_model=List[JobMatchResultRead])
def get_candidate_matching_history(
    candidate_id: uuid.UUID,
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Returns candidate's matching history across all jobs belonging to the current agency.
    Strictly isolated: Never returns match results for any other agency.
    """
    service = MatchingService(db, current_user.agency_id)
    results = service.list_candidate_matching_history(candidate_id=candidate_id, limit=limit)
    return [serialize_result(r) for r in results]

