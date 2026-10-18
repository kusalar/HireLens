import uuid
from datetime import datetime
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy import select, func, and_, or_, desc, asc
from sqlalchemy.orm import Session, joinedload
from app.repositories.base import BaseTenantRepository
from app.models.interview import (
    Interview,
    InterviewParticipant,
    InterviewFeedback,
    InterviewHistory,
)
from app.models.application import Application
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.entities import User
from app.models.enums import (
    InterviewStatus,
    InterviewMode,
    InterviewRoundType,
)
from app.models.base import utc_now
from app.core.timezone import get_kolkata_day_bounds


class InterviewRepository(BaseTenantRepository[Interview]):
    def __init__(self, db: Session, agency_id: uuid.UUID):
        super().__init__(Interview, db, agency_id)

    def get_with_details(self, interview_id: uuid.UUID) -> Optional[Interview]:
        """Fetch interview with application, candidate, job, participants, feedbacks eagerly loaded."""
        stmt = (
            select(Interview)
            .options(
                joinedload(Interview.application).joinedload(Application.job),
                joinedload(Interview.application).joinedload(Application.candidate),
                joinedload(Interview.creator),
                joinedload(Interview.participants),
                joinedload(Interview.feedbacks).joinedload(InterviewFeedback.reviewer),
                joinedload(Interview.history).joinedload(InterviewHistory.actor),
            )
            .where(
                Interview.id == interview_id,
                Interview.agency_id == self.agency_id,
            )
        )
        return self.db.scalars(stmt).unique().first()

    def find_interviewer_conflicts(
        self,
        user_id: uuid.UUID,
        start_time: datetime,
        end_time: datetime,
        exclude_interview_id: Optional[uuid.UUID] = None,
    ) -> List[Interview]:
        """Detect if an internal interviewer has an overlapping scheduled or confirmed interview."""
        active_statuses = [
            InterviewStatus.SCHEDULED,
            InterviewStatus.CONFIRMED,
            InterviewStatus.RESCHEDULED,
        ]
        stmt = (
            select(Interview)
            .join(InterviewParticipant, InterviewParticipant.interview_id == Interview.id)
            .where(
                Interview.agency_id == self.agency_id,
                InterviewParticipant.user_id == user_id,
                Interview.status.in_(active_statuses),
                Interview.scheduled_start < end_time,
                Interview.scheduled_end > start_time,
            )
        )
        if exclude_interview_id:
            stmt = stmt.where(Interview.id != exclude_interview_id)

        return list(self.db.scalars(stmt).unique().all())

    def list_interviews(
        self,
        application_id: Optional[uuid.UUID] = None,
        job_id: Optional[uuid.UUID] = None,
        interviewer_id: Optional[uuid.UUID] = None,
        status: Optional[InterviewStatus] = None,
        round_type: Optional[InterviewRoundType] = None,
        interview_mode: Optional[InterviewMode] = None,
        timeframe: Optional[str] = None,  # "upcoming", "past", "today"
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Interview], int, Dict[str, int]]:
        """List interviews with comprehensive filtering, status counts, and eager joins."""
        base_query = (
            select(Interview)
            .join(Application, Interview.application_id == Application.id)
            .join(Candidate, Application.candidate_id == Candidate.id)
            .join(Job, Application.job_id == Job.id)
            .options(
                joinedload(Interview.application).joinedload(Application.job),
                joinedload(Interview.application).joinedload(Application.candidate),
                joinedload(Interview.participants),
                joinedload(Interview.creator),
            )
            .where(Interview.agency_id == self.agency_id)
        )

        # Compute status distribution counts across the agency (or scoped by application/job if given)
        counts_stmt = (
            select(Interview.status, func.count(Interview.id))
            .where(Interview.agency_id == self.agency_id)
        )
        if application_id:
            counts_stmt = counts_stmt.where(Interview.application_id == application_id)
        elif job_id:
            counts_stmt = counts_stmt.join(Application, Interview.application_id == Application.id).where(Application.job_id == job_id)
        counts_stmt = counts_stmt.group_by(Interview.status)

        counts_raw = self.db.execute(counts_stmt).all()
        status_counts: Dict[str, int] = {st.value: 0 for st in InterviewStatus}
        for st, count in counts_raw:
            val = st.value if hasattr(st, "value") else str(st)
            status_counts[val] = count

        # Apply filters
        query = base_query
        if application_id:
            query = query.where(Interview.application_id == application_id)

        if job_id:
            query = query.where(Application.job_id == job_id)

        if status:
            query = query.where(Interview.status == status)

        if round_type:
            query = query.where(Interview.round_type == round_type)

        if interview_mode:
            query = query.where(Interview.interview_mode == interview_mode)

        if interviewer_id:
            query = query.join(
                InterviewParticipant,
                and_(
                    InterviewParticipant.interview_id == Interview.id,
                    InterviewParticipant.user_id == interviewer_id,
                ),
            )

        now = utc_now()
        if timeframe == "upcoming":
            query = query.where(
                Interview.scheduled_end >= now,
                Interview.status.in_([
                    InterviewStatus.SCHEDULED,
                    InterviewStatus.CONFIRMED,
                    InterviewStatus.RESCHEDULED,
                ]),
            )
        elif timeframe == "past":
            query = query.where(
                or_(
                    Interview.scheduled_end < now,
                    Interview.status.in_([
                        InterviewStatus.COMPLETED,
                        InterviewStatus.CANCELLED,
                    ]),
                )
            )
        elif timeframe == "today":
            start_of_day, end_of_day = get_kolkata_day_bounds(now)
            query = query.where(
                Interview.scheduled_start >= start_of_day,
                Interview.scheduled_start <= end_of_day,
            )

        if search:
            s = f"%{search.strip().lower()}%"
            query = query.where(
                or_(
                    func.lower(Interview.title).ilike(s),
                    func.lower(Interview.round_name).ilike(s),
                    func.lower(Candidate.full_name).ilike(s),
                    func.lower(Job.title).ilike(s),
                )
            )

        # Count total
        count_stmt = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_stmt) or 0

        # Sort: upcoming first or most recently scheduled
        order = asc(Interview.scheduled_start) if timeframe == "upcoming" else desc(Interview.scheduled_start)
        results = (
            self.db.scalars(query.order_by(order).offset(skip).limit(limit))
            .unique()
            .all()
        )

        return list(results), total, status_counts

    def list_for_application(self, application_id: uuid.UUID) -> List[Interview]:
        """Fetch all interviews for an application ordered by start time ascending."""
        stmt = (
            select(Interview)
            .options(
                joinedload(Interview.participants),
                joinedload(Interview.feedbacks).joinedload(InterviewFeedback.reviewer),
                joinedload(Interview.creator),
            )
            .where(
                Interview.agency_id == self.agency_id,
                Interview.application_id == application_id,
            )
            .order_by(asc(Interview.scheduled_start))
        )
        return list(self.db.scalars(stmt).unique().all())

    def list_for_recruiter(self, recruiter_id: uuid.UUID) -> List[Interview]:
        """Fetch all interviews where the user is an assigned participant or creator."""
        stmt = (
            select(Interview)
            .outerjoin(InterviewParticipant, InterviewParticipant.interview_id == Interview.id)
            .options(
                joinedload(Interview.application).joinedload(Application.job),
                joinedload(Interview.application).joinedload(Application.candidate),
                joinedload(Interview.participants),
            )
            .where(
                Interview.agency_id == self.agency_id,
                or_(
                    Interview.created_by == recruiter_id,
                    InterviewParticipant.user_id == recruiter_id,
                ),
            )
            .order_by(desc(Interview.scheduled_start))
        )
        return list(self.db.scalars(stmt).unique().all())

    def get_feedback(self, feedback_id: uuid.UUID) -> Optional[InterviewFeedback]:
        """Fetch a specific interview feedback record scoped to tenant."""
        stmt = (
            select(InterviewFeedback)
            .options(joinedload(InterviewFeedback.reviewer))
            .where(
                InterviewFeedback.id == feedback_id,
                InterviewFeedback.agency_id == self.agency_id,
            )
        )
        return self.db.scalars(stmt).first()

    def get_feedbacks_for_interview(self, interview_id: uuid.UUID) -> List[InterviewFeedback]:
        """Fetch all feedbacks for an interview."""
        stmt = (
            select(InterviewFeedback)
            .options(joinedload(InterviewFeedback.reviewer))
            .where(
                InterviewFeedback.agency_id == self.agency_id,
                InterviewFeedback.interview_id == interview_id,
            )
            .order_by(desc(InterviewFeedback.submitted_at))
        )
        return list(self.db.scalars(stmt).all())

    def get_history(self, interview_id: uuid.UUID) -> List[InterviewHistory]:
        """Fetch immutable history for an interview."""
        stmt = (
            select(InterviewHistory)
            .options(joinedload(InterviewHistory.actor))
            .where(
                InterviewHistory.agency_id == self.agency_id,
                InterviewHistory.interview_id == interview_id,
            )
            .order_by(desc(InterviewHistory.created_at))
        )
        return list(self.db.scalars(stmt).all())
