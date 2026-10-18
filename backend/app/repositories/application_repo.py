import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import Session, joinedload
from app.repositories.base import BaseTenantRepository
from app.models.application import Application, ApplicationStageHistory, ApplicationNote
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.entities import User, AuditLog
from app.models.enums import PipelineStageType


class ApplicationRepository(BaseTenantRepository[Application]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(Application, db, agency_id)

    def get_with_details(self, application_id: uuid.UUID) -> Optional[Application]:
        """Fetch application with relationships eagerly loaded, tenant-isolated."""
        stmt = (
            select(Application)
            .options(
                joinedload(Application.job),
                joinedload(Application.candidate),
                joinedload(Application.assigned_recruiter),
                joinedload(Application.stage_history),
                joinedload(Application.notes),
            )
            .where(
                Application.id == application_id,
                Application.agency_id == self.agency_id,
            )
        )
        return self.db.scalars(stmt).unique().first()

    def find_active_by_job_and_candidate(
        self, job_id: uuid.UUID, candidate_id: uuid.UUID
    ) -> Optional[Application]:
        """Find an active (non-archived, non-withdrawn) application for (job_id, candidate_id)."""
        stmt = select(Application).where(
            Application.agency_id == self.agency_id,
            Application.job_id == job_id,
            Application.candidate_id == candidate_id,
            Application.archived_at.is_(None),
            Application.status != PipelineStageType.WITHDRAWN,
        )
        return self.db.scalars(stmt).first()

    def list_for_job(
        self,
        job_id: uuid.UUID,
        status: Optional[PipelineStageType] = None,
        assigned_recruiter_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Application], int, Dict[str, int]]:
        """List applications for a job with filtering, search, and stage distribution counts."""
        base_query = (
            select(Application)
            .join(Candidate, Application.candidate_id == Candidate.id)
            .options(
                joinedload(Application.candidate),
                joinedload(Application.assigned_recruiter),
            )
            .where(
                Application.agency_id == self.agency_id,
                Application.job_id == job_id,
            )
        )

        if not include_archived:
            base_query = base_query.where(Application.archived_at.is_(None))

        # Calculate stage distribution counts for the job (independent of current status filter)
        stage_counts_stmt = (
            select(Application.status, func.count(Application.id))
            .where(
                Application.agency_id == self.agency_id,
                Application.job_id == job_id,
            )
        )
        if not include_archived:
            stage_counts_stmt = stage_counts_stmt.where(Application.archived_at.is_(None))
        stage_counts_stmt = stage_counts_stmt.group_by(Application.status)

        stage_counts_raw = self.db.execute(stage_counts_stmt).all()
        stage_counts: Dict[str, int] = {st.value: 0 for st in PipelineStageType}
        for st, count in stage_counts_raw:
            val = st.value if hasattr(st, "value") else str(st)
            stage_counts[val] = count

        # Apply specific filters
        query = base_query
        if status:
            query = query.where(Application.status == status)

        if assigned_recruiter_id:
            query = query.where(Application.assigned_recruiter_id == assigned_recruiter_id)

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Candidate.full_name).ilike(s),
                    func.lower(Candidate.email).ilike(s),
                    func.lower(Candidate.current_title).ilike(s),
                )
            )

        # Count total filtered items
        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Execute pagination ordered by last_activity_at descending
        results = (
            self.db.scalars(
                query.order_by(desc(Application.last_activity_at)).offset(skip).limit(limit)
            )
            .unique()
            .all()
        )

        return list(results), total, stage_counts

    def list_for_candidate(self, candidate_id: uuid.UUID) -> List[Application]:
        """List all applications for a specific candidate across all jobs in the agency."""
        stmt = (
            select(Application)
            .options(
                joinedload(Application.job),
                joinedload(Application.assigned_recruiter),
            )
            .where(
                Application.agency_id == self.agency_id,
                Application.candidate_id == candidate_id,
            )
            .order_by(desc(Application.applied_at))
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_for_recruiter(self, recruiter_id: uuid.UUID) -> List[Application]:
        """List all active applications assigned to a specific recruiter in the agency."""
        stmt = (
            select(Application)
            .options(
                joinedload(Application.job),
                joinedload(Application.candidate),
            )
            .where(
                Application.agency_id == self.agency_id,
                Application.assigned_recruiter_id == recruiter_id,
                Application.archived_at.is_(None),
            )
            .order_by(desc(Application.last_activity_at))
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_stage_history(self, application_id: uuid.UUID) -> List[ApplicationStageHistory]:
        """Fetch full immutable stage history for an application."""
        stmt = (
            select(ApplicationStageHistory)
            .options(joinedload(ApplicationStageHistory.user))
            .where(
                ApplicationStageHistory.agency_id == self.agency_id,
                ApplicationStageHistory.application_id == application_id,
            )
            .order_by(desc(ApplicationStageHistory.created_at))
        )
        return list(self.db.scalars(stmt).all())

    def get_notes(self, application_id: uuid.UUID) -> List[ApplicationNote]:
        """Fetch notes for an application ordered by creation date descending."""
        stmt = (
            select(ApplicationNote)
            .options(joinedload(ApplicationNote.author))
            .where(
                ApplicationNote.agency_id == self.agency_id,
                ApplicationNote.application_id == application_id,
            )
            .order_by(desc(ApplicationNote.created_at))
        )
        return list(self.db.scalars(stmt).all())

    def get_note(self, note_id: uuid.UUID) -> Optional[ApplicationNote]:
        """Fetch a specific note scoped to tenant."""
        stmt = select(ApplicationNote).where(
            ApplicationNote.id == note_id,
            ApplicationNote.agency_id == self.agency_id,
        )
        return self.db.scalars(stmt).first()

    def get_agency_pipeline_stats(self) -> Dict[str, Any]:
        """Compute active pipeline numbers across all jobs in the agency."""
        # Stage distribution across agency
        stage_counts_stmt = (
            select(Application.status, func.count(Application.id))
            .where(
                Application.agency_id == self.agency_id,
                Application.archived_at.is_(None),
            )
            .group_by(Application.status)
        )
        stage_counts_raw = self.db.execute(stage_counts_stmt).all()
        stage_counts: Dict[str, int] = {st.value: 0 for st in PipelineStageType}
        total_active = 0
        for st, count in stage_counts_raw:
            val = st.value if hasattr(st, "value") else str(st)
            stage_counts[val] = count
            if val not in ("REJECTED", "WITHDRAWN"):
                total_active += count

        # Recent activities from AuditLog
        activity_stmt = (
            select(AuditLog, User.full_name)
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(
                AuditLog.agency_id == self.agency_id,
                AuditLog.resource_type == "application",
            )
            .order_by(desc(AuditLog.created_at))
            .limit(10)
        )
        recent_activities_raw = self.db.execute(activity_stmt).all()
        recent_activities = []
        for log, user_name in recent_activities_raw:
            recent_activities.append(
                {
                    "id": str(log.id),
                    "action": log.action,
                    "resource_id": log.resource_id,
                    "details": log.details,
                    "user_name": user_name or "System Recruiter",
                    "created_at": log.created_at.isoformat(),
                }
            )

        # Per-job pipeline breakdown
        jobs_stmt = (
            select(Job.id, Job.title, Job.status, func.count(Application.id))
            .outerjoin(
                Application,
                and_(
                    Application.job_id == Job.id,
                    Application.agency_id == self.agency_id,
                    Application.archived_at.is_(None),
                ),
            )
            .where(Job.agency_id == self.agency_id)
            .group_by(Job.id, Job.title, Job.status)
            .order_by(desc(func.count(Application.id)))
            .limit(15)
        )
        jobs_raw = self.db.execute(jobs_stmt).all()
        job_summaries = []
        for j_id, j_title, j_status, app_count in jobs_raw:
            job_summaries.append(
                {
                    "job_id": str(j_id),
                    "job_title": j_title,
                    "job_status": j_status.value if hasattr(j_status, "value") else str(j_status),
                    "active_applications_count": app_count,
                }
            )

        return {
            "total_active_applications": total_active,
            "stage_counts": stage_counts,
            "recent_activities": recent_activities,
            "job_summaries": job_summaries,
        }
