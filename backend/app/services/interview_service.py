import json
import uuid
import hashlib
import zoneinfo
from datetime import datetime
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, desc, update, text
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException, status

from app.models.interview import (
    Interview,
    InterviewParticipant,
    InterviewFeedback,
    InterviewHistory,
)
from app.models.application import Application
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.entities import User, AuditLog
from app.models.enums import (
    InterviewMode,
    InterviewStatus,
    InterviewRoundType,
    ParticipantRole,
    AttendanceStatus,
    FeedbackRecommendation,
    UserRole,
    PipelineStageType,
)
from app.models.base import utc_now
from app.core.timezone import (
    validate_timezone,
    parse_and_normalize_to_utc,
    convert_utc_to_timezone,
    format_ist,
    DEFAULT_TIMEZONE,
)
from app.repositories.interview_repo import InterviewRepository
from app.repositories.application_repo import ApplicationRepository
from app.schemas.interview import (
    InterviewCreate,
    InterviewUpdate,
    InterviewReschedule,
    InterviewCancel,
    InterviewComplete,
    InterviewRead,
    InterviewDetailRead,
    InterviewListResponse,
    InterviewParticipantCreate,
    InterviewParticipantRead,
    InterviewFeedbackCreate,
    InterviewFeedbackUpdate,
    InterviewFeedbackRead,
    InterviewHistoryRead,
)


