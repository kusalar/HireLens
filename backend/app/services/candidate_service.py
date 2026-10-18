import uuid
from typing import List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.candidate import (
    Candidate,
    CandidateExperience,
    CandidateEducation,
    CandidateSkill,
    RecruiterNote,
)
from app.models.entities import User, AuditLog
from app.models.enums import CandidateProfileStatus
from app.schemas.candidate import (
    CandidateCreate,
    CandidateUpdate,
    CandidateRead,
    CandidateListRead,
    CandidateExperienceCreate,
    CandidateEducationCreate,
    CandidateSkillCreate,
    RecruiterNoteCreate,
    RecruiterNoteUpdate,
    RecruiterNoteRead,
)
from app.repositories.candidate_repo import CandidateRepository

class CandidateService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = CandidateRepository(db, agency_id)

    def create_candidate(self, current_user: User, data: CandidateCreate) -> Candidate:
        # Cautious duplicate check
        duplicate = self.repo.check_duplicate(
            email=str(data.email) if data.email else None,
            full_name=data.full_name,
        )
        if duplicate:
            # We log an audit/warning, but allow user control rather than auto-merging or breaking
            pass

        candidate = Candidate(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            full_name=data.full_name.strip(),
            email=str(data.email).lower().strip() if data.email else None,
            phone_encrypted=data.phone_encrypted.strip() if data.phone_encrypted else None,
            current_title=data.current_title.strip() if data.current_title else None,
            total_experience_months=data.total_experience_months,
            current_location=data.current_location.strip() if data.current_location else None,
            professional_summary=data.professional_summary,
            profile_status=data.profile_status,
            source=data.source.strip() if data.source else None,
        )

        if data.experiences:
            for exp_in in data.experiences:
                candidate.experiences.append(
                    CandidateExperience(
                        id=uuid.uuid4(),
                        company=exp_in.company.strip(),
                        job_title=exp_in.job_title.strip(),
                        start_date=exp_in.start_date,
                        end_date=exp_in.end_date,
                        description=exp_in.description,
                    )
                )

        if data.educations:
            for edu_in in data.educations:
                candidate.educations.append(
                    CandidateEducation(
                        id=uuid.uuid4(),
                        institution=edu_in.institution.strip(),
                        qualification=edu_in.qualification.strip(),
                        field_of_study=edu_in.field_of_study.strip() if edu_in.field_of_study else None,
                        start_year=edu_in.start_year,
                        end_year=edu_in.end_year,
                    )
                )

        if data.skills:
            for skill_in in data.skills:
                candidate.skills.append(
                    CandidateSkill(
                        id=uuid.uuid4(),
                        skill_name=skill_in.skill_name.strip(),
                        normalized_skill=skill_in.normalized_skill.strip() if skill_in.normalized_skill else None,
                        proficiency=skill_in.proficiency,
                        evidence=skill_in.evidence,
                        source_page=skill_in.source_page,
                    )
                )

        created_candidate = self.repo.create(candidate)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="CANDIDATE_CREATED",
            resource_type="Candidate",
            resource_id=str(created_candidate.id),
            details=f"Candidate '{created_candidate.full_name}' created by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_candidate_profile(created_candidate.id)

    def list_candidates(
        self,
        search: Optional[str] = None,
        skill: Optional[str] = None,
        location: Optional[str] = None,
        min_experience_months: Optional[int] = None,
        status: Optional[CandidateProfileStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[CandidateListRead]:
        candidates = self.repo.list_filtered(
            search=search,
            skill=skill,
            location=location,
            min_experience_months=min_experience_months,
            status=status,
            skip=skip,
            limit=limit,
        )

        result = []
        for c in candidates:
            skills_preview = [s.skill_name for s in c.skills[:5]] if c.skills else []
            result.append(
                CandidateListRead(
                    id=c.id,
                    agency_id=c.agency_id,
                    full_name=c.full_name,
                    email=c.email,
                    current_title=c.current_title,
                    total_experience_months=c.total_experience_months,
                    current_location=c.current_location,
                    profile_status=c.profile_status,
                    source=c.source,
                    skills_preview=skills_preview,
                    created_at=c.created_at,
                )
            )
        return result

    def get_candidate_profile(self, candidate_id: uuid.UUID) -> CandidateRead:
        candidate = self.repo.get_profile(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )

        # Map recruiter notes with author names
        notes_read = []
        for n in candidate.notes:
            notes_read.append(
                RecruiterNoteRead(
                    id=n.id,
                    candidate_id=n.candidate_id,
                    agency_id=n.agency_id,
                    created_by=n.created_by,
                    note=n.note,
                    created_at=n.created_at,
                    updated_at=n.updated_at,
                    author_name=n.author.full_name if n.author else None,
                )
            )

        return CandidateRead(
            id=candidate.id,
            agency_id=candidate.agency_id,
            full_name=candidate.full_name,
            email=candidate.email,
            phone_encrypted=candidate.phone_encrypted,
            current_title=candidate.current_title,
            total_experience_months=candidate.total_experience_months,
            current_location=candidate.current_location,
            professional_summary=candidate.professional_summary,
            profile_status=candidate.profile_status,
            created_at=candidate.created_at,
            updated_at=candidate.updated_at,
            experiences=candidate.experiences,
            educations=candidate.educations,
            skills=candidate.skills,
            notes=notes_read,
        )

    def update_candidate(
        self, current_user: User, candidate_id: uuid.UUID, data: CandidateUpdate
    ) -> CandidateRead:
        candidate = self.repo.get(candidate_id)
        if not candidate:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )

        updates = data.model_dump(exclude_unset=True)
        if "email" in updates and updates["email"]:
            updates["email"] = str(updates["email"]).lower().strip()

        self.repo.update(candidate, updates)

        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="CANDIDATE_UPDATED",
            resource_type="Candidate",
            resource_id=str(candidate_id),
            details=f"Candidate '{candidate.full_name}' updated by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()

        return self.get_candidate_profile(candidate_id)

    def archive_candidate(self, current_user: User, candidate_id: uuid.UUID) -> CandidateRead:
        archived = self.repo.archive(candidate_id)
        if not archived:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )
        audit = AuditLog(
            agency_id=self.agency_id,
            user_id=current_user.id,
            action="CANDIDATE_ARCHIVED",
            resource_type="Candidate",
            resource_id=str(candidate_id),
            details=f"Candidate '{archived.full_name}' archived by {current_user.email}",
        )
        self.db.add(audit)
        self.db.commit()
        return self.get_candidate_profile(candidate_id)

    # --- Recruiter Notes ---

    def add_recruiter_note(
        self, current_user: User, candidate_id: uuid.UUID, data: RecruiterNoteCreate
    ) -> RecruiterNoteRead:
        note = self.repo.add_note(candidate_id, current_user.id, data.note)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )
        return RecruiterNoteRead(
            id=note.id,
            candidate_id=note.candidate_id,
            agency_id=note.agency_id,
            created_by=note.created_by,
            note=note.note,
            created_at=note.created_at,
            updated_at=note.updated_at,
            author_name=current_user.full_name,
        )

    def update_recruiter_note(
        self,
        current_user: User,
        candidate_id: uuid.UUID,
        note_id: uuid.UUID,
        data: RecruiterNoteUpdate,
    ) -> RecruiterNoteRead:
        note = self.repo.update_note(candidate_id, note_id, data.note)
        if not note:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter note not found or unauthorized.",
            )
        return RecruiterNoteRead(
            id=note.id,
            candidate_id=note.candidate_id,
            agency_id=note.agency_id,
            created_by=note.created_by,
            note=note.note,
            created_at=note.created_at,
            updated_at=note.updated_at,
            author_name=note.author.full_name if note.author else current_user.full_name,
        )

    def delete_recruiter_note(
        self, current_user: User, candidate_id: uuid.UUID, note_id: uuid.UUID
    ) -> bool:
        deleted = self.repo.delete_note(candidate_id, note_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter note not found or unauthorized.",
            )
        return True

    # --- Sub-entity methods ---

    def add_experience(
        self, current_user: User, candidate_id: uuid.UUID, data: CandidateExperienceCreate
    ) -> CandidateExperience:
        exp = CandidateExperience(
            id=uuid.uuid4(),
            company=data.company.strip(),
            job_title=data.job_title.strip(),
            start_date=data.start_date,
            end_date=data.end_date,
            description=data.description,
        )
        created = self.repo.add_experience(candidate_id, exp)
        if not created:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )
        return created

    def delete_experience(
        self, current_user: User, candidate_id: uuid.UUID, experience_id: uuid.UUID
    ) -> bool:
        deleted = self.repo.delete_experience(candidate_id, experience_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Experience record not found or unauthorized.",
            )
        return True

    def add_education(
        self, current_user: User, candidate_id: uuid.UUID, data: CandidateEducationCreate
    ) -> CandidateEducation:
        edu = CandidateEducation(
            id=uuid.uuid4(),
            institution=data.institution.strip(),
            qualification=data.qualification.strip(),
            field_of_study=data.field_of_study.strip() if data.field_of_study else None,
            start_year=data.start_year,
            end_year=data.end_year,
        )
        created = self.repo.add_education(candidate_id, edu)
        if not created:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )
        return created

    def delete_education(
        self, current_user: User, candidate_id: uuid.UUID, education_id: uuid.UUID
    ) -> bool:
        deleted = self.repo.delete_education(candidate_id, education_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Education record not found or unauthorized.",
            )
        return True

    def add_skill(
        self, current_user: User, candidate_id: uuid.UUID, data: CandidateSkillCreate
    ) -> CandidateSkill:
        skill = CandidateSkill(
            id=uuid.uuid4(),
            skill_name=data.skill_name.strip(),
            normalized_skill=data.normalized_skill.strip() if data.normalized_skill else None,
            proficiency=data.proficiency,
            evidence=data.evidence,
            source_page=data.source_page,
        )
        created = self.repo.add_skill(candidate_id, skill)
        if not created:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate not found or unauthorized.",
            )
        return created

    def delete_skill(
        self, current_user: User, candidate_id: uuid.UUID, skill_id: uuid.UUID
    ) -> bool:
        deleted = self.repo.delete_skill(candidate_id, skill_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Skill record not found or unauthorized.",
            )
        return True
