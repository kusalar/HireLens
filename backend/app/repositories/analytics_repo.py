import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy import select, func, and_, or_, distinct, case, text, desc
from sqlalchemy.orm import Session
import statistics

from app.models.job import Job
from app.models.candidate import Candidate
from app.models.application import Application, ApplicationStageHistory
from app.models.interview import Interview, InterviewParticipant
from app.models.entities import User
from app.models.enums import (
    JobStatus,
    CandidateProfileStatus,
    PipelineStageType,
    InterviewStatus,
    UserRole,
)
from app.core.timezone import DEFAULT_ZONEINFO, convert_utc_to_timezone


class AnalyticsRepository:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id

    # ------------------------------------------------------------------
    # 1. Overview Metrics
    # ------------------------------------------------------------------
    def get_overview_metrics(
        self,
        start_utc: datetime,
        end_utc: datetime,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        # Total active jobs (agency-scoped)
        active_jobs_stmt = select(func.count(Job.id)).where(
            Job.agency_id == self.agency_id,
            Job.status == JobStatus.ACTIVE,
        )
        if job_id:
            active_jobs_stmt = active_jobs_stmt.where(Job.id == job_id)
        total_active_jobs = self.db.scalar(active_jobs_stmt) or 0

        # Total active candidates (agency-scoped)
        candidates_stmt = select(func.count(Candidate.id)).where(
            Candidate.agency_id == self.agency_id,
            Candidate.profile_status == CandidateProfileStatus.ACTIVE,
        )
        total_candidates = self.db.scalar(candidates_stmt) or 0

        # Applications filters
        app_filters = [
            Application.agency_id == self.agency_id,
            Application.archived_at.is_(None),
        ]
        if job_id:
            app_filters.append(Application.job_id == job_id)
        if recruiter_id:
            app_filters.append(Application.assigned_recruiter_id == recruiter_id)
        if source:
            app_filters.append(Application.source == source)

        # Total applications overall
        total_apps_stmt = select(func.count(Application.id)).where(and_(*app_filters))
        total_applications = self.db.scalar(total_apps_stmt) or 0

        # Applications received in period
        period_app_filters = list(app_filters) + [
            Application.applied_at >= start_utc,
            Application.applied_at <= end_utc,
        ]
        period_apps_stmt = select(func.count(Application.id)).where(and_(*period_app_filters))
        applications_in_period = self.db.scalar(period_apps_stmt) or 0

        # Active applications (not terminal: SELECTED, REJECTED, WITHDRAWN)
        active_app_filters = list(app_filters) + [
            ~Application.status.in_([
                PipelineStageType.SELECTED,
                PipelineStageType.REJECTED,
                PipelineStageType.WITHDRAWN,
            ])
        ]
        active_apps_stmt = select(func.count(Application.id)).where(and_(*active_app_filters))
        active_applications = self.db.scalar(active_apps_stmt) or 0

        # Successful hires in period: applications that transitioned to SELECTED in period
        hires_subq = (
            select(ApplicationStageHistory.application_id).distinct()
            .join(Application, Application.id == ApplicationStageHistory.application_id)
            .where(
                ApplicationStageHistory.agency_id == self.agency_id,
                ApplicationStageHistory.new_stage == PipelineStageType.SELECTED,
                ApplicationStageHistory.created_at >= start_utc,
                ApplicationStageHistory.created_at <= end_utc,
                Application.archived_at.is_(None),
            )
        )
        if job_id:
            hires_subq = hires_subq.where(Application.job_id == job_id)
        if recruiter_id:
            hires_subq = hires_subq.where(Application.assigned_recruiter_id == recruiter_id)
        if source:
            hires_subq = hires_subq.where(Application.source == source)

        successful_hires = self.db.scalar(select(func.count()).select_from(hires_subq.subquery())) or 0

        # If no history transitions in period, fallback to current status == SELECTED within applied_at period
        if successful_hires == 0:
            current_selected_filters = list(app_filters) + [
                Application.status == PipelineStageType.SELECTED,
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            ]
            successful_hires = self.db.scalar(
                select(func.count(Application.id)).where(and_(*current_selected_filters))
            ) or 0

        # Interviews scheduled in period
        interview_filters = [
            Interview.agency_id == self.agency_id,
            Interview.scheduled_start >= start_utc,
            Interview.scheduled_start <= end_utc,
            Interview.status.in_([
                InterviewStatus.SCHEDULED,
                InterviewStatus.CONFIRMED,
                InterviewStatus.COMPLETED,
            ]),
        ]
        if job_id or recruiter_id or source:
            interview_filters.append(Interview.application_id == Application.id)
            if job_id:
                interview_filters.append(Application.job_id == job_id)
            if recruiter_id:
                interview_filters.append(Application.assigned_recruiter_id == recruiter_id)
            if source:
                interview_filters.append(Application.source == source)
            interviews_scheduled_stmt = (
                select(func.count(distinct(Interview.id)))
                .select_from(Interview)
                .join(Application, Application.id == Interview.application_id)
                .where(and_(*interview_filters))
            )
        else:
            interviews_scheduled_stmt = select(func.count(Interview.id)).where(and_(*interview_filters))

        interviews_scheduled = self.db.scalar(interviews_scheduled_stmt) or 0

        # Completed interviews in period
        completed_filters = [
            Interview.agency_id == self.agency_id,
            Interview.status == InterviewStatus.COMPLETED,
            or_(
                and_(Interview.completed_at >= start_utc, Interview.completed_at <= end_utc),
                and_(
                    Interview.completed_at.is_(None),
                    Interview.scheduled_start >= start_utc,
                    Interview.scheduled_start <= end_utc,
                ),
            ),
        ]
        if job_id or recruiter_id or source:
            if job_id:
                completed_filters.append(Application.job_id == job_id)
            if recruiter_id:
                completed_filters.append(Application.assigned_recruiter_id == recruiter_id)
            if source:
                completed_filters.append(Application.source == source)
            interviews_completed_stmt = (
                select(func.count(distinct(Interview.id)))
                .select_from(Interview)
                .join(Application, Application.id == Interview.application_id)
                .where(and_(*completed_filters))
            )
        else:
            interviews_completed_stmt = select(func.count(Interview.id)).where(and_(*completed_filters))

        interviews_completed = self.db.scalar(interviews_completed_stmt) or 0

        return {
            "total_active_jobs": total_active_jobs,
            "total_candidates": total_candidates,
            "total_applications": total_applications,
            "applications_in_period": applications_in_period,
            "interviews_scheduled": interviews_scheduled,
            "interviews_completed": interviews_completed,
            "active_applications": active_applications,
            "successful_hires": successful_hires,
        }

    # ------------------------------------------------------------------
    # 2. Recruitment Funnel Metrics
    # ------------------------------------------------------------------
    def get_funnel_metrics(
        self,
        start_utc: datetime,
        end_utc: datetime,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
        source: Optional[str] = None,
    ) -> Dict[str, Any]:
        stages = [
            (PipelineStageType.APPLIED, "Applied"),
            (PipelineStageType.UNDER_REVIEW, "Screening / Review"),
            (PipelineStageType.SHORTLISTED, "Shortlisted"),
            (PipelineStageType.INTERVIEW, "Interview"),
            (PipelineStageType.SELECTED, "Hired (Selected)"),
            (PipelineStageType.REJECTED, "Rejected"),
            (PipelineStageType.WITHDRAWN, "Withdrawn"),
        ]

        app_base = [
            Application.agency_id == self.agency_id,
            Application.archived_at.is_(None),
        ]
        if job_id:
            app_base.append(Application.job_id == job_id)
        if recruiter_id:
            app_base.append(Application.assigned_recruiter_id == recruiter_id)
        if source:
            app_base.append(Application.source == source)

        # 1. Current distribution by stage
        current_counts_stmt = (
            select(Application.status, func.count(Application.id))
            .where(and_(*app_base))
            .group_by(Application.status)
        )
        current_map = dict(self.db.execute(current_counts_stmt).all())

        # 2. Historical entries into stage during period
        history_filters = [
            ApplicationStageHistory.agency_id == self.agency_id,
            ApplicationStageHistory.created_at >= start_utc,
            ApplicationStageHistory.created_at <= end_utc,
            Application.archived_at.is_(None),
        ]
        if job_id:
            history_filters.append(Application.job_id == job_id)
        if recruiter_id:
            history_filters.append(Application.assigned_recruiter_id == recruiter_id)
        if source:
            history_filters.append(Application.source == source)

        entered_counts_stmt = (
            select(
                ApplicationStageHistory.new_stage,
                func.count(distinct(ApplicationStageHistory.application_id)),
            )
            .join(Application, Application.id == ApplicationStageHistory.application_id)
            .where(and_(*history_filters))
            .group_by(ApplicationStageHistory.new_stage)
        )
        entered_map = dict(self.db.execute(entered_counts_stmt).all())

        # If applied entered count from history is zero (legacy apps), fallback to applied_at count
        applied_period_stmt = (
            select(func.count(Application.id))
            .where(
                and_(*app_base),
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            )
        )
        applied_period_count = self.db.scalar(applied_period_stmt) or 0
        if entered_map.get(PipelineStageType.APPLIED, 0) < applied_period_count:
            entered_map[PipelineStageType.APPLIED] = applied_period_count

        # 3. Drop-offs: transitions to REJECTED or WITHDRAWN from previous stage
        drop_off_stmt = (
            select(
                ApplicationStageHistory.previous_stage,
                func.count(distinct(ApplicationStageHistory.application_id)),
            )
            .join(Application, Application.id == ApplicationStageHistory.application_id)
            .where(
                and_(*history_filters),
                ApplicationStageHistory.new_stage.in_([
                    PipelineStageType.REJECTED,
                    PipelineStageType.WITHDRAWN,
                ]),
                ApplicationStageHistory.previous_stage.is_not(None),
            )
            .group_by(ApplicationStageHistory.previous_stage)
        )
        drop_off_map = dict(self.db.execute(drop_off_stmt).all())

        # Build funnel list
        funnel_items = []
        applied_count = entered_map.get(PipelineStageType.APPLIED, 0)
        prev_count = None

        main_funnel_stages = [
            (PipelineStageType.APPLIED, "Applied"),
            (PipelineStageType.UNDER_REVIEW, "Screening / Review"),
            (PipelineStageType.SHORTLISTED, "Shortlisted"),
            (PipelineStageType.INTERVIEW, "Interview"),
            (PipelineStageType.SELECTED, "Hired (Selected)"),
            (PipelineStageType.REJECTED, "Rejected"),
            (PipelineStageType.WITHDRAWN, "Withdrawn"),
        ]

        for stage_enum, label in main_funnel_stages:
            cur = current_map.get(stage_enum, 0)
            entered = entered_map.get(stage_enum, 0)
            drop = drop_off_map.get(stage_enum, 0)

            conv_prev = None
            if prev_count is not None and prev_count > 0:
                conv_prev = round((entered / prev_count) * 100, 2)

            conv_applied = None
            if applied_count > 0:
                conv_applied = round((entered / applied_count) * 100, 2)

            # Update prev_count for next sequential stage (only among progressive hiring stages)
            if stage_enum in [
                PipelineStageType.APPLIED,
                PipelineStageType.UNDER_REVIEW,
                PipelineStageType.SHORTLISTED,
                PipelineStageType.INTERVIEW,
            ]:
                prev_count = entered if entered > 0 else cur

            funnel_items.append({
                "stage": stage_enum.value,
                "label": label,
                "current_count": cur,
                "entered_count": entered,
                "drop_off_count": drop,
                "conversion_from_previous_percent": conv_prev,
                "conversion_from_applied_percent": conv_applied,
            })

        hired_count = entered_map.get(PipelineStageType.SELECTED, 0)
        overall_conversion = round((hired_count / applied_count) * 100, 2) if applied_count > 0 else 0.0

        return {
            "stages": funnel_items,
            "overall_application_to_hire_rate": overall_conversion,
            "total_applications_evaluated": applied_count,
            "funnel_methodology": (
                "Calculated using ApplicationStageHistory transitions during the reporting period. "
                "Current counts reflect live application states; entered counts reflect candidates who traversed "
                "into that stage during the period. Drop-offs represent exits to Rejected or Withdrawn."
            ),
        }

    # ------------------------------------------------------------------
    # 3. Hiring Performance & Time-To-Hire
    # ------------------------------------------------------------------
    def get_hiring_performance_metrics(
        self,
        start_utc: datetime,
        end_utc: datetime,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        # Query hired journeys
        history_stmt = (
            select(
                Application.id,
                Application.applied_at,
                func.min(ApplicationStageHistory.created_at).label("hired_at"),
            )
            .join(ApplicationStageHistory, ApplicationStageHistory.application_id == Application.id)
            .where(
                Application.agency_id == self.agency_id,
                ApplicationStageHistory.new_stage == PipelineStageType.SELECTED,
                ApplicationStageHistory.created_at >= start_utc,
                ApplicationStageHistory.created_at <= end_utc,
            )
        )
        if job_id:
            history_stmt = history_stmt.where(Application.job_id == job_id)
        if recruiter_id:
            history_stmt = history_stmt.where(Application.assigned_recruiter_id == recruiter_id)

        history_stmt = history_stmt.group_by(Application.id, Application.applied_at)
        hired_rows = self.db.execute(history_stmt).all()

        durations_days: List[float] = []
        for row in hired_rows:
            applied_at = row.applied_at
            hired_at = row.hired_at
            if applied_at and hired_at:
                diff = (hired_at - applied_at).total_seconds() / 86400.0
                if diff >= 0:
                    durations_days.append(round(diff, 2))

        avg_days = round(statistics.mean(durations_days), 2) if durations_days else None
        med_days = round(statistics.median(durations_days), 2) if durations_days else None
        min_days = min(durations_days) if durations_days else None
        max_days = max(durations_days) if durations_days else None

        # Interview conversion stats
        app_filters = [
            Application.agency_id == self.agency_id,
            Application.archived_at.is_(None),
            Application.applied_at >= start_utc,
            Application.applied_at <= end_utc,
        ]
        if job_id:
            app_filters.append(Application.job_id == job_id)
        if recruiter_id:
            app_filters.append(Application.assigned_recruiter_id == recruiter_id)

        total_apps = self.db.scalar(select(func.count(Application.id)).where(and_(*app_filters))) or 0

        # Applications with interviews
        apps_with_interviews_subq = (
            select(Interview.application_id).distinct()
            .join(Application, Application.id == Interview.application_id)
            .where(
                and_(*app_filters),
                Interview.status != InterviewStatus.CANCELLED,
            )
        )
        apps_with_interviews = self.db.scalar(select(func.count()).select_from(apps_with_interviews_subq.subquery())) or 0

        # Total completed interviews
        completed_interviews_stmt = (
            select(func.count(Interview.id))
            .join(Application, Application.id == Interview.application_id)
            .where(
                and_(*app_filters),
                Interview.status == InterviewStatus.COMPLETED,
            )
        )
        total_completed = self.db.scalar(completed_interviews_stmt) or 0

        # Cancelled interviews
        cancelled_interviews_stmt = (
            select(func.count(Interview.id))
            .join(Application, Application.id == Interview.application_id)
            .where(
                and_(*app_filters),
                Interview.status == InterviewStatus.CANCELLED,
            )
        )
        cancelled_interviews_count = self.db.scalar(cancelled_interviews_stmt) or 0

        # Interview to hire: applications with interviews that reached SELECTED
        interviewed_hires_subq = (
            select(Application.id).distinct()
            .join(Interview, Interview.application_id == Application.id)
            .where(
                and_(*app_filters),
                Interview.status == InterviewStatus.COMPLETED,
                Application.status == PipelineStageType.SELECTED,
            )
        )
        interview_to_hire_count = self.db.scalar(select(func.count()).select_from(interviewed_hires_subq.subquery())) or 0
        interview_to_hire_rate = (
            round((interview_to_hire_count / apps_with_interviews) * 100, 2)
            if apps_with_interviews > 0
            else 0.0
        )
        interviews_per_app = round(total_completed / total_apps, 2) if total_apps > 0 else 0.0

        return {
            "time_to_hire": {
                "average_days": avg_days,
                "median_days": med_days,
                "min_days": min_days,
                "max_days": max_days,
                "hired_sample_size": len(durations_days),
                "calculation_notes": (
                    "Time-to-hire represents calendar days between application submission and the earliest "
                    "transition to the SELECTED stage in ApplicationStageHistory. Incomplete journeys and invalid "
                    "timestamps are strictly excluded."
                ),
            },
            "interview_conversion": {
                "total_applications_considered": total_apps,
                "total_interviews_conducted": total_completed,
                "interviews_per_application": interviews_per_app,
                "applications_with_interviews": apps_with_interviews,
                "interview_to_hire_count": interview_to_hire_count,
                "interview_to_hire_rate": interview_to_hire_rate,
                "cancelled_interviews_excluded": cancelled_interviews_count,
            },
        }

    # ------------------------------------------------------------------
    # 4. Job Analytics
    # ------------------------------------------------------------------
    def get_job_performance_metrics(
        self,
        start_utc: datetime,
        end_utc: datetime,
        department: Optional[str] = None,
    ) -> Dict[str, Any]:
        job_filters = [Job.agency_id == self.agency_id]
        if department:
            job_filters.append(Job.department == department)

        jobs_stmt = select(Job).where(and_(*job_filters)).order_by(desc(Job.created_at))
        jobs = list(self.db.scalars(jobs_stmt).all())

        results = []
        zero_applicant_jobs = 0

        for job in jobs:
            # Applications count in period
            app_stmt = select(func.count(Application.id)).where(
                Application.agency_id == self.agency_id,
                Application.job_id == job.id,
                Application.archived_at.is_(None),
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            )
            app_count = self.db.scalar(app_stmt) or 0
            if app_count == 0:
                zero_applicant_jobs += 1

            # Interviews count
            interview_stmt = (
                select(func.count(Interview.id))
                .join(Application, Application.id == Interview.application_id)
                .where(
                    Application.agency_id == self.agency_id,
                    Application.job_id == job.id,
                    Interview.status == InterviewStatus.COMPLETED,
                    Interview.scheduled_start >= start_utc,
                    Interview.scheduled_start <= end_utc,
                )
            )
            int_count = self.db.scalar(interview_stmt) or 0

            # Hires count
            hires_stmt = select(func.count(Application.id)).where(
                Application.agency_id == self.agency_id,
                Application.job_id == job.id,
                Application.status == PipelineStageType.SELECTED,
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            )
            hires_count = self.db.scalar(hires_stmt) or 0
            conv_rate = round((hires_count / app_count) * 100, 2) if app_count > 0 else 0.0

            results.append({
                "job_id": job.id,
                "job_title": job.title,
                "department": job.department,
                "status": job.status.value,
                "applications_count": app_count,
                "interviews_count": int_count,
                "hires_count": hires_count,
                "conversion_rate": conv_rate,
                "created_at": job.created_at,
            })

        return {
            "total_jobs_evaluated": len(jobs),
            "jobs_with_zero_applications": zero_applicant_jobs,
            "jobs": results,
        }

    # ------------------------------------------------------------------
    # 5. Recruiter Analytics
    # ------------------------------------------------------------------
    def get_recruiter_performance_metrics(
        self,
        start_utc: datetime,
        end_utc: datetime,
    ) -> List[Dict[str, Any]]:
        # Get recruiters belonging to agency
        users_stmt = select(User).where(
            User.agency_id == self.agency_id,
            User.role.in_([UserRole.RECRUITER, UserRole.ADMIN, UserRole.OWNER]),
            User.is_active.is_(True),
        ).order_by(User.full_name)
        users = list(self.db.scalars(users_stmt).all())

        results = []
        for user in users:
            # Applications handled in period
            app_stmt = select(func.count(Application.id)).where(
                Application.agency_id == self.agency_id,
                Application.assigned_recruiter_id == user.id,
                Application.archived_at.is_(None),
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            )
            handled = self.db.scalar(app_stmt) or 0

            # Active workload (current live applications)
            workload_stmt = select(func.count(Application.id)).where(
                Application.agency_id == self.agency_id,
                Application.assigned_recruiter_id == user.id,
                Application.archived_at.is_(None),
                ~Application.status.in_([
                    PipelineStageType.SELECTED,
                    PipelineStageType.REJECTED,
                    PipelineStageType.WITHDRAWN,
                ]),
            )
            workload = self.db.scalar(workload_stmt) or 0

            # Interviews coordinated (created_by or participant)
            coord_stmt = select(func.count(distinct(Interview.id))).where(
                Interview.agency_id == self.agency_id,
                or_(
                    Interview.created_by == user.id,
                    Interview.id.in_(
                        select(InterviewParticipant.interview_id).where(
                            InterviewParticipant.user_id == user.id
                        )
                    ),
                ),
                Interview.status != InterviewStatus.CANCELLED,
                Interview.scheduled_start >= start_utc,
                Interview.scheduled_start <= end_utc,
            )
            interviews_coord = self.db.scalar(coord_stmt) or 0

            # Attributable hires
            hires_stmt = select(func.count(Application.id)).where(
                Application.agency_id == self.agency_id,
                Application.assigned_recruiter_id == user.id,
                Application.status == PipelineStageType.SELECTED,
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            )
            hires = self.db.scalar(hires_stmt) or 0

            # Recruiter-specific time to hire
            time_stmt = (
                select(
                    Application.applied_at,
                    func.min(ApplicationStageHistory.created_at).label("hired_at"),
                )
                .join(ApplicationStageHistory, ApplicationStageHistory.application_id == Application.id)
                .where(
                    Application.agency_id == self.agency_id,
                    Application.assigned_recruiter_id == user.id,
                    ApplicationStageHistory.new_stage == PipelineStageType.SELECTED,
                    ApplicationStageHistory.created_at >= start_utc,
                    ApplicationStageHistory.created_at <= end_utc,
                )
                .group_by(Application.id, Application.applied_at)
            )
            time_rows = self.db.execute(time_stmt).all()
            rec_durations = [
                (r.hired_at - r.applied_at).total_seconds() / 86400.0
                for r in time_rows
                if r.applied_at and r.hired_at and (r.hired_at - r.applied_at).total_seconds() >= 0
            ]
            avg_tth = round(statistics.mean(rec_durations), 2) if rec_durations else None

            results.append({
                "recruiter_id": user.id,
                "recruiter_name": user.full_name,
                "recruiter_email": user.email,
                "role": user.role.value,
                "applications_handled": handled,
                "active_workload": workload,
                "interviews_coordinated": interviews_coord,
                "attributable_hires": hires,
                "avg_time_to_hire_days": avg_tth,
            })

        return results

    # ------------------------------------------------------------------
    # 6. Candidate Source Analytics
    # ------------------------------------------------------------------
    def get_source_performance_metrics(
        self,
        start_utc: datetime,
        end_utc: datetime,
        job_id: Optional[uuid.UUID] = None,
    ) -> Dict[str, Any]:
        # Count unattributed
        unattr_cand_stmt = select(func.count(Candidate.id)).where(
            Candidate.agency_id == self.agency_id,
            or_(Candidate.source.is_(None), Candidate.source == ""),
        )
        unattributed_candidates = self.db.scalar(unattr_cand_stmt) or 0

        unattr_app_stmt = select(func.count(Application.id)).where(
            Application.agency_id == self.agency_id,
            Application.archived_at.is_(None),
            or_(Application.source.is_(None), Application.source == ""),
        )
        if job_id:
            unattr_app_stmt = unattr_app_stmt.where(Application.job_id == job_id)
        unattributed_applications = self.db.scalar(unattr_app_stmt) or 0

        # Query sources from applications in period
        app_source_filters = [
            Application.agency_id == self.agency_id,
            Application.archived_at.is_(None),
            Application.applied_at >= start_utc,
            Application.applied_at <= end_utc,
        ]
        if job_id:
            app_source_filters.append(Application.job_id == job_id)

        app_source_stmt = (
            select(
                func.coalesce(func.nullif(Application.source, ''), 'Unattributed').label("src"),
                func.count(Application.id).label("apps_cnt"),
                func.sum(case((Application.status == PipelineStageType.SELECTED, 1), else_=0)).label("hires_cnt"),
            )
            .where(and_(*app_source_filters))
            .group_by("src")
        )
        app_source_rows = self.db.execute(app_source_stmt).all()

        source_map: Dict[str, Dict[str, Any]] = {}
        for row in app_source_rows:
            src_name = row.src
            apps_c = row.apps_cnt or 0
            hires_c = int(row.hires_cnt or 0)
            source_map[src_name] = {
                "source": src_name,
                "candidates_count": 0,
                "applications_count": apps_c,
                "interviews_count": 0,
                "hires_count": hires_c,
                "conversion_rate": round((hires_c / apps_c) * 100, 2) if apps_c > 0 else 0.0,
            }

        # Query candidates by source created in agency
        cand_source_stmt = (
            select(
                func.coalesce(func.nullif(Candidate.source, ''), 'Unattributed').label("src"),
                func.count(Candidate.id).label("cands_cnt"),
            )
            .where(
                Candidate.agency_id == self.agency_id,
                Candidate.created_at >= start_utc,
                Candidate.created_at <= end_utc,
            )
            .group_by("src")
        )
        cand_rows = self.db.execute(cand_source_stmt).all()
        for row in cand_rows:
            src_name = row.src
            if src_name not in source_map:
                source_map[src_name] = {
                    "source": src_name,
                    "candidates_count": row.cands_cnt,
                    "applications_count": 0,
                    "interviews_count": 0,
                    "hires_count": 0,
                    "conversion_rate": 0.0,
                }
            else:
                source_map[src_name]["candidates_count"] = row.cands_cnt

        # Query interviews by application source
        interview_source_stmt = (
            select(
                func.coalesce(func.nullif(Application.source, ''), 'Unattributed').label("src"),
                func.count(distinct(Interview.id)).label("int_cnt"),
            )
            .join(Application, Application.id == Interview.application_id)
            .where(
                and_(*app_source_filters),
                Interview.status == InterviewStatus.COMPLETED,
            )
            .group_by("src")
        )
        interview_rows = self.db.execute(interview_source_stmt).all()
        for row in interview_rows:
            src_name = row.src
            if src_name in source_map:
                source_map[src_name]["interviews_count"] = row.int_cnt

        sorted_sources = sorted(
            source_map.values(),
            key=lambda x: (x["hires_count"], x["applications_count"]),
            reverse=True,
        )

        return {
            "sources": sorted_sources,
            "unattributed_candidates_count": unattributed_candidates,
            "unattributed_applications_count": unattributed_applications,
            "attribution_notes": (
                "Candidate and application sources reflect actual recorded attribution. "
                "Historical records lacking source data are strictly marked as 'Unattributed' to maintain honest reporting."
            ),
        }

    # ------------------------------------------------------------------
    # 7. Trends Time-Series Data
    # ------------------------------------------------------------------
    def get_trends_data(
        self,
        start_utc: datetime,
        end_utc: datetime,
        job_id: Optional[uuid.UUID] = None,
        recruiter_id: Optional[uuid.UUID] = None,
    ) -> List[Dict[str, Any]]:
        # Calculate daily intervals in Asia/Kolkata
        start_ist = convert_utc_to_timezone(start_utc, "Asia/Kolkata")
        end_ist = convert_utc_to_timezone(end_utc, "Asia/Kolkata")

        # Map each calendar day in period
        days_map: Dict[str, Dict[str, int]] = {}
        curr = start_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        end_day = end_ist.replace(hour=23, minute=59, second=59, microsecond=999999)

        while curr <= end_day:
            day_str = curr.strftime("%Y-%m-%d")
            days_map[day_str] = {
                "date": day_str,
                "applications": 0,
                "interviews_scheduled": 0,
                "interviews_completed": 0,
                "hires": 0,
            }
            curr += timedelta(days=1)

        # 1. Applications per day
        app_stmt = (
            select(Application.applied_at)
            .where(
                Application.agency_id == self.agency_id,
                Application.archived_at.is_(None),
                Application.applied_at >= start_utc,
                Application.applied_at <= end_utc,
            )
        )
        if job_id:
            app_stmt = app_stmt.where(Application.job_id == job_id)
        if recruiter_id:
            app_stmt = app_stmt.where(Application.assigned_recruiter_id == recruiter_id)

        app_rows = self.db.execute(app_stmt).all()
        for r in app_rows:
            if r.applied_at:
                ist_date = convert_utc_to_timezone(r.applied_at, "Asia/Kolkata").strftime("%Y-%m-%d")
                if ist_date in days_map:
                    days_map[ist_date]["applications"] += 1

        # 2. Interviews scheduled & completed
        int_stmt = (
            select(
                Interview.scheduled_start,
                Interview.completed_at,
                Interview.status,
            )
            .where(
                Interview.agency_id == self.agency_id,
                Interview.scheduled_start >= start_utc,
                Interview.scheduled_start <= end_utc,
            )
        )
        if job_id or recruiter_id:
            int_stmt = int_stmt.join(Application, Application.id == Interview.application_id)
            if job_id:
                int_stmt = int_stmt.where(Application.job_id == job_id)
            if recruiter_id:
                int_stmt = int_stmt.where(Application.assigned_recruiter_id == recruiter_id)

        int_rows = self.db.execute(int_stmt).all()
        for r in int_rows:
            if r.scheduled_start:
                ist_date = convert_utc_to_timezone(r.scheduled_start, "Asia/Kolkata").strftime("%Y-%m-%d")
                if ist_date in days_map:
                    days_map[ist_date]["interviews_scheduled"] += 1
            if r.status == InterviewStatus.COMPLETED:
                target_dt = r.completed_at or r.scheduled_start
                if target_dt:
                    comp_date = convert_utc_to_timezone(target_dt, "Asia/Kolkata").strftime("%Y-%m-%d")
                    if comp_date in days_map:
                        days_map[comp_date]["interviews_completed"] += 1

        # 3. Hires per day
        hires_stmt = (
            select(ApplicationStageHistory.created_at)
            .join(Application, Application.id == ApplicationStageHistory.application_id)
            .where(
                ApplicationStageHistory.agency_id == self.agency_id,
                ApplicationStageHistory.new_stage == PipelineStageType.SELECTED,
                ApplicationStageHistory.created_at >= start_utc,
                ApplicationStageHistory.created_at <= end_utc,
            )
        )
        if job_id:
            hires_stmt = hires_stmt.where(Application.job_id == job_id)
        if recruiter_id:
            hires_stmt = hires_stmt.where(Application.assigned_recruiter_id == recruiter_id)

        hire_rows = self.db.execute(hires_stmt).all()
        for r in hire_rows:
            if r.created_at:
                ist_date = convert_utc_to_timezone(r.created_at, "Asia/Kolkata").strftime("%Y-%m-%d")
                if ist_date in days_map:
                    days_map[ist_date]["hires"] += 1

        return sorted(days_map.values(), key=lambda x: x["date"])