class InterviewService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = InterviewRepository(db, agency_id)
        self.app_repo = ApplicationRepository(db, agency_id)

    @staticmethod
    def compute_advisory_lock_key(agency_id: uuid.UUID, user_id: uuid.UUID) -> int:
        """Derive a deterministic 64-bit signed integer advisory lock key from agency_id and user_id."""
        digest = hashlib.sha256(f"{agency_id}_{user_id}".encode("utf-8")).digest()
        return int.from_bytes(digest[:8], byteorder="big", signed=True)

    _compute_advisory_lock_key = compute_advisory_lock_key

    def _acquire_interviewer_locks(self, user_ids: List[uuid.UUID]) -> None:
        """Acquire exclusive transaction-level advisory locks for interviewers in PostgreSQL.
        Locks are sorted deterministically by user_id to prevent deadlocks when multiple
        interviewers are scheduled concurrently.
        Preserves SQLite compatibility by inspecting the active database engine dialect.
        """
        valid_ids = sorted(list({u for u in user_ids if u is not None}))
        if not valid_ids:
            return

        try:
            bind = self.db.get_bind()
            dialect_name = bind.dialect.name
        except Exception:
            dialect_name = "sqlite"

        if dialect_name == "postgresql":
            for u_id in valid_ids:
                lock_key = self.compute_advisory_lock_key(self.agency_id, u_id)
                self.db.execute(
                    text("SELECT pg_advisory_xact_lock(:key)"),
                    {"key": lock_key},
                )

    def _validate_timezone(self, tz_str: str) -> None:
        """Validate IANA timezone string."""
        validate_timezone(tz_str)

    def _validate_meeting_url(self, url: Optional[str]) -> None:
        """Validate meeting URL format if provided."""
        if not url:
            return
        trimmed = url.strip()
        if not (trimmed.startswith("http://") or trimmed.startswith("https://")):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Meeting URL must begin with 'https://' or 'http://'.",
            )
        if len(trimmed) < 10 or "." not in trimmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Malformed meeting URL. Please provide a valid meeting link.",
            )

    def _resolve_interview_read(
        self,
        interview: Interview,
        application: Optional[Application] = None,
        job: Optional[Job] = None,
        candidate: Optional[Candidate] = None,
        current_user: Optional[User] = None,
    ) -> InterviewRead:
        """Helper to project Interview ORM model to InterviewRead with denormalized context.
        Applies privacy filtering so that private feedback does NOT leak via feedbacks_count
        or average_rating to unauthorized recruiters or viewers.
        """
        app = application or interview.application
        jb = job or (app.job if app else None)
        cand = candidate or (app.candidate if app else None)

        participants_read = [
            InterviewParticipantRead.model_validate(p) for p in interview.participants
        ]

        # Calculate feedback stats respecting privacy visibility
        visible_feedbacks = []
        for f in interview.feedbacks:
            if f.is_private:
                can_view = (
                    current_user is not None
                    and (
                        f.reviewer_id == current_user.id
                        or current_user.role in (UserRole.OWNER, UserRole.ADMIN)
                    )
                )
                if not can_view:
                    continue
            visible_feedbacks.append(f)

        feedbacks_count = len(visible_feedbacks)
        avg_rating = None
        if feedbacks_count > 0:
            avg_rating = round(sum(f.overall_rating for f in visible_feedbacks) / feedbacks_count, 1)

        creator_name = interview.creator.full_name if interview.creator else None

        # Formatted IST strings
        ist_start_str = format_ist(interview.scheduled_start)
        ist_end_str = format_ist(interview.scheduled_end)

        return InterviewRead(
            id=interview.id,
            agency_id=interview.agency_id,
            application_id=interview.application_id,
            round_name=interview.round_name,
            round_type=interview.round_type,
            title=interview.title,
            description=interview.description,
            interview_mode=interview.interview_mode,
            scheduled_start=interview.scheduled_start,
            scheduled_end=interview.scheduled_end,
            timezone=interview.timezone,
            location=interview.location,
            meeting_url=interview.meeting_url,
            status=interview.status,
            version=interview.version,
            created_by=interview.created_by,
            created_by_name=creator_name,
            cancelled_at=interview.cancelled_at,
            cancellation_reason=interview.cancellation_reason,
            completed_at=interview.completed_at,
            created_at=interview.created_at,
            updated_at=interview.updated_at,
            job_id=jb.id if jb else None,
            job_title=jb.title if jb else None,
            candidate_id=cand.id if cand else None,
            candidate_name=cand.full_name if cand else None,
            candidate_title=cand.current_title if cand else None,
            candidate_email=cand.email if cand else None,
            application_status=app.status if app else None,
            participants=participants_read,
            feedbacks_count=feedbacks_count,
            average_rating=avg_rating,
            scheduled_start_ist=ist_start_str,
            scheduled_end_ist=ist_end_str,
        )

    def create_interview(
        self,
        application_id: uuid.UUID,
        current_user: User,
        data: InterviewCreate,
    ) -> InterviewRead:
        """Schedule a new interview round for an active job application."""
        # 1. Enforce Application tenant isolation & activity status
        app = self.app_repo.get_with_details(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        if app.archived_at is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule an interview for an archived application.",
            )

        if app.status == PipelineStageType.WITHDRAWN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot schedule an interview for a withdrawn application. Candidate must reapply first.",
            )

        # 2. Validate timing and duration with standardized timezone normalization
        target_tz = data.timezone or DEFAULT_TIMEZONE
        self._validate_timezone(target_tz)
        self._validate_meeting_url(data.meeting_url)

        utc_start = parse_and_normalize_to_utc(data.scheduled_start, target_tz)
        utc_end = parse_and_normalize_to_utc(data.scheduled_end, target_tz)

        if utc_end <= utc_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview scheduled end time must be after start time.",
            )

        duration_minutes = (utc_end - utc_start).total_seconds() / 60
        if duration_minutes < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview duration must be at least 10 minutes.",
            )
        if duration_minutes > 480:  # 8 hours
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview duration cannot exceed 8 hours.",
            )

        # 3. Validate participants, acquire PostgreSQL advisory locks, and detect interviewer conflicts
        now = utc_now()
        seen_emails = set()
        seen_user_ids = set()
        validated_participants: List[InterviewParticipant] = []

        interview_id = uuid.uuid4()

        # Deterministically acquire transaction-level advisory locks for all internal interviewers
        internal_user_ids = [p.user_id for p in data.participants if p.user_id]
        self._acquire_interviewer_locks(internal_user_ids)

        for p in data.participants:
            email_lower = p.participant_email.strip().lower()
            if email_lower in seen_emails:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Duplicate participant email in request: '{p.participant_email}'.",
                )
            seen_emails.add(email_lower)

            internal_user = None
            if p.user_id:
                if p.user_id in seen_user_ids:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Duplicate participant user assigned in request.",
                    )
                seen_user_ids.add(p.user_id)

                internal_user = self.db.scalars(
                    select(User).where(
                        User.id == p.user_id,
                        User.agency_id == self.agency_id,
                    )
                ).first()
                if not internal_user:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Assigned participant user not found or does not belong to your agency.",
                    )

                # Scheduling Conflict Detection for internal interviewers
                conflicts = self.repo.find_interviewer_conflicts(
                    user_id=p.user_id,
                    start_time=utc_start,
                    end_time=utc_end,
                )
                if conflicts:
                    conflict = conflicts[0]
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Scheduling conflict: Interviewer '{internal_user.full_name}' is already "
                            f"booked for '{conflict.title}' ({conflict.round_name}) from "
                            f"{conflict.scheduled_start.strftime('%Y-%m-%d %H:%M')} to "
                            f"{conflict.scheduled_end.strftime('%H:%M %Z')}."
                        ),
                    )

            part_model = InterviewParticipant(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                interview_id=interview_id,
                user_id=p.user_id,
                participant_name=internal_user.full_name if internal_user else p.participant_name.strip(),
                participant_email=internal_user.email if internal_user else email_lower,
                participant_role=p.participant_role,
                attendance_status=p.attendance_status,
                created_at=now,
            )
            validated_participants.append(part_model)

        # 4. Create Interview Record with normalized UTC timestamps
        interview = Interview(
            id=interview_id,
            agency_id=self.agency_id,
            application_id=application_id,
            round_name=data.round_name.strip(),
            round_type=data.round_type,
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            interview_mode=data.interview_mode,
            scheduled_start=utc_start,
            scheduled_end=utc_end,
            timezone=target_tz,
            location=data.location.strip() if data.location else None,
            meeting_url=data.meeting_url.strip() if data.meeting_url else None,
            status=InterviewStatus.SCHEDULED,
            version=1,
            created_by=current_user.id,
            created_at=now,
            updated_at=now,
        )
        self.db.add(interview)

        for p_model in validated_participants:
            self.db.add(p_model)

        # 5. Immutable Interview History Record
        history = InterviewHistory(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            interview_id=interview.id,
            actor_id=current_user.id,
            action="INTERVIEW_SCHEDULED",
            previous_value=None,
            new_value=json.dumps({
                "round_name": interview.round_name,
                "start": interview.scheduled_start.isoformat(),
                "end": interview.scheduled_end.isoformat(),
                "timezone": interview.timezone,
                "mode": interview.interview_mode.value,
                "participants_count": len(validated_participants),
            }),
            reason="Interview round scheduled",
            created_at=now,
        )
        self.db.add(history)

        # 6. AuditLog entry
        cand_name = app.candidate.full_name if app.candidate else "Candidate"
        job_title = app.job.title if app.job else "Job"
        audit_details = {
            "application_id": str(application_id),
            "candidate_name": cand_name,
            "job_title": job_title,
            "round_name": interview.round_name,
            "scheduled_start": interview.scheduled_start.isoformat(),
            "scheduled_end": interview.scheduled_end.isoformat(),
            "mode": interview.interview_mode.value,
        }
        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="INTERVIEW_SCHEDULED",
                resource_type="interview",
                resource_id=str(interview.id),
                details=json.dumps(audit_details),
                created_at=now,
            )
        )

        # Touch application last_activity_at
        app.last_activity_at = now

        self.db.commit()
        self.db.refresh(interview)

        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db, self.agency_id).on_interview_scheduled(interview, app, current_user)
        except Exception:
            pass

        try:
            from app.services.calendar_sync_service import CalendarSyncService
            CalendarSyncService(self.db, self.agency_id).on_interview_scheduled(interview, current_user)
        except Exception:
            pass

        try:
            from app.services.workflow_service import WorkflowService
            from app.models.enums import WorkflowTriggerType
            WorkflowService(self.db, self.agency_id).trigger_event(
                trigger_type=WorkflowTriggerType.INTERVIEW_SCHEDULED,
                entity_type="interview",
                entity_id=interview.id,
                current_user=current_user,
            )
        except Exception:
            pass

        return self._resolve_interview_read(interview, application=app, current_user=current_user)


    def get_interview_detail(
        self, interview_id: uuid.UUID, current_user: User
    ) -> InterviewDetailRead:
        """Retrieve interview detail with privacy-filtered feedbacks, participants, and history."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        app = interview.application
        cand = app.candidate if app else None
        job = app.job if app else None

        interview_read = self._resolve_interview_read(
            interview, application=app, job=job, candidate=cand, current_user=current_user
        )

        # Privacy Filter for Feedback:
        # If is_private is True, ONLY the author or OWNER/ADMIN can see the feedback!
        filtered_feedbacks: List[InterviewFeedbackRead] = []
        user_has_submitted = False
        all_feedbacks = interview.feedbacks

        for f in all_feedbacks:
            if f.reviewer_id == current_user.id:
                user_has_submitted = True

            # Check privacy visibility
            if f.is_private:
                can_view_private = (
                    f.reviewer_id == current_user.id
                    or current_user.role in (UserRole.OWNER, UserRole.ADMIN)
                )
                if not can_view_private:
                    continue  # Hidden from other recruiters/viewers

            reviewer_name = f.reviewer.full_name if f.reviewer else "Unknown Reviewer"
            reviewer_role = f.reviewer.role.value if f.reviewer else None

            strengths_list = json.loads(f.strengths) if f.strengths else []
            concerns_list = json.loads(f.concerns) if f.concerns else []

            filtered_feedbacks.append(
                InterviewFeedbackRead(
                    id=f.id,
                    interview_id=f.interview_id,
                    reviewer_id=f.reviewer_id,
                    reviewer_name=reviewer_name,
                    reviewer_role=reviewer_role,
                    overall_rating=f.overall_rating,
                    recommendation=f.recommendation,
                    technical_assessment=f.technical_assessment,
                    communication_assessment=f.communication_assessment,
                    problem_solving_assessment=f.problem_solving_assessment,
                    role_specific_assessment=f.role_specific_assessment,
                    strengths=strengths_list,
                    concerns=concerns_list,
                    detailed_feedback=f.detailed_feedback,
                    is_private=f.is_private,
                    submitted_at=f.submitted_at,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                )
            )

        history_reads = [
            InterviewHistoryRead(
                id=h.id,
                interview_id=h.interview_id,
                actor_id=h.actor_id,
                actor_name=h.actor.full_name if h.actor else "System",
                action=h.action,
                previous_value=h.previous_value,
                new_value=h.new_value,
                reason=h.reason,
                created_at=h.created_at,
            )
            for h in interview.history
        ]

        participants_read = [
            InterviewParticipantRead.model_validate(p) for p in interview.participants
        ]

        avg_rating = None
        if filtered_feedbacks:
            avg_rating = round(sum(f.overall_rating for f in filtered_feedbacks) / len(filtered_feedbacks), 1)

        user_can_submit = (
            current_user.role in (UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER)
            and interview.status not in (InterviewStatus.CANCELLED, InterviewStatus.DRAFT)
        )

        return InterviewDetailRead(
            interview=interview_read,
            participants=participants_read,
            feedbacks=filtered_feedbacks,
            history=history_reads,
            feedbacks_count=len(filtered_feedbacks),
            average_rating=avg_rating,
            user_can_submit_feedback=user_can_submit,
            user_has_submitted_feedback=user_has_submitted,
        )

    def update_interview(
        self, interview_id: uuid.UUID, current_user: User, data: InterviewUpdate
    ) -> InterviewRead:
        """Update interview general details (title, round, mode, location, meeting URL)."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        if interview.status in (InterviewStatus.CANCELLED, InterviewStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit an interview that is already '{interview.status.value}'.",
            )

        now = utc_now()
        previous_vals = {}
        new_vals = {}
        updated = False

        if data.round_name is not None and data.round_name.strip() != interview.round_name:
            previous_vals["round_name"] = interview.round_name
            interview.round_name = data.round_name.strip()
            new_vals["round_name"] = interview.round_name
            updated = True

        if data.round_type is not None and data.round_type != interview.round_type:
            previous_vals["round_type"] = interview.round_type.value
            interview.round_type = data.round_type
            new_vals["round_type"] = interview.round_type.value
            updated = True

        if data.title is not None and data.title.strip() != interview.title:
            previous_vals["title"] = interview.title
            interview.title = data.title.strip()
            new_vals["title"] = interview.title
            updated = True

        if data.description is not None and data.description.strip() != (interview.description or ""):
            interview.description = data.description.strip() or None
            updated = True

        if data.interview_mode is not None and data.interview_mode != interview.interview_mode:
            previous_vals["interview_mode"] = interview.interview_mode.value
            interview.interview_mode = data.interview_mode
            new_vals["interview_mode"] = interview.interview_mode.value
            updated = True

        if data.location is not None:
            interview.location = data.location.strip() or None
            updated = True

        if data.meeting_url is not None:
            self._validate_meeting_url(data.meeting_url)
            interview.meeting_url = data.meeting_url.strip() or None
            updated = True

        if data.participants is not None:
            # Deterministically acquire locks for both existing and new internal interviewers
            existing_user_ids = [p.user_id for p in interview.participants if p.user_id]
            new_user_ids = [p.user_id for p in data.participants if p.user_id]
            all_user_ids = list(set(existing_user_ids + new_user_ids))
            self._acquire_interviewer_locks(all_user_ids)

            seen_emails = set()
            seen_ids = set()
            new_part_models: List[InterviewParticipant] = []

            for p in data.participants:
                email_lower = p.participant_email.strip().lower()
                if email_lower in seen_emails:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Duplicate participant email in request: '{p.participant_email}'.",
                    )
                seen_emails.add(email_lower)

                internal_user = None
                if p.user_id:
                    if p.user_id in seen_ids:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail="Duplicate participant user assigned in request.",
                        )
                    seen_ids.add(p.user_id)

                    internal_user = self.db.scalars(
                        select(User).where(
                            User.id == p.user_id,
                            User.agency_id == self.agency_id,
                        )
                    ).first()
                    if not internal_user:
                        raise HTTPException(
                            status_code=status.HTTP_404_NOT_FOUND,
                            detail="Assigned participant user not found or does not belong to your agency.",
                        )

                    # Conflict detection for internal interviewers
                    conflicts = self.repo.find_interviewer_conflicts(
                        user_id=p.user_id,
                        start_time=interview.scheduled_start,
                        end_time=interview.scheduled_end,
                        exclude_interview_id=interview.id,
                    )
                    if conflicts:
                        conflict = conflicts[0]
                        raise HTTPException(
                            status_code=status.HTTP_409_CONFLICT,
                            detail=(
                                f"Scheduling conflict: Interviewer '{internal_user.full_name}' is already "
                                f"booked for '{conflict.title}' ({conflict.round_name}) from "
                                f"{conflict.scheduled_start.strftime('%Y-%m-%d %H:%M')} to "
                                f"{conflict.scheduled_end.strftime('%H:%M %Z')}."
                            ),
                        )

                part_model = InterviewParticipant(
                    id=uuid.uuid4(),
                    agency_id=self.agency_id,
                    interview_id=interview.id,
                    user_id=p.user_id,
                    participant_name=internal_user.full_name if internal_user else p.participant_name.strip(),
                    participant_email=internal_user.email if internal_user else email_lower,
                    participant_role=p.participant_role,
                    attendance_status=p.attendance_status,
                    created_at=now,
                )
                new_part_models.append(part_model)

            interview.participants.clear()
            interview.participants.extend(new_part_models)
            new_vals["participants_count"] = len(new_part_models)
            updated = True


        if updated:
            interview.updated_at = now
            interview.version += 1

            self.db.add(
                InterviewHistory(
                    id=uuid.uuid4(),
                    agency_id=self.agency_id,
                    interview_id=interview.id,
                    actor_id=current_user.id,
                    action="INTERVIEW_DETAILS_UPDATED",
                    previous_value=json.dumps(previous_vals) if previous_vals else None,
                    new_value=json.dumps(new_vals) if new_vals else None,
                    reason="Details updated by recruiter",
                    created_at=now,
                )
            )

            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="INTERVIEW_UPDATED",
                    resource_type="interview",
                    resource_id=str(interview.id),
                    details=json.dumps(new_vals),
                    created_at=now,
                )
            )

            self.db.commit()
            self.db.refresh(interview)

        return self._resolve_interview_read(interview, current_user=current_user)

    def confirm_interview(
        self, interview_id: uuid.UUID, current_user: User
    ) -> InterviewRead:
        """Confirm a scheduled interview."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        if interview.status == InterviewStatus.CONFIRMED:
            # Idempotent response
            return self._resolve_interview_read(interview, current_user=current_user)

        if interview.status in (InterviewStatus.CANCELLED, InterviewStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot confirm an interview that is '{interview.status.value}'.",
            )

        now = utc_now()
        old_status = interview.status.value
        interview.status = InterviewStatus.CONFIRMED
        interview.updated_at = now
        interview.version += 1

        self.db.add(
            InterviewHistory(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                interview_id=interview.id,
                actor_id=current_user.id,
                action="INTERVIEW_CONFIRMED",
                previous_value=json.dumps({"status": old_status}),
                new_value=json.dumps({"status": InterviewStatus.CONFIRMED.value}),
                reason="Interview confirmed by recruiter",
                created_at=now,
            )
        )

        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="INTERVIEW_CONFIRMED",
                resource_type="interview",
                resource_id=str(interview.id),
                details=json.dumps({"status": "CONFIRMED"}),
                created_at=now,
            )
        )

        self.db.commit()
        self.db.refresh(interview)

        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db, self.agency_id).on_interview_confirmed(interview, interview.application, current_user)
        except Exception:
            pass

        try:
            from app.services.calendar_sync_service import CalendarSyncService
            CalendarSyncService(self.db, self.agency_id).on_interview_confirmed(interview, current_user)
        except Exception:
            pass

        return self._resolve_interview_read(interview, current_user=current_user)


    def reschedule_interview(
        self, interview_id: uuid.UUID, current_user: User, data: InterviewReschedule
    ) -> InterviewRead:
        """Reschedule interview date/time with conflict checking and OCC version protection."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        if interview.status == InterviewStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reschedule a cancelled interview. Please schedule a new interview round.",
            )

        if interview.status == InterviewStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot reschedule an interview that is already completed.",
            )

        if data.scheduled_end <= data.scheduled_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview scheduled end time must be after start time.",
            )

        target_tz = data.timezone or interview.timezone or DEFAULT_TIMEZONE
        self._validate_timezone(target_tz)

        utc_start = parse_and_normalize_to_utc(data.scheduled_start, target_tz)
        utc_end = parse_and_normalize_to_utc(data.scheduled_end, target_tz)

        if utc_end <= utc_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview scheduled end time must be after start time.",
            )

        duration_minutes = (utc_end - utc_start).total_seconds() / 60
        if duration_minutes < 10:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview duration must be at least 10 minutes.",
            )
        if duration_minutes > 480:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview duration cannot exceed 8 hours.",
            )

        # Acquire PostgreSQL advisory locks for all assigned internal interviewers
        participant_user_ids = [p.user_id for p in interview.participants if p.user_id]
        self._acquire_interviewer_locks(participant_user_ids)

        # Check interviewer conflicts for assigned participants
        for part in interview.participants:
            if part.user_id:
                conflicts = self.repo.find_interviewer_conflicts(
                    user_id=part.user_id,
                    start_time=utc_start,
                    end_time=utc_end,
                    exclude_interview_id=interview.id,
                )
                if conflicts:
                    conflict = conflicts[0]
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail=(
                            f"Scheduling conflict: Interviewer '{part.participant_name}' has an "
                            f"overlapping interview '{conflict.title}' ({conflict.round_name}) from "
                            f"{conflict.scheduled_start.strftime('%Y-%m-%d %H:%M')} to "
                            f"{conflict.scheduled_end.strftime('%H:%M %Z')}."
                        ),
                    )

        now = utc_now()
        current_version = interview.version or 1
        previous_start_utc = interview.scheduled_start
        previous_end_utc = interview.scheduled_end

        previous_schedule = {
            "start": interview.scheduled_start.isoformat(),
            "end": interview.scheduled_end.isoformat(),
            "timezone": interview.timezone,
            "status": interview.status.value,
        }
        new_schedule = {
            "start": utc_start.isoformat(),
            "end": utc_end.isoformat(),
            "timezone": target_tz,
            "status": InterviewStatus.RESCHEDULED.value,
        }

        # Atomic OCC update
        stmt = (
            update(Interview)
            .where(
                Interview.id == interview.id,
                Interview.agency_id == self.agency_id,
                Interview.version == current_version,
            )
            .values(
                scheduled_start=utc_start,
                scheduled_end=utc_end,
                timezone=target_tz,
                status=InterviewStatus.RESCHEDULED,
                version=current_version + 1,
                updated_at=now,
            )
        )
        res = self.db.execute(stmt)
        if res.rowcount == 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Concurrent modification detected. The interview was updated by another request. Please refresh and try again.",
            )

        # Record History
        self.db.add(
            InterviewHistory(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                interview_id=interview.id,
                actor_id=current_user.id,
                action="INTERVIEW_RESCHEDULED",
                previous_value=json.dumps(previous_schedule),
                new_value=json.dumps(new_schedule),
                reason=data.reason.strip(),
                created_at=now,
            )
        )

        # AuditLog
        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="INTERVIEW_RESCHEDULED",
                resource_type="interview",
                resource_id=str(interview.id),
                details=json.dumps({
                    "reason": data.reason.strip(),
                    "new_start": utc_start.isoformat(),
                    "new_end": utc_end.isoformat(),
                }),
                created_at=now,
            )
        )

        # Touch application last_activity_at
        if interview.application:
            interview.application.last_activity_at = now

        self.db.commit()
        self.db.refresh(interview)

        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db, self.agency_id).on_interview_rescheduled(
                interview, interview.application, current_user, previous_start_utc, previous_end_utc, data.reason
            )
        except Exception:
            pass

        try:
            from app.services.calendar_sync_service import CalendarSyncService
            CalendarSyncService(self.db, self.agency_id).on_interview_rescheduled(interview, current_user)
        except Exception:
            pass

        try:
            from app.services.workflow_service import WorkflowService
            from app.models.enums import WorkflowTriggerType
            WorkflowService(self.db, self.agency_id).trigger_event(
                trigger_type=WorkflowTriggerType.INTERVIEW_RESCHEDULED,
                entity_type="interview",
                entity_id=interview.id,
                current_user=current_user,
            )
        except Exception:
            pass

        return self._resolve_interview_read(interview, current_user=current_user)


    def cancel_interview(
        self, interview_id: uuid.UUID, current_user: User, data: InterviewCancel
    ) -> InterviewRead:
        """Cancel an interview with reason, preserving historical records."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        if interview.status == InterviewStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview is already cancelled.",
            )

        if interview.status == InterviewStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot cancel an interview that has already been completed.",
            )

        now = utc_now()
        old_status = interview.status.value
        interview.status = InterviewStatus.CANCELLED
        interview.cancelled_at = now
        interview.cancellation_reason = data.reason.strip()
        interview.updated_at = now
        interview.version += 1

        self.db.add(
            InterviewHistory(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                interview_id=interview.id,
                actor_id=current_user.id,
                action="INTERVIEW_CANCELLED",
                previous_value=json.dumps({"status": old_status}),
                new_value=json.dumps({"status": InterviewStatus.CANCELLED.value, "reason": interview.cancellation_reason}),
                reason=interview.cancellation_reason,
                created_at=now,
            )
        )

        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="INTERVIEW_CANCELLED",
                resource_type="interview",
                resource_id=str(interview.id),
                details=json.dumps({"reason": interview.cancellation_reason}),
                created_at=now,
            )
        )

        if interview.application:
            interview.application.last_activity_at = now

        self.db.commit()
        self.db.refresh(interview)

        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db, self.agency_id).on_interview_cancelled(
                interview, interview.application, current_user, interview.cancellation_reason
            )
        except Exception:
            pass

        try:
            from app.services.calendar_sync_service import CalendarSyncService
            CalendarSyncService(self.db, self.agency_id).on_interview_cancelled(interview, current_user)
        except Exception:
            pass

        return self._resolve_interview_read(interview, current_user=current_user)


    def complete_interview(
        self, interview_id: uuid.UUID, current_user: User, data: InterviewComplete
    ) -> InterviewRead:
        """Mark an interview as completed."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        if interview.status == InterviewStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Interview is already marked as completed.",
            )

        if interview.status == InterviewStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot complete an interview that was cancelled.",
            )

        now = utc_now()
        old_status = interview.status.value
        interview.status = InterviewStatus.COMPLETED
        interview.completed_at = now
        interview.updated_at = now
        interview.version += 1

        self.db.add(
            InterviewHistory(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                interview_id=interview.id,
                actor_id=current_user.id,
                action="INTERVIEW_COMPLETED",
                previous_value=json.dumps({"status": old_status}),
                new_value=json.dumps({"status": InterviewStatus.COMPLETED.value, "notes": data.notes}),
                reason=data.notes.strip() if data.notes else "Interview marked as completed",
                created_at=now,
            )
        )

        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="INTERVIEW_COMPLETED",
                resource_type="interview",
                resource_id=str(interview.id),
                details=json.dumps({"notes": data.notes}),
                created_at=now,
            )
        )

        if interview.application:
            interview.application.last_activity_at = now

        self.db.commit()
        self.db.refresh(interview)

        try:
            from app.services.notification_service import NotificationService
            NotificationService(self.db, self.agency_id).on_interview_completed(interview, interview.application, current_user)
        except Exception:
            pass

        try:
            from app.services.workflow_service import WorkflowService
            from app.models.enums import WorkflowTriggerType
            WorkflowService(self.db, self.agency_id).trigger_event(
                trigger_type=WorkflowTriggerType.INTERVIEW_COMPLETED,
                entity_type="interview",
                entity_id=interview.id,
                current_user=current_user,
            )
        except Exception:
            pass

        return self._resolve_interview_read(interview, current_user=current_user)

    def submit_feedback(
        self,
        interview_id: uuid.UUID,
        current_user: User,
        data: InterviewFeedbackCreate,
    ) -> InterviewFeedbackRead:
        """Submit structured interview evaluation and recommendation."""
        interview = self.repo.get_with_details(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        if interview.status == InterviewStatus.CANCELLED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit feedback for a cancelled interview.",
            )

        # Check duplicate submission by same reviewer
        existing = (
            self.db.scalars(
                select(InterviewFeedback).where(
                    InterviewFeedback.interview_id == interview_id,
                    InterviewFeedback.reviewer_id == current_user.id,
                )
            ).first()
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "You have already submitted feedback for this interview round. "
                    "Please edit your existing feedback instead."
                ),
            )

        now = utc_now()
        strengths_json = json.dumps(data.strengths) if data.strengths else None
        concerns_json = json.dumps(data.concerns) if data.concerns else None

        feedback = InterviewFeedback(
            id=uuid.uuid4(),
            agency_id=self.agency_id,
            interview_id=interview_id,
            reviewer_id=current_user.id,
            overall_rating=data.overall_rating,
            recommendation=data.recommendation,
            technical_assessment=data.technical_assessment.strip() if data.technical_assessment else None,
            communication_assessment=data.communication_assessment.strip() if data.communication_assessment else None,
            problem_solving_assessment=data.problem_solving_assessment.strip() if data.problem_solving_assessment else None,
            role_specific_assessment=data.role_specific_assessment.strip() if data.role_specific_assessment else None,
            strengths=strengths_json,
            concerns=concerns_json,
            detailed_feedback=data.detailed_feedback.strip(),
            is_private=data.is_private,
            submitted_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(feedback)

        # Record History
        self.db.add(
            InterviewHistory(
                id=uuid.uuid4(),
                agency_id=self.agency_id,
                interview_id=interview.id,
                actor_id=current_user.id,
                action="FEEDBACK_SUBMITTED",
                previous_value=None,
                new_value=json.dumps({
                    "rating": data.overall_rating,
                    "recommendation": data.recommendation.value,
                    "is_private": data.is_private,
                }),
                reason="Feedback submitted by reviewer",
                created_at=now,
            )
        )

        # AuditLog
        self.db.add(
            AuditLog(
                agency_id=self.agency_id,
                user_id=current_user.id,
                action="INTERVIEW_FEEDBACK_SUBMITTED",
                resource_type="interview_feedback",
                resource_id=str(feedback.id),
                details=json.dumps({
                    "interview_id": str(interview_id),
                    "rating": data.overall_rating,
                    "recommendation": data.recommendation.value,
                }),
                created_at=now,
            )
        )

        try:
            self.db.commit()
            self.db.refresh(feedback)
        except IntegrityError:
            self.db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Feedback from this reviewer already exists for this interview round.",
            )

        try:
            from app.services.workflow_service import WorkflowService
            from app.models.enums import WorkflowTriggerType
            WorkflowService(self.db, self.agency_id).trigger_event(
                trigger_type=WorkflowTriggerType.FEEDBACK_SUBMITTED,
                entity_type="interview",
                entity_id=interview.id,
                override_context={"overall_rating": data.overall_rating, "recommendation": data.recommendation.value},
                current_user=current_user,
            )
        except Exception:
            pass

        return InterviewFeedbackRead(
            id=feedback.id,
            interview_id=feedback.interview_id,
            reviewer_id=feedback.reviewer_id,
            reviewer_name=current_user.full_name,
            reviewer_role=current_user.role.value,
            overall_rating=feedback.overall_rating,
            recommendation=feedback.recommendation,
            technical_assessment=feedback.technical_assessment,
            communication_assessment=feedback.communication_assessment,
            problem_solving_assessment=feedback.problem_solving_assessment,
            role_specific_assessment=feedback.role_specific_assessment,
            strengths=data.strengths or [],
            concerns=data.concerns or [],
            detailed_feedback=feedback.detailed_feedback,
            is_private=feedback.is_private,
            submitted_at=feedback.submitted_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )

    def update_feedback(
        self,
        interview_id: uuid.UUID,
        feedback_id: uuid.UUID,
        current_user: User,
        data: InterviewFeedbackUpdate,
    ) -> InterviewFeedbackRead:
        """Edit feedback (author or OWNER/ADMIN only)."""
        feedback = self.repo.get_feedback(feedback_id)
        if not feedback or feedback.agency_id != self.agency_id or feedback.interview_id != interview_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview feedback not found.",
            )

        # Authorization: Only original reviewer or OWNER/ADMIN can modify
        if feedback.reviewer_id != current_user.id and current_user.role not in (
            UserRole.OWNER,
            UserRole.ADMIN,
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to modify another interviewer's evaluation.",
            )

        now = utc_now()
        updated = False

        if data.overall_rating is not None:
            feedback.overall_rating = data.overall_rating
            updated = True

        if data.recommendation is not None:
            feedback.recommendation = data.recommendation
            updated = True

        if data.technical_assessment is not None:
            feedback.technical_assessment = data.technical_assessment.strip() or None
            updated = True

        if data.communication_assessment is not None:
            feedback.communication_assessment = data.communication_assessment.strip() or None
            updated = True

        if data.problem_solving_assessment is not None:
            feedback.problem_solving_assessment = data.problem_solving_assessment.strip() or None
            updated = True

        if data.role_specific_assessment is not None:
            feedback.role_specific_assessment = data.role_specific_assessment.strip() or None
            updated = True

        if data.strengths is not None:
            feedback.strengths = json.dumps(data.strengths)
            updated = True

        if data.concerns is not None:
            feedback.concerns = json.dumps(data.concerns)
            updated = True

        if data.detailed_feedback is not None:
            feedback.detailed_feedback = data.detailed_feedback.strip()
            updated = True

        if data.is_private is not None:
            feedback.is_private = data.is_private
            updated = True

        if updated:
            feedback.updated_at = now

            self.db.add(
                InterviewHistory(
                    id=uuid.uuid4(),
                    agency_id=self.agency_id,
                    interview_id=interview_id,
                    actor_id=current_user.id,
                    action="FEEDBACK_UPDATED",
                    previous_value=None,
                    new_value=json.dumps({
                        "rating": feedback.overall_rating,
                        "recommendation": feedback.recommendation.value,
                    }),
                    reason="Feedback modified by reviewer",
                    created_at=now,
                )
            )

            self.db.add(
                AuditLog(
                    agency_id=self.agency_id,
                    user_id=current_user.id,
                    action="INTERVIEW_FEEDBACK_UPDATED",
                    resource_type="interview_feedback",
                    resource_id=str(feedback.id),
                    details=json.dumps({"interview_id": str(interview_id)}),
                    created_at=now,
                )
            )

            self.db.commit()
            self.db.refresh(feedback)

        reviewer_name = feedback.reviewer.full_name if feedback.reviewer else current_user.full_name
        reviewer_role = feedback.reviewer.role.value if feedback.reviewer else current_user.role.value

        strengths_list = json.loads(feedback.strengths) if feedback.strengths else []
        concerns_list = json.loads(feedback.concerns) if feedback.concerns else []

        return InterviewFeedbackRead(
            id=feedback.id,
            interview_id=feedback.interview_id,
            reviewer_id=feedback.reviewer_id,
            reviewer_name=reviewer_name,
            reviewer_role=reviewer_role,
            overall_rating=feedback.overall_rating,
            recommendation=feedback.recommendation,
            technical_assessment=feedback.technical_assessment,
            communication_assessment=feedback.communication_assessment,
            problem_solving_assessment=feedback.problem_solving_assessment,
            role_specific_assessment=feedback.role_specific_assessment,
            strengths=strengths_list,
            concerns=concerns_list,
            detailed_feedback=feedback.detailed_feedback,
            is_private=feedback.is_private,
            submitted_at=feedback.submitted_at,
            created_at=feedback.created_at,
            updated_at=feedback.updated_at,
        )

    def list_interviews(
        self,
        application_id: Optional[uuid.UUID] = None,
        job_id: Optional[uuid.UUID] = None,
        interviewer_id: Optional[uuid.UUID] = None,
        status: Optional[InterviewStatus] = None,
        round_type: Optional[InterviewRoundType] = None,
        interview_mode: Optional[InterviewMode] = None,
        timeframe: Optional[str] = None,
        search: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
        current_user: Optional[User] = None,
    ) -> InterviewListResponse:
        """List agency interviews with filters, search, and status counters."""
        interviews, total, status_counts = self.repo.list_interviews(
            application_id=application_id,
            job_id=job_id,
            interviewer_id=interviewer_id,
            status=status,
            round_type=round_type,
            interview_mode=interview_mode,
            timeframe=timeframe,
            search=search,
            skip=skip,
            limit=limit,
        )

        items = [self._resolve_interview_read(i, current_user=current_user) for i in interviews]
        return InterviewListResponse(
            items=items,
            total=total,
            status_counts=status_counts,
        )

    def list_application_interviews(
        self, application_id: uuid.UUID, current_user: Optional[User] = None
    ) -> List[InterviewRead]:
        """Fetch all interviews for an application ordered chronologically."""
        app = self.app_repo.get(application_id)
        if not app or app.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Application not found or does not belong to your agency.",
            )

        interviews = self.repo.list_for_application(application_id)
        return [self._resolve_interview_read(i, application=app, current_user=current_user) for i in interviews]

    def list_recruiter_interviews(
        self, recruiter_id: uuid.UUID, current_user: Optional[User] = None
    ) -> List[InterviewRead]:
        """Fetch all interviews where the user is an assigned participant or creator."""
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

        interviews = self.repo.list_for_recruiter(recruiter_id)
        return [self._resolve_interview_read(i, current_user=current_user) for i in interviews]

    def get_interview_history(self, interview_id: uuid.UUID) -> List[InterviewHistoryRead]:
        """Fetch chronological event history for an interview."""
        interview = self.repo.get(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        histories = self.repo.get_history(interview_id)
        return [
            InterviewHistoryRead(
                id=h.id,
                interview_id=h.interview_id,
                actor_id=h.actor_id,
                actor_name=h.actor.full_name if h.actor else "System",
                action=h.action,
                previous_value=h.previous_value,
                new_value=h.new_value,
                reason=h.reason,
                created_at=h.created_at,
            )
            for h in histories
        ]

    def get_interview_feedbacks(
        self, interview_id: uuid.UUID, current_user: User
    ) -> List[InterviewFeedbackRead]:
        """Fetch feedbacks for an interview respecting privacy settings."""
        interview = self.repo.get(interview_id)
        if not interview or interview.agency_id != self.agency_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Interview round not found or does not belong to your agency.",
            )

        feedbacks = self.repo.get_feedbacks_for_interview(interview_id)
        result: List[InterviewFeedbackRead] = []

        for f in feedbacks:
            if f.is_private:
                can_view_private = (
                    f.reviewer_id == current_user.id
                    or current_user.role in (UserRole.OWNER, UserRole.ADMIN)
                )
                if not can_view_private:
                    continue

            reviewer_name = f.reviewer.full_name if f.reviewer else "Unknown Reviewer"
            reviewer_role = f.reviewer.role.value if f.reviewer else None
            strengths_list = json.loads(f.strengths) if f.strengths else []
            concerns_list = json.loads(f.concerns) if f.concerns else []

            result.append(
                InterviewFeedbackRead(
                    id=f.id,
                    interview_id=f.interview_id,
                    reviewer_id=f.reviewer_id,
                    reviewer_name=reviewer_name,
                    reviewer_role=reviewer_role,
                    overall_rating=f.overall_rating,
                    recommendation=f.recommendation,
                    technical_assessment=f.technical_assessment,
                    communication_assessment=f.communication_assessment,
                    problem_solving_assessment=f.problem_solving_assessment,
                    role_specific_assessment=f.role_specific_assessment,
                    strengths=strengths_list,
                    concerns=concerns_list,
                    detailed_feedback=f.detailed_feedback,
                    is_private=f.is_private,
                    submitted_at=f.submitted_at,
                    created_at=f.created_at,
                    updated_at=f.updated_at,
                )
            )

        return result
