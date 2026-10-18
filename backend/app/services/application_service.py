import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, update
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.application import Application, ApplicationStageHistory, ApplicationNote
from app.models.job import Job, JobRequirement
from app.models.candidate import Candidate
from app.models.entities import User, AuditLog
from app.models.matching import JobMatchResult, MatchEvidence
from app.models.enums import PipelineStageType, UserRole
from app.models.base import utc_now
from app.repositories.application_repo import ApplicationRepository
from app.repositories.job_repo import JobRepository
from app.repositories.candidate_repo import CandidateRepository
from app.schemas.application import (
    ApplicationCreate,
    ApplicationUpdate,
    ApplicationStageTransition,
    ApplicationRead,
    ApplicationListResponse,
    ApplicationDetailRead,
    ApplicationStageHistoryRead,
    ApplicationNoteCreate,
    ApplicationNoteUpdate,
    ApplicationNoteRead,
    ApplicationActivityRead,
    CandidateComparisonItem,
    CandidateComparisonResponse,
    PipelineDashboardStats,
)
from app.schemas.job import JobRead
from app.schemas.candidate import CandidateRead
from app.schemas.matching import JobMatchResultRead, MatchEvidenceRead


class ApplicationService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = ApplicationRepository(db, agency_id)
        self.job_repo = JobRepository(db, agency_id)
        self.cand_repo = CandidateRepository(db, agency_id)

    def _resolve_application_read(
        self,
        app: Application,
        candidate: Optional[Candidate] = None,
        job: Optional[Job] = None,
        recruiter: Optional[User] = None,
        latest_match: Optional[JobMatchResult] = None,
    ) -> ApplicationRead:
        """Helper to project Application ORM model to ApplicationRead with resolved denormalized fields."""
        cand = candidate or app.candidate
        jb = job or app.job
        rec = recruiter or app.assigned_recruiter

        # Fetch match result if not provided
        if latest_match is None:
            latest_match = (
                self.db.scalars(
                    select(JobMatchResult)
                    .where(
                        JobMatchResult.agency_id == self.agency_id,
                        JobMatchResult.job_id == app.job_id,
                        JobMatchResult.candidate_id == app.candidate_id,
                    )
                    .order_by(desc(JobMatchResult.created_at))
                )
                .first()
            )

        is_stale = False
        latest_score = None
        if latest_match:
            latest_score = latest_match.overall_score
            # Check staleness: if job or candidate updated after match result or status STALE
            cand_updated = cand.updated_at if cand else None
            job_updated = jb.updated_at if jb else None
            match_created = latest_match.created_at
            if latest_match.status == "STALE":
                is_stale = True
            elif cand_updated and cand_updated > match_created:
                is_stale = True
            elif job_updated and job_updated > match_created:
                is_stale = True

        return ApplicationRead(
            id=app.id,
            agency_id=app.agency_id,
            job_id=app.job_id,
            candidate_id=app.candidate_id,
            status=app.status,
            source=app.source,
            applied_at=app.applied_at,
            shortlisted_at=app.shortlisted_at,
            last_activity_at=app.last_activity_at,
            assigned_recruiter_id=app.assigned_recruiter_id,
            assigned_recruiter_name=rec.full_name if rec else None,
            recruiter_summary=app.recruiter_summary,
            archived_at=app.archived_at,
            created_at=app.created_at,
            updated_at=app.updated_at,
            candidate_name=cand.full_name if cand else "Unknown",
            candidate_title=cand.current_title if cand else None,
            candidate_email=cand.email if cand else None,
            candidate_location=cand.current_location if cand else None,
            total_experience_months=cand.total_experience_months if cand else 0,
            job_title=jb.title if jb else "Unknown Position",
            latest_match_score=latest_score,
            is_stale_match=is_stale,
        )

    def create_application(
        self, job_id: uuid.UUID, current_user: User, data: ApplicationCreate
    ) -> ApplicationRead:
        # 1. Enforce Job tenant ownership
        job = self.job_repo.get(job_id)
        if not job or job.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job opening not found or does not belong to your agency.",
            )

        # 2. Enforce Candidate tenant ownership
        candidate = self.cand_repo.get(data.candidate_id)
        if not candidate or candidate.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate master profile not found or does not belong to your agency.",
            )

        # 3. Enforce Recruiter tenant ownership if assigned
        assigned_recruiter = None
        if data.assigned_recruiter_id:
            assigned_recruiter = self.db.scalars(
                select(User).where(
                    User.id == data.assigned_recruiter_id,
                    User.agency_id == self.agency_id,
                )
            ).first()
            if not assigned_recruiter:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Assigned recruiter not found or does not belong to your agency.",
                )

        # 4. Duplicate policy check
        # A candidate cannot have multiple concurrent active (non-archived, non-withdrawn) applications for the same job.
        existing = self.repo.find_active_by_job_and_candidate(job_id, data.candidate_id)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Candidate '{candidate.full_name}' already has an active application "
                    f"for job '{job.title}' in stage '{existing.status.value}'. "
                    "Reapplication is allowed only after the existing application is archived or withdrawn."
                ),
            )

        # 5. Create Application
        initial_stage = data.status or PipelineStageType.APPLIED
        now = utc_now()
        shortlisted_at = now if initial_stage == PipelineStageType.SHORTLISTED else None

        app = Application(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            job_id=job_id,
            candidate_id=data.candidate_id,
            status=initial_stage,
            source=data.source.strip() if data.source else "RECRUITER_SOURCED",
            applied_at=now,
            shortlisted_at=shortlisted_at,
            last_activity_at=now,
            assigned_recruiter_id=data.assigned_recruiter_id,
            recruiter_summary=data.recruiter_summary.strip() if data.recruiter_summary else None,
        )
        self.db.add(app)

        # 6. Create immutable initial stage history record
        history = ApplicationStageHistory(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            application_id=app.id,
            previous_stage=None,
            new_stage=initial_stage,
            changed_by=current_user.id,
            reason="Application created",
            created_at=now,
        )
        self.db.add(history)

        # 7. Create optional initial note
        if data.initial_note and data.initial_note.strip():
            note = ApplicationNote(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                application_id=app.id,
                author_id=current_user.id,
                content=data.initial_note.strip(),
                created_at=now,
                updated_at=now,
            )
            self.db.add(note)

        # 8. Audit Logging
        audit_payload = {
            "job_id": str(job_id),
            "job_title": job.title,
            "candidate_id": str(data.candidate_id),
            "candidate_name": candidate.full_name,
            "initial_stage": initial_stage.value,
            "source": app.source,
        }
        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="APPLICATION_CREATED",
                resource_type="application",
                resource_id=str(app.id),
                details=json.dumps(audit_payload),
                created_at=now,
            )
        )

        if initial_stage == PipelineStageType.SHORTLISTED:
            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="CANDIDATE_SHORTLISTED",
                    resource_type="application",
                    resource_id=str(app.id),
                    details=json.dumps({"stage": initial_stage.value, "initial": True}),
                    created_at=now,
                )
            )

        if data.assigned_recruiter_id:
            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="RECRUITER_ASSIGNED",
                    resource_type="application",
                    resource_id=str(app.id),
                    details=json.dumps(
                        {"assigned_recruiter_id": str(data.assigned_recruiter_id)}
                    ),
                    created_at=now,
                )
            )

        cand_name = candidate.full_name
        job_title = job.title

        try:
            self.db.commit()
            self.db.refresh(app)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    f"Candidate '{cand_name}' already has an active application "
                    f"for job '{job_title}'. "
                    "Reapplication is allowed only after the existing application is archived or withdrawn."
                ),
            )

        try:
            from app.services.workflow_service import WorkflowService
            from app.models.enums import WorkflowTriggerType
            WorkflowService(self.db, self.agency_id).trigger_event(
                trigger_type=WorkflowTriggerType.APPLICATION_SUBMITTED,
                entity_type="application",
                entity_id=app.id,
                current_user=current_user,
            )
        except Exception:
            pass

        return self._resolve_application_read(
            app=app,
            candidate=candidate,
            job=job,
            recruiter=assigned_recruiter,
        )

    def transition_stage(
        self, application_id: uuid.UUID, current_user: User, data: ApplicationStageTransition
    ) -> ApplicationRead:
        """Execute validated transactional stage change with optimistic concurrency control (OCC).

        Stage Transition Policy:
        - HireLens operates an Action-Driven Pipeline Stage Model: transitions between any two distinct
          stages (A -> B where A != B) are supported to accommodate rapid, flexible agency operations
          (e.g., fast-tracking directly to Interview, reconsidering candidates from Rejected, reactivation).
        - Transitions to the exact same stage (A -> A) are rejected as redundant no-ops.
        - Concurrency is protected via database-level OCC version checking and partial unique constraints.
        """
        app = self.repo.get_with_details(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        old_stage = app.status
        new_stage = data.new_stage

        if old_stage == new_stage:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Application is already in '{new_stage.value}' stage.",
            )

        now = utc_now()
        current_version = app.version or 1
        shortlisted_at_val = app.shortlisted_at
        if new_stage == PipelineStageType.SHORTLISTED and not shortlisted_at_val:
            shortlisted_at_val = now

        # Atomic OCC update: guarantees that concurrent transitions cannot overwrite each other
        update_stmt = (
            update(Application)
            .where(
                Application.id == app.id,
                Application.agency_id == self.agency_id,
                Application.version == current_version,
            )
            .values(
                status=new_stage,
                last_activity_at=now,
                shortlisted_at=shortlisted_at_val,
                version=current_version + 1,
            )
        )
        res = self.db.execute(update_stmt)
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent stage modification detected. The application was modified by another operation. Please refresh and try again.",
            )

        # Record stage history
        history = ApplicationStageHistory(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            application_id=app.id,
            previous_stage=old_stage,
            new_stage=new_stage,
            changed_by=current_user.id,
            reason=data.reason.strip() if data.reason else None,
            created_at=now,
        )
        self.db.add(history)

        # Audit logs for sensitive pipeline actions
        audit_details = {
            "previous_stage": old_stage.value,
            "new_stage": new_stage.value,
            "reason": data.reason,
            "candidate_id": str(app.candidate_id),
            "job_id": str(app.job_id),
        }
        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="STAGE_TRANSITION",
                resource_type="application",
                resource_id=str(app.id),
                details=json.dumps(audit_details),
                created_at=now,
            )
        )

        if new_stage == PipelineStageType.SHORTLISTED:
            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="CANDIDATE_SHORTLISTED",
                    resource_type="application",
                    resource_id=str(app.id),
                    details=json.dumps(audit_details),
                    created_at=now,
                )
            )
        elif new_stage == PipelineStageType.ON_HOLD:
            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="CANDIDATE_PUT_ON_HOLD",
                    resource_type="application",
                    resource_id=str(app.id),
                    details=json.dumps(audit_details),
                    created_at=now,
                )
            )
        elif new_stage == PipelineStageType.INTERVIEW:
            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="INTERVIEW_SCHEDULED_OR_UPDATED",
                    resource_type="application",
                    resource_id=str(app.id),
                    details=json.dumps(audit_details),
                    created_at=now,
                )
            )
        elif new_stage == PipelineStageType.WITHDRAWN:
            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="APPLICATION_WITHDRAWN",
                    resource_type="application",
                    resource_id=str(app.id),
                    details=json.dumps(audit_details),
                    created_at=now,
                )
            )

        try:
            self.db.commit()
            self.db.refresh(app)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Conflict during stage transition: candidate already has an active application for this job.",
            )

        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db, self.agency_id).on_application_stage_changed(
                app, current_user, old_stage, new_stage, data.reason
            )
        except Exception:
            pass

        try:
            from app.services.workflow_service import WorkflowService
            from app.models.enums import WorkflowTriggerType
            WorkflowService(self.db, self.agency_id).trigger_event(
                trigger_type=WorkflowTriggerType.APPLICATION_STAGE_CHANGED,
                entity_type="application",
                entity_id=app.id,
                override_context={"old_stage": old_stage.value, "new_stage": new_stage.value},
                current_user=current_user,
            )
        except Exception:
            pass

        return self._resolve_application_read(app)

    def update_application(
        self, application_id: uuid.UUID, current_user: User, data: ApplicationUpdate
    ) -> ApplicationRead:
        app = self.repo.get_with_details(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        now = utc_now()
        updated = False

        # Recruiter assignment / unassignment
        if data.unassign_recruiter or ("assigned_recruiter_id" in data.model_fields_set and data.assigned_recruiter_id is None):
            if app.assigned_recruiter_id is not None:
                old_rec_id = app.assigned_recruiter_id
                app.assigned_recruiter_id = None
                app.last_activity_at = now
                updated = True
                self.db.add(
                    AuditLog(
                        agency_id=self.agency_id,
                        user_id=current_user.id,
                        action="RECRUITER_UNASSIGNED",
                        resource_type="application",
                        resource_id=str(app.id),
                        details=json.dumps({"previous_recruiter_id": str(old_rec_id)}),
                        created_at=now,
                    )
                )
        elif data.assigned_recruiter_id is not None:
            if data.assigned_recruiter_id != app.assigned_recruiter_id:
                recruiter = self.db.scalars(
                    select(User).where(
                        User.id == data.assigned_recruiter_id,
                        User.agency_id == self.agency_id,
                    )
                ).first()
                if not recruiter:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Recruiter not found or does not belong to your agency.",
                    )
                app.assigned_recruiter_id = data.assigned_recruiter_id
                app.last_activity_at = now
                updated = True
                self.db.add(
                    AuditLog(
                        agency_id=self.agency_id,
                        user_id=current_user.id,
                        action="RECRUITER_ASSIGNED",
                        resource_type="application",
                        resource_id=str(app.id),
                        details=json.dumps(
                            {"assigned_recruiter_id": str(data.assigned_recruiter_id)}
                        ),
                        created_at=now,
                    )
                )

        if data.recruiter_summary is not None:
            app.recruiter_summary = data.recruiter_summary.strip() or None
            app.last_activity_at = now
            updated = True

        if data.source is not None:
            app.source = data.source.strip() or app.source
            updated = True

        if data.archived is not None:
            if data.archived and not app.archived_at:
                app.archived_at = now
                app.last_activity_at = now
                updated = True
                self.db.add(
                    AuditLog(
                        agency_id=self.agency_id,
                        user_id=current_user.id,
                        action="APPLICATION_ARCHIVED",
                        resource_type="application",
                        resource_id=str(app.id),
                        details=json.dumps({"archived": True}),
                        created_at=now,
                    )
                )
            elif not data.archived and app.archived_at:
                app.archived_at = None
                app.last_activity_at = now
                updated = True

        if updated:
            try:
                self.db.commit()
                self.db.refresh(app)
            except IntegrityError:
                self.db.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Cannot reactivate application because candidate already has an active application for this job opening.",
                )

        return self._resolve_application_read(app)

    def get_application_detail(self, application_id: uuid.UUID) -> ApplicationDetailRead:
        app = self.repo.get_with_details(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        candidate = self.cand_repo.get(app.candidate_id)
        job = self.job_repo.get(app.job_id)

        # Get latest match result
        latest_match = (
            self.db.scalars(
                select(JobMatchResult)
                .where(
                    JobMatchResult.agency_id == self.agency_id,
                    JobMatchResult.job_id == app.job_id,
                    JobMatchResult.candidate_id == app.candidate_id,
                )
                .order_by(desc(JobMatchResult.created_at))
            )
            .first()
        )

        match_evidences = []
        latest_match_read = None
        if latest_match:
            evs = self.db.scalars(
                select(MatchEvidence)
                .where(
                    MatchEvidence.match_result_id == latest_match.id,
                    MatchEvidence.agency_id == self.agency_id,
                )
                .order_by(MatchEvidence.created_at.asc())
            ).all()
            match_evidences = [MatchEvidenceRead.model_validate(e) for e in evs]
            # Convert JobMatchResult to JobMatchResultRead
            strengths_list = json.loads(latest_match.strengths) if latest_match.strengths else []
            gaps_list = json.loads(latest_match.skill_gaps) if latest_match.skill_gaps else []
            verification_list = (
                json.loads(latest_match.verification_items)
                if latest_match.verification_items
                else []
            )
            questions_list = (
                json.loads(latest_match.suggested_questions)
                if latest_match.suggested_questions
                else []
            )

            is_stale = False
            if latest_match.status == "STALE":
                is_stale = True
            elif candidate and candidate.updated_at and candidate.updated_at > latest_match.created_at:
                is_stale = True
            elif job and job.updated_at and job.updated_at > latest_match.created_at:
                is_stale = True

            latest_match_read = JobMatchResultRead(
                id=latest_match.id,
                agency_id=latest_match.agency_id,
                job_id=latest_match.job_id,
                candidate_id=latest_match.candidate_id,
                match_run_id=latest_match.match_run_id,
                overall_score=latest_match.overall_score,
                required_skills_score=latest_match.required_skills_score,
                experience_score=latest_match.experience_score,
                preferred_skills_score=latest_match.preferred_skills_score,
                project_relevance_score=latest_match.project_relevance_score,
                other_criteria_score=latest_match.other_criteria_score,
                matched_requirements_count=latest_match.matched_requirements_count,
                partial_requirements_count=latest_match.partial_requirements_count,
                missing_requirements_count=latest_match.missing_requirements_count,
                needs_verification_count=latest_match.needs_verification_count,
                explanation=latest_match.explanation,
                strengths=strengths_list,
                skill_gaps=gaps_list,
                verification_items=verification_list,
                suggested_questions=questions_list,
                scoring_version=latest_match.scoring_version,
                status=latest_match.status,
                created_at=latest_match.created_at,
                updated_at=latest_match.updated_at,
                candidate_name=candidate.full_name if candidate else None,
                candidate_title=candidate.current_title if candidate else None,
                candidate_email=candidate.email if candidate else None,
                candidate_location=candidate.current_location if candidate else None,
                job_title=job.title if job else None,
                source_fingerprint=latest_match.source_fingerprint,
                is_stale=is_stale,
            )

        # Stage history
        history_records = self.repo.get_stage_history(app.id)
        stage_history_reads = [
            ApplicationStageHistoryRead(
                id=h.id,
                application_id=h.application_id,
                previous_stage=h.previous_stage,
                new_stage=h.new_stage,
                changed_by=h.changed_by,
                changed_by_name=h.user.full_name if h.user else "System",
                reason=h.reason,
                created_at=h.created_at,
            )
            for h in history_records
        ]

        # Notes
        notes_records = self.repo.get_notes(app.id)
        notes_reads = [
            ApplicationNoteRead(
                id=n.id,
                application_id=n.application_id,
                author_id=n.author_id,
                author_name=n.author.full_name if n.author else "Recruiter",
                content=n.content,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in notes_records
        ]

        # Activity log from AuditLog
        activity_logs = self.db.execute(
            select(AuditLog, User.full_name)
            .outerjoin(User, AuditLog.user_id == User.id)
            .where(
                AuditLog.agency_id == self.agency_id,
                AuditLog.resource_type == "application",
                AuditLog.resource_id == str(app.id),
            )
            .order_by(desc(AuditLog.created_at))
            .limit(30)
        ).all()
        activity_reads = [
            ApplicationActivityRead(
                id=log.id,
                action=log.action,
                user_id=log.user_id,
                user_name=u_name or "System Recruiter",
                details=log.details,
                created_at=log.created_at,
            )
            for log, u_name in activity_logs
        ]

        app_read = self._resolve_application_read(
            app=app,
            candidate=candidate,
            job=job,
            latest_match=latest_match,
        )

        return ApplicationDetailRead(
            application=app_read,
            candidate=CandidateRead.model_validate(candidate),
            job=JobRead.model_validate(job),
            stage_history=stage_history_reads,
            notes=notes_reads,
            activity=activity_reads,
            latest_match_result=latest_match_read,
            match_evidences=match_evidences,
        )

    def list_job_applications(
        self,
        job_id: uuid.UUID,
        status: Optional[PipelineStageType] = None,
        assigned_recruiter_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        include_archived: bool = False,
        skip: int = 0,
        limit: int = 100,
    ) -> ApplicationListResponse:
        # Verify job
        job = self.job_repo.get(job_id)
        if not job or job.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job opening not found or does not belong to your agency.",
            )

        apps, total, stage_counts = self.repo.list_for_job(
            job_id=job_id,
            status=status,
            assigned_recruiter_id=assigned_recruiter_id,
            search=search,
            include_archived=include_archived,
            skip=skip,
            limit=limit,
        )

        items = [
            self._resolve_application_read(app=a, job=job)
            for a in apps
        ]

        return ApplicationListResponse(
            items=items,
            total=total,
            stage_counts=stage_counts,
        )

    def list_candidate_applications(self, candidate_id: uuid.UUID) -> List[ApplicationRead]:
        candidate = self.cand_repo.get(candidate_id)
        if not candidate or candidate.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Candidate master profile not found or does not belong to your agency.",
            )

        apps = self.repo.list_for_candidate(candidate_id)
        return [
            self._resolve_application_read(app=a, candidate=candidate)
            for a in apps
        ]

    def list_recruiter_applications(self, recruiter_id: uuid.UUID) -> List[ApplicationRead]:
        recruiter = self.db.scalars(
            select(User).where(
                User.id == recruiter_id,
                User.agency_id == self.agency_id,
            )
        ).first()
        if not recruiter:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter not found or does not belong to your agency.",
            )

        apps = self.repo.list_for_recruiter(recruiter_id)
        return [
            self._resolve_application_read(app=a, recruiter=recruiter)
            for a in apps
        ]

    def get_stage_history(self, application_id: uuid.UUID) -> List[ApplicationStageHistoryRead]:
        app = self.repo.get(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        records = self.repo.get_stage_history(application_id)
        return [
            ApplicationStageHistoryRead(
                id=h.id,
                application_id=h.application_id,
                previous_stage=h.previous_stage,
                new_stage=h.new_stage,
                changed_by=h.changed_by,
                changed_by_name=h.user.full_name if h.user else "System",
                reason=h.reason,
                created_at=h.created_at,
            )
            for h in records
        ]

    def get_notes(self, application_id: uuid.UUID) -> List[ApplicationNoteRead]:
        app = self.repo.get(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        records = self.repo.get_notes(application_id)
        return [
            ApplicationNoteRead(
                id=n.id,
                application_id=n.application_id,
                author_id=n.author_id,
                author_name=n.author.full_name if n.author else "Recruiter",
                content=n.content,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in records
        ]

    def add_note(
        self, application_id: uuid.UUID, current_user: User, data: ApplicationNoteCreate
    ) -> ApplicationNoteRead:
        app = self.repo.get(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        now = utc_now()
        note = ApplicationNote(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            application_id=application_id,
            author_id=current_user.id,
            content=data.content.strip(),
            created_at=now,
            updated_at=now,
        )
        self.db.add(note)
        app.last_activity_at = now

        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="APPLICATION_NOTE_ADDED",
                resource_type="application",
                resource_id=str(application_id),
                details=json.dumps({"note_id": str(note.id)}),
                created_at=now,
            )
        )

        self.db.commit()
        self.db.refresh(note)

        return ApplicationNoteRead(
            id=note.id,
            application_id=note.application_id,
            author_id=note.author_id,
            author_name=current_user.full_name,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    def update_note(
        self,
        application_id: uuid.UUID,
        note_id: uuid.UUID,
        current_user: User,
        data: ApplicationNoteUpdate,
    ) -> ApplicationNoteRead:
        app = self.repo.get(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        note = self.repo.get_note(note_id)
        if not note or note.application_id != application_id or note.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application note not found.",
            )

        # RBAC: Only author or OWNER/ADMIN can edit
        if note.author_id != current_user.id and current_user.role not in (
            UserRole.OWNER,
            UserRole.ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify this recruiter note.",
            )

        note.content = data.content.strip()
        note.updated_at = utc_now()
        app.last_activity_at = note.updated_at

        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="APPLICATION_NOTE_UPDATED",
                resource_type="application",
                resource_id=str(application_id),
                details=json.dumps({"note_id": str(note.id)}),
                created_at=note.updated_at,
            )
        )

        self.db.commit()
        self.db.refresh(note)

        author_name = current_user.full_name
        if note.author_id != current_user.id and note.author:
            author_name = note.author.full_name

        return ApplicationNoteRead(
            id=note.id,
            application_id=note.application_id,
            author_id=note.author_id,
            author_name=author_name,
            content=note.content,
            created_at=note.created_at,
            updated_at=note.updated_at,
        )

    def compare_candidates(
        self, job_id: uuid.UUID, candidate_ids: List[uuid.UUID]
    ) -> CandidateComparisonResponse:
        """Compare multiple candidates side-by-side for a specific job opening."""
        job = self.job_repo.get(job_id)
        if not job or job.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Job opening not found or does not belong to your agency.",
            )

        if not candidate_ids:
            return CandidateComparisonResponse(job_id=job.id, job_title=job.title, candidates=[])

        comparison_items: List[CandidateComparisonItem] = []
        evidences_by_candidate: Dict[uuid.UUID, Dict[str, MatchEvidence]] = {}

        for cand_id in candidate_ids:
            cand = self.cand_repo.get(cand_id)
            if not cand or cand.agency_id != self.agency_id:
                continue

            # Check application status if present
            app = (
                self.db.scalars(
                    select(Application).where(
                        Application.agency_id == self.agency_id,
                        Application.job_id == job_id,
                        Application.candidate_id == cand_id,
                        Application.archived_at.is_(None),
                    )
                ).first()
            )

            # Check match result
            match_res = (
                self.db.scalars(
                    select(JobMatchResult)
                    .where(
                        JobMatchResult.agency_id == self.agency_id,
                        JobMatchResult.job_id == job_id,
                        JobMatchResult.candidate_id == cand_id,
                    )
                    .order_by(desc(JobMatchResult.created_at))
                ).first()
            )

            is_stale = False
            strengths = []
            skill_gaps = []
            verification_items = []
            overall_score = None
            req_score = None
            exp_score = None
            pref_score = None
            proj_score = None
            other_score = None
            matched_count = 0
            partial_count = 0
            missing_count = 0
            needs_verif_count = 0
            scoring_ver = None
            evaluated_at = None

            if match_res:
                overall_score = match_res.overall_score
                req_score = match_res.required_skills_score
                exp_score = match_res.experience_score
                pref_score = match_res.preferred_skills_score
                proj_score = match_res.project_relevance_score
                other_score = match_res.other_criteria_score
                matched_count = match_res.matched_requirements_count
                partial_count = match_res.partial_requirements_count
                missing_count = match_res.missing_requirements_count
                needs_verif_count = match_res.needs_verification_count
                scoring_ver = match_res.scoring_version
                evaluated_at = match_res.created_at

                if match_res.strengths:
                    strengths = json.loads(match_res.strengths)
                if match_res.skill_gaps:
                    skill_gaps = json.loads(match_res.skill_gaps)
                if match_res.verification_items:
                    verification_items = json.loads(match_res.verification_items)

                if match_res.status == "STALE":
                    is_stale = True
                elif cand.updated_at and cand.updated_at > match_res.created_at:
                    is_stale = True
                elif job.updated_at and job.updated_at > match_res.created_at:
                    is_stale = True

                # Load evidences for criteria matrix
                evs = self.db.scalars(
                    select(MatchEvidence).where(
                        MatchEvidence.match_result_id == match_res.id,
                        MatchEvidence.agency_id == self.agency_id,
                    )
                ).all()
                evidences_by_candidate[cand_id] = {e.criterion_name: e for e in evs}

            comparison_items.append(
                CandidateComparisonItem(
                    candidate_id=cand.id,
                    candidate_name=cand.full_name,
                    current_title=cand.current_title,
                    total_experience_months=cand.total_experience_months,
                    application_id=app.id if app else None,
                    application_status=app.status if app else None,
                    overall_score=overall_score,
                    required_skills_score=req_score,
                    experience_score=exp_score,
                    preferred_skills_score=pref_score,
                    project_relevance_score=proj_score,
                    other_criteria_score=other_score,
                    matched_requirements_count=matched_count,
                    partial_requirements_count=partial_count,
                    missing_requirements_count=missing_count,
                    needs_verification_count=needs_verif_count,
                    strengths=strengths,
                    skill_gaps=skill_gaps,
                    verification_items=verification_items,
                    is_stale=is_stale,
                    scoring_version=scoring_ver,
                    evaluated_at=evaluated_at,
                )
            )

        # Build detailed criteria matrix mapping job requirements across all compared candidates
        requirements = self.db.scalars(
            select(JobRequirement).where(JobRequirement.job_id == job_id)
        ).all()

        criteria_matrix = []
        for req in requirements:
            row: Dict[str, Any] = {
                "requirement_id": str(req.id),
                "requirement_text": req.requirement_text,
                "requirement_type": req.requirement_type.value,
                "is_mandatory": req.is_mandatory,
                "importance_weight": req.importance_weight,
                "evaluations": {},
            }
            for cand_id in candidate_ids:
                cand_ev_map = evidences_by_candidate.get(cand_id, {})
                ev = cand_ev_map.get(req.requirement_text)
                if ev:
                    row["evaluations"][str(cand_id)] = {
                        "evidence_status": ev.evidence_status.value,
                        "candidate_evidence": ev.candidate_evidence,
                        "semantic_similarity": ev.semantic_similarity,
                        "verification_status": ev.verification_status.value,
                    }
                else:
                    row["evaluations"][str(cand_id)] = {
                        "evidence_status": "NOT_EVALUATED",
                        "candidate_evidence": None,
                        "semantic_similarity": None,
                        "verification_status": "UNREVIEWED",
                    }
            criteria_matrix.append(row)

        return CandidateComparisonResponse(
            job_id=job.id,
            job_title=job.title,
            candidates=comparison_items,
            criteria_matrix=criteria_matrix,
        )

    def get_pipeline_dashboard_stats(self) -> PipelineDashboardStats:
        stats = self.repo.get_agency_pipeline_stats()
        return PipelineDashboardStats(
            total_active_applications=stats["total_active_applications"],
            stage_counts=stats["stage_counts"],
            recent_activities=stats["recent_activities"],
            job_summaries=stats["job_summaries"],
        )
