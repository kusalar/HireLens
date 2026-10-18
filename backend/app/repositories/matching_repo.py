import uuid
from typing import Optional, List, Tuple
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, and_, or_, func, desc
from app.models.matching import JobMatchRun, JobMatchResult, MatchEvidence
from app.models.candidate import Candidate
from app.models.job import Job
from app.repositories.base import BaseTenantRepository


class JobMatchRepository(BaseTenantRepository[JobMatchRun]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(JobMatchRun, db, agency_id)

    # ==========================================
    # Matching Runs
    # ==========================================

    def create_run(self, run: JobMatchRun) -> JobMatchRun:
        run.agency_id = self.agency_id
        self.db.add(run)
        self.db.commit()
        self.db.refresh(run)
        return run

    def get_run(self, run_id: uuid.UUID) -> Optional[JobMatchRun]:
        stmt = (
            select(JobMatchRun)
            .where(JobMatchRun.id == run_id, JobMatchRun.agency_id == self.agency_id)
            .options(
                selectinload(JobMatchRun.job),
                selectinload(JobMatchRun.initiator),
            )
        )
        return self.db.scalars(stmt).first()

    def get_latest_run_for_job(self, job_id: uuid.UUID) -> Optional[JobMatchRun]:
        stmt = (
            select(JobMatchRun)
            .where(JobMatchRun.job_id == job_id, JobMatchRun.agency_id == self.agency_id)
            .order_by(desc(JobMatchRun.created_at))
        )
        return self.db.scalars(stmt).first()

    def list_runs_for_job(
        self, job_id: uuid.UUID, skip: int = 0, limit: int = 20
    ) -> Tuple[List[JobMatchRun], int]:
        query = select(JobMatchRun).where(
            JobMatchRun.job_id == job_id, JobMatchRun.agency_id == self.agency_id
        )
        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        paged_stmt = query.order_by(desc(JobMatchRun.created_at)).offset(skip).limit(limit)
        items = list(self.db.scalars(paged_stmt).all())
        return items, total

    # ==========================================
    # Matching Results
    # ==========================================

    def create_result(self, result: JobMatchResult) -> JobMatchResult:
        result.agency_id = self.agency_id
        self.db.add(result)
        self.db.commit()
        self.db.refresh(result)
        return result

    def get_result(self, result_id: uuid.UUID) -> Optional[JobMatchResult]:
        stmt = (
            select(JobMatchResult)
            .where(JobMatchResult.id == result_id, JobMatchResult.agency_id == self.agency_id)
            .options(
                selectinload(JobMatchResult.candidate),
                selectinload(JobMatchResult.job),
                selectinload(JobMatchResult.match_run),
                selectinload(JobMatchResult.evidences),
            )
        )
        return self.db.scalars(stmt).first()

    def get_result_by_candidate(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Optional[JobMatchResult]:
        """Fetch the most recent matching result for a candidate & job."""
        stmt = (
            select(JobMatchResult)
            .where(
                JobMatchResult.job_id == job_id,
                JobMatchResult.candidate_id == candidate_id,
                JobMatchResult.agency_id == self.agency_id,
            )
            .options(
                selectinload(JobMatchResult.candidate),
                selectinload(JobMatchResult.job),
                selectinload(JobMatchResult.match_run),
                selectinload(JobMatchResult.evidences),
            )
            .order_by(desc(JobMatchResult.created_at))
        )
        return self.db.scalars(stmt).first()

    def list_results_for_job(
        self,
        job_id: uuid.UUID,
        min_score: Optional[float] = None,
        search: Optional[str] = None,
        run_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 20,
    ) -> Tuple[List[JobMatchResult], int]:
        query = (
            select(JobMatchResult)
            .join(Candidate, JobMatchResult.candidate_id == Candidate.id)
            .where(
                JobMatchResult.job_id == job_id,
                JobMatchResult.agency_id == self.agency_id,
            )
        )

        if run_id:
            query = query.where(JobMatchResult.match_run_id == run_id)
        else:
            # If no run_id specified, pick results from the latest completed run for this job
            latest_run = self.get_latest_run_for_job(job_id)
            if latest_run:
                query = query.where(JobMatchResult.match_run_id == latest_run.id)

        if min_score is not None:
            query = query.where(JobMatchResult.overall_score >= min_score)

        if search:
            s_term = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Candidate.full_name.ilike(s_term),
                    Candidate.current_title.ilike(s_term),
                    Candidate.current_location.ilike(s_term),
                )
            )

        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        paged_stmt = (
            query.options(selectinload(JobMatchResult.candidate))
            .order_by(desc(JobMatchResult.overall_score))
            .offset(skip)
            .limit(limit)
        )
        items = list(self.db.scalars(paged_stmt).all())
        return items, total

    def list_results_for_run(
        self, run_id: uuid.UUID, skip: int = 0, limit: int = 50
    ) -> Tuple[List[JobMatchResult], int]:
        query = select(JobMatchResult).where(
            JobMatchResult.match_run_id == run_id,
            JobMatchResult.agency_id == self.agency_id,
        )
        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        paged_stmt = (
            query.options(selectinload(JobMatchResult.candidate))
            .order_by(desc(JobMatchResult.overall_score))
            .offset(skip)
            .limit(limit)
        )
        items = list(self.db.scalars(paged_stmt).all())
        return items, total

    def list_candidate_matching_history(
        self, candidate_id: uuid.UUID, limit: int = 20
    ) -> List[JobMatchResult]:
        stmt = (
            select(JobMatchResult)
            .where(
                JobMatchResult.candidate_id == candidate_id,
                JobMatchResult.agency_id == self.agency_id,
            )
            .options(
                selectinload(JobMatchResult.job),
                selectinload(JobMatchResult.match_run),
            )
            .order_by(desc(JobMatchResult.created_at))
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())

    def update_result(self, result: JobMatchResult, updates: dict) -> JobMatchResult:
        for k, v in updates.items():
            if hasattr(result, k):
                setattr(result, k, v)
        self.db.commit()
        self.db.refresh(result)
        return result

    # ==========================================
    # Match Evidence
    # ==========================================

    def create_evidence(self, ev: MatchEvidence) -> MatchEvidence:
        ev.agency_id = self.agency_id
        self.db.add(ev)
        self.db.commit()
        self.db.refresh(ev)
        return ev
