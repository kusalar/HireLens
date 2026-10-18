import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, or_, func, desc
from app.models.resume import (
    Resume,
    ResumeParseRun,
    ResumeExtractedProfile,
    ResumeEvidence,
)
from app.models.candidate import Candidate
from app.models.enums import (
    ResumeProcessingStatus,
    VerificationStatus,
    RecruiterReviewStatus,
)
from app.repositories.base import BaseTenantRepository


class ResumeRepository(BaseTenantRepository[Resume]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(Resume, db, agency_id)

    def get_by_sha256(self, sha256_hash: str) -> Optional[Resume]:
        """Find an existing resume in this agency by its SHA-256 hash."""
        stmt = select(Resume).where(
            Resume.agency_id == self.agency_id,
            Resume.sha256_hash == sha256_hash,
        )
        return self.db.scalars(stmt).first()

    def get_detail(self, id: uuid.UUID) -> Optional[Resume]:
        """Fetch a resume with eager loaded relationships strictly scoped to this agency."""
        stmt = (
            select(Resume)
            .where(Resume.id == id, Resume.agency_id == self.agency_id)
            .options(
                selectinload(Resume.candidate),
                selectinload(Resume.parse_runs),
                selectinload(Resume.extracted_profiles),
                selectinload(Resume.evidences),
            )
        )
        return self.db.scalars(stmt).first()

    def list_filtered(
        self,
        search: Optional[str] = None,
        status: Optional[ResumeProcessingStatus] = None,
        candidate_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Resume], int]:
        """List and search resumes strictly scoped to agency_id."""
        query = select(Resume).where(Resume.agency_id == self.agency_id)

        if status:
            query = query.where(Resume.processing_status == status)

        if candidate_id:
            query = query.where(Resume.candidate_id == candidate_id)

        if search:
            search_term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Resume.original_filename.ilike(search_term),
                    Resume.mime_type.ilike(search_term),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Order by newest first
        paged_stmt = (
            query.options(selectinload(Resume.candidate))
            .order_by(desc(Resume.created_at))
            .offset(skip)
            .limit(limit)
        )
        items = list(self.db.scalars(paged_stmt).all())
        return items, total

    # ==========================================
    # Parse Run Operations
    # ==========================================

    def create_parse_run(self, run: ResumeParseRun) -> ResumeParseRun:
        run.agency_id = self.agency_id
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_parse_run(self, run_id: uuid.UUID) -> Optional[ResumeParseRun]:
        stmt = select(ResumeParseRun).where(
            ResumeParseRun.id == run_id,
            ResumeParseRun.agency_id == self.agency_id,
        )
        return self.db.scalars(stmt).first()

    def list_parse_runs(self, resume_id: uuid.UUID) -> List[ResumeParseRun]:
        stmt = (
            select(ResumeParseRun)
            .where(
                ResumeParseRun.resume_id == resume_id,
                ResumeParseRun.agency_id == self.agency_id,
            )
            .order_by(desc(ResumeParseRun.created_at))
        )
        return list(self.db.scalars(stmt).all())

    # ==========================================
    # Extracted Profile Operations
    # ==========================================

    def create_extracted_profile(self, profile: ResumeExtractedProfile) -> ResumeExtractedProfile:
        profile.agency_id = self.agency_id
        self.db.add(profile)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    def get_extracted_profile(self, profile_id: uuid.UUID) -> Optional[ResumeExtractedProfile]:
        stmt = select(ResumeExtractedProfile).where(
            ResumeExtractedProfile.id == profile_id,
            ResumeExtractedProfile.agency_id == self.agency_id,
        )
        return self.db.scalars(stmt).first()

    def get_latest_extracted_profile(self, resume_id: uuid.UUID) -> Optional[ResumeExtractedProfile]:
        stmt = (
            select(ResumeExtractedProfile)
            .where(
                ResumeExtractedProfile.resume_id == resume_id,
                ResumeExtractedProfile.agency_id == self.agency_id,
            )
            .order_by(desc(ResumeExtractedProfile.created_at))
        )
        return self.db.scalars(stmt).first()

    def update_extracted_profile(
        self, profile: ResumeExtractedProfile, updates: dict
    ) -> ResumeExtractedProfile:
        for k, v in updates.items():
            if hasattr(profile, k):
                setattr(profile, k, v)
        self.db.commit()
        self.db.refresh(profile)
        return profile

    # ==========================================
    # Evidence Operations
    # ==========================================

    def create_evidence(self, evidence: ResumeEvidence) -> ResumeEvidence:
        evidence.agency_id = self.agency_id
        self.db.add(evidence)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence

    def get_evidence(self, evidence_id: uuid.UUID) -> Optional[ResumeEvidence]:
        stmt = select(ResumeEvidence).where(
            ResumeEvidence.id == evidence_id,
            ResumeEvidence.agency_id == self.agency_id,
        )
        return self.db.scalars(stmt).first()

    def list_evidences(self, resume_id: uuid.UUID) -> List[ResumeEvidence]:
        stmt = (
            select(ResumeEvidence)
            .where(
                ResumeEvidence.resume_id == resume_id,
                ResumeEvidence.agency_id == self.agency_id,
            )
            .order_by(ResumeEvidence.created_at.asc())
        )
        return list(self.db.scalars(stmt).all())

    def update_evidence(self, evidence: ResumeEvidence, updates: dict) -> ResumeEvidence:
        for k, v in updates.items():
            if hasattr(evidence, k):
                setattr(evidence, k, v)
        self.db.commit()
        self.db.refresh(evidence)
        return evidence
