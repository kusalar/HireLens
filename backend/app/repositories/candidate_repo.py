import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, or_, distinct
from app.models.candidate import (
    Candidate,
    CandidateExperience,
    CandidateEducation,
    CandidateSkill,
    RecruiterNote,
)
from app.models.enums import CandidateProfileStatus
from app.repositories.base import BaseTenantRepository

class CandidateRepository(BaseTenantRepository[Candidate]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(Candidate, db, agency_id)

    def get_profile(self, id: uuid.UUID) -> Optional[Candidate]:
        stmt = (
            select(Candidate)
            .where(Candidate.id == id, Candidate.agency_id == self.agency_id)
            .options(
                selectinload(Candidate.experiences),
                selectinload(Candidate.educations),
                selectinload(Candidate.skills),
                selectinload(Candidate.notes).selectinload(RecruiterNote.author),
            )
        )
        return self.db.scalars(stmt).first()

    def get_detail(self, id: uuid.UUID) -> Optional[Candidate]:
        return self.get_profile(id)


    def list_filtered(
        self,
        search: Optional[str] = None,
        skill: Optional[str] = None,
        location: Optional[str] = None,
        min_experience_months: Optional[int] = None,
        status: Optional[CandidateProfileStatus] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> List[Candidate]:
        stmt = (
            select(Candidate)
            .where(Candidate.agency_id == self.agency_id)
            .options(
                selectinload(Candidate.skills),
            )
        )

        if status:
            stmt = stmt.where(Candidate.profile_status == status)
        if location:
            stmt = stmt.where(Candidate.current_location.ilike(f"%{location.strip()}%"))
        if min_experience_months is not None:
            stmt = stmt.where(Candidate.total_experience_months >= min_experience_months)
        if search:
            search_term = f"%{search.strip()}%"
            stmt = stmt.where(
                or_(
                    Candidate.full_name.ilike(search_term),
                    Candidate.email.ilike(search_term),
                    Candidate.current_title.ilike(search_term),
                    Candidate.professional_summary.ilike(search_term),
                )
            )
        if skill:
            skill_term = f"%{skill.strip()}%"
            stmt = stmt.join(Candidate.skills).where(
                or_(
                    CandidateSkill.skill_name.ilike(skill_term),
                    CandidateSkill.normalized_skill.ilike(skill_term),
                )
            ).distinct()

        stmt = stmt.order_by(Candidate.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt).all())

    def check_duplicate(self, email: Optional[str], full_name: str) -> Optional[Candidate]:
        """Cautious duplicate check inside current agency."""
        if email:
            stmt = select(Candidate).where(
                Candidate.agency_id == self.agency_id,
                Candidate.email == email.lower().strip(),
            )
            found = self.db.scalars(stmt).first()
            if found:
                return found

        stmt = select(Candidate).where(
            Candidate.agency_id == self.agency_id,
            Candidate.full_name.ilike(full_name.strip()),
        )
        return self.db.scalars(stmt).first()

    def archive(self, id: uuid.UUID) -> Optional[Candidate]:
        candidate = self.get(id)
        if candidate:
            candidate.profile_status = CandidateProfileStatus.ARCHIVED
            self.db.commit()
            self.db.refresh(candidate)
        return candidate

    # --- Recruiter Notes ---

    def add_note(self, candidate_id: uuid.UUID, author_id: uuid.UUID, note_text: str) -> Optional[RecruiterNote]:
        candidate = self.get(candidate_id)
        if not candidate:
            return None
        note = RecruiterNote(
            id=uuid.uuid4(),
            candidate_id=candidate.id,
            agency_id=self.agency_id,
            created_by=author_id,
            note=note_text.strip(),
        )
        self.db.add(note)
        self.db.commit()
        self.db.refresh(note)
        return note

    def get_note(self, candidate_id: uuid.UUID, note_id: uuid.UUID) -> Optional[RecruiterNote]:
        # Validate candidate belongs to agency
        candidate = self.get(candidate_id)
        if not candidate:
            return None
        stmt = select(RecruiterNote).where(
            RecruiterNote.id == note_id,
            RecruiterNote.candidate_id == candidate_id,
            RecruiterNote.agency_id == self.agency_id,
        ).options(selectinload(RecruiterNote.author))
        return self.db.scalars(stmt).first()

    def update_note(self, candidate_id: uuid.UUID, note_id: uuid.UUID, new_text: str) -> Optional[RecruiterNote]:
        note = self.get_note(candidate_id, note_id)
        if not note:
            return None
        note.note = new_text.strip()
        self.db.commit()
        self.db.refresh(note)
        return note

    def delete_note(self, candidate_id: uuid.UUID, note_id: uuid.UUID) -> bool:
        note = self.get_note(candidate_id, note_id)
        if not note:
            return False
        self.db.delete(note)
        self.db.commit()
        return True

    # --- Experience, Education, Skills Sub-entities ---

    def add_experience(self, candidate_id: uuid.UUID, exp: CandidateExperience) -> Optional[CandidateExperience]:
        candidate = self.get(candidate_id)
        if not candidate:
            return None
        exp.candidate_id = candidate.id
        self.db.add(exp)
        self.db.commit()
        self.db.refresh(exp)
        return exp

    def delete_experience(self, candidate_id: uuid.UUID, exp_id: uuid.UUID) -> bool:
        candidate = self.get(candidate_id)
        if not candidate:
            return False
        stmt = select(CandidateExperience).where(
            CandidateExperience.id == exp_id,
            CandidateExperience.candidate_id == candidate_id,
        )
        exp = self.db.scalars(stmt).first()
        if not exp:
            return False
        self.db.delete(exp)
        self.db.commit()
        return True

    def add_education(self, candidate_id: uuid.UUID, edu: CandidateEducation) -> Optional[CandidateEducation]:
        candidate = self.get(candidate_id)
        if not candidate:
            return None
        edu.candidate_id = candidate.id
        self.db.add(edu)
        self.db.commit()
        self.db.refresh(edu)
        return edu

    def delete_education(self, candidate_id: uuid.UUID, edu_id: uuid.UUID) -> bool:
        candidate = self.get(candidate_id)
        if not candidate:
            return False
        stmt = select(CandidateEducation).where(
            CandidateEducation.id == edu_id,
            CandidateEducation.candidate_id == candidate_id,
        )
        edu = self.db.scalars(stmt).first()
        if not edu:
            return False
        self.db.delete(edu)
        self.db.commit()
        return True

    def add_skill(self, candidate_id: uuid.UUID, skill: CandidateSkill) -> Optional[CandidateSkill]:
        candidate = self.get(candidate_id)
        if not candidate:
            return None
        skill.candidate_id = candidate.id
        self.db.add(skill)
        self.db.commit()
        self.db.refresh(skill)
        return skill

    def delete_skill(self, candidate_id: uuid.UUID, skill_id: uuid.UUID) -> bool:
        candidate = self.get(candidate_id)
        if not candidate:
            return False
        stmt = select(CandidateSkill).where(
            CandidateSkill.id == skill_id,
            CandidateSkill.candidate_id == candidate_id,
        )
        skill = self.db.scalars(stmt).first()
        if not skill:
            return False
        self.db.delete(skill)
        self.db.commit()
        return True
