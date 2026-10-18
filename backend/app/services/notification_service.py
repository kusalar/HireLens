import uuid
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.entities import User, Agency
from app.models.enums import (
    UserRole,
    NotificationType,
    NotificationDeliveryStatus,
    PipelineStageType,
)
from app.models.notification import (
    Notification,
    NotificationPreference,
    EmailDeliveryLog,
    NotificationOutbox,
)
from app.models.interview import Interview
from app.models.application import Application
from app.models.base import utc_now
from app.core.timezone import DEFAULT_TIMEZONE, validate_timezone
from app.repositories.notification_repo import NotificationRepository
from app.services.email.base import EmailMessage
from app.services.email.factory import get_email_provider
from app.services.email.templates import (
    render_interview_invitation,
    render_interview_rescheduled,
    render_interview_confirmed,
    render_interview_cancelled,
    render_application_status_update,
)

logger = logging.getLogger(__name__)


def is_redis_available(host: str = "127.0.0.1", port: int = 6379, timeout: float = 0.05) -> bool:
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(timeout)
        err = s.connect_ex((host, port))
        s.close()
        return err == 0
    except Exception:
        return False


class NotificationService:
    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id
        self.repo = NotificationRepository(db, agency_id)

    # ------------------------------------------------------------------
    # Notification Center
    # ------------------------------------------------------------------
    def list_user_notifications(
        self,
        current_user: User,
        unread_only: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[Notification], int]:
        return self.repo.list_for_user(
            recipient_user_id=current_user.id,
            unread_only=unread_only,
            skip=skip,
            limit=limit,
        )

    def get_unread_count(self, current_user: User) -> int:
        return self.repo.count_unread_for_user(recipient_user_id=current_user.id)

    def mark_as_read(self, notification_id: uuid.UUID, current_user: User) -> Notification:
        notif = self.repo.mark_as_read(notification_id, current_user.id)
        if not notif:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Notification not found or access denied.",
            )
        self.db.commit()
        return notif

    def mark_all_read(self, current_user: User) -> int:
        count = self.repo.mark_all_read(current_user.id)
        self.db.commit()
        return count

    # ------------------------------------------------------------------
    # Notification Preferences
    # ------------------------------------------------------------------
    def get_preferences(self, current_user: User) -> NotificationPreference:
        return self.repo.get_or_create_preferences()

    def update_preferences(
        self,
        current_user: User,
        email_enabled: Optional[bool] = None,
        interview_notifications_enabled: Optional[bool] = None,
        application_status_notifications_enabled: Optional[bool] = None,
        candidate_email_updates_enabled: Optional[bool] = None,
        default_timezone: Optional[str] = None,
    ) -> NotificationPreference:
        if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OWNER or ADMIN users can configure agency notification settings.",
            )

        pref = self.repo.get_or_create_preferences()

        if email_enabled is not None:
            pref.email_enabled = email_enabled
        if interview_notifications_enabled is not None:
            pref.interview_notifications_enabled = interview_notifications_enabled
        if application_status_notifications_enabled is not None:
            pref.application_status_notifications_enabled = application_status_notifications_enabled
        if candidate_email_updates_enabled is not None:
            pref.candidate_email_updates_enabled = candidate_email_updates_enabled
        if default_timezone is not None:
            validate_timezone(default_timezone)
            pref.default_timezone = default_timezone.strip()

        self.db.commit()
        self.db.refresh(pref)
        return pref

    # ------------------------------------------------------------------
    # Delivery Logs
    # ------------------------------------------------------------------
    def list_delivery_logs(
        self,
        current_user: User,
        status_filter: Optional[NotificationDeliveryStatus] = None,
        event_type: Optional[str] = None,
        recipient_email: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[EmailDeliveryLog], int]:
        if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OWNER or ADMIN users can view email delivery logs.",
            )

        return self.repo.list_delivery_logs(
            status=status_filter,
            event_type=event_type,
            recipient_email=recipient_email,
            skip=skip,
            limit=limit,
        )

    def retry_delivery_log(self, log_id: uuid.UUID, current_user: User) -> EmailDeliveryLog:
        if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only OWNER or ADMIN users can retry failed delivery logs.",
            )

        log = (
            self.db.query(EmailDeliveryLog)
            .filter(
                EmailDeliveryLog.id == log_id,
                EmailDeliveryLog.agency_id == self.agency_id,
            )
            .first()
        )
        if not log:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Delivery log not found.",
            )

        # Locate associated outbox item by idempotency_key
        outbox = self.repo.get_outbox_by_idempotency_key(log.idempotency_key)
        if outbox:
            outbox.status = NotificationDeliveryStatus.PENDING
            outbox.attempt_count = 0
            outbox.next_retry_at = utc_now()
            outbox.last_error = None
            self.db.commit()
            # Attempt dispatch
            self.dispatch_outbox_item(outbox.id)
            self.db.refresh(log)
            return log

        # If outbox entry was already cleaned up, re-attempt log via email provider directly
        provider = get_email_provider()
        msg = EmailMessage(
            to_email=log.recipient_email,
            subject=log.subject,
            body_html=f"<p>Retried notification: {log.subject}</p>",
            body_text=f"Retried notification: {log.subject}",
        )
        success, error = provider.send_email(msg)
        now = utc_now()
        log.attempt_count += 1
        log.last_attempt_at = now
        if success:
            log.status = NotificationDeliveryStatus.SENT
            log.delivered_at = now
            log.error_message = None
        else:
            log.status = NotificationDeliveryStatus.FAILED
            log.error_message = error
        self.db.commit()
        return log

    # ------------------------------------------------------------------
    # Transactional Outbox Processing
    # ------------------------------------------------------------------
    def dispatch_outbox_item(self, outbox_id: uuid.UUID) -> bool:
        """Process a single outbox record with bounded retries and exponential backoff."""
        outbox = self.db.query(NotificationOutbox).filter(
            NotificationOutbox.id == outbox_id,
            NotificationOutbox.agency_id == self.agency_id,
        ).first()

        if not outbox or outbox.status == NotificationDeliveryStatus.SENT:
            return True

        provider = get_email_provider()
        message = EmailMessage(
            to_email=outbox.recipient_email,
            to_name=outbox.recipient_name,
            subject=outbox.subject,
            body_html=outbox.body_html,
            body_text=outbox.body_text,
        )

        outbox.attempt_count += 1
        now = utc_now()

        success, err = provider.send_email(message)

        if success:
            outbox.status = NotificationDeliveryStatus.SENT
            outbox.last_error = None
            self.repo.record_delivery_log(
                recipient_email=outbox.recipient_email,
                event_type=outbox.event_type,
                subject=outbox.subject,
                provider=provider.name,
                status=NotificationDeliveryStatus.SENT,
                idempotency_key=outbox.idempotency_key,
                attempt_count=outbox.attempt_count,
                delivered_at=now,
                error_message=None,
            )
            self.db.commit()
            return True
        else:
            safe_err = err or "Unknown email delivery failure"
            if outbox.attempt_count >= outbox.max_retries:
                outbox.status = NotificationDeliveryStatus.DEAD_LETTER
            else:
                outbox.status = NotificationDeliveryStatus.FAILED
                # Exponential backoff: attempt 1 -> 10s, attempt 2 -> 30s, attempt 3 -> 90s
                backoff_delay = 10 * (3 ** (outbox.attempt_count - 1))
                outbox.next_retry_at = now + timedelta(seconds=backoff_delay)

            outbox.last_error = safe_err
            self.repo.record_delivery_log(
                recipient_email=outbox.recipient_email,
                event_type=outbox.event_type,
                subject=outbox.subject,
                provider=provider.name,
                status=outbox.status,
                idempotency_key=outbox.idempotency_key,
                attempt_count=outbox.attempt_count,
                delivered_at=None,
                error_message=safe_err,
            )
            self.db.commit()
            return False

    def process_pending_outbox(self, limit: int = 25) -> int:
        """Process all pending outbox entries ready for retry."""
        items = self.repo.get_pending_outbox_items(limit=limit)
        sent_count = 0
        for item in items:
            if self.dispatch_outbox_item(item.id):
                sent_count += 1
        return sent_count

    def _trigger_background_delivery(self, outbox_id: uuid.UUID):
        """Asynchronously dispatch outbox email using Celery if Redis is available, or deliver directly."""
        if is_redis_available():
            try:
                from app.tasks.notification_tasks import dispatch_outbox_email_task
                dispatch_outbox_email_task.apply_async(
                    args=[str(outbox_id), str(self.agency_id)],
                    retry=False,
                )
                return
            except Exception as exc:
                logger.warning("Could not dispatch outbox task to Celery: %s", exc)

        # Fallback to direct synchronous execution if Celery broker is offline
        try:
            self.dispatch_outbox_item(outbox_id)
        except Exception as exc:
            logger.error("Synchronous outbox dispatch failed: %s", exc)

    # ------------------------------------------------------------------
    # High-Level Event Integrations
    # ------------------------------------------------------------------
    def on_interview_scheduled(self, interview: Interview, application: Application, creator: User):
        """Triggered after an interview round is successfully scheduled."""
        try:
            prefs = self.repo.get_or_create_preferences()
            if not prefs.interview_notifications_enabled:
                return

            agency = self.db.query(Agency).filter(Agency.id == self.agency_id).first()
            agency_name = agency.name if agency else "HireLens Agency"
            job_title = application.job.title if application.job else "Position"
            cand_name = application.candidate.full_name if application.candidate else "Candidate"
            cand_email = application.candidate.email if application.candidate else None

            # 1. In-App Notifications for internal participants & creator
            notified_user_ids = set()
            for p in interview.participants:
                if p.user_id and p.user_id not in notified_user_ids:
                    notified_user_ids.add(p.user_id)
                    self.repo.create_notification(
                        recipient_user_id=p.user_id,
                        notification_type=NotificationType.INTERVIEW_SCHEDULED,
                        title=f"Interview Scheduled: {interview.round_name}",
                        message=f"You are scheduled for '{interview.round_name}' with {cand_name} for '{job_title}'.",
                        related_entity_type="interview",
                        related_entity_id=interview.id,
                    )

            if creator.id not in notified_user_ids:
                self.repo.create_notification(
                    recipient_user_id=creator.id,
                    notification_type=NotificationType.INTERVIEW_SCHEDULED,
                    title=f"Interview Scheduled: {interview.round_name}",
                    message=f"You scheduled '{interview.round_name}' with {cand_name} for '{job_title}'.",
                    related_entity_type="interview",
                    related_entity_id=interview.id,
                )

            # 2. Email Outbox for Candidate (if candidate updates enabled & email enabled)
            outbox_entries = []
            if prefs.email_enabled and prefs.candidate_email_updates_enabled and cand_email:
                cand_subj, cand_html, cand_text = render_interview_invitation(
                    recipient_name=cand_name,
                    job_title=job_title,
                    round_name=interview.round_name,
                    start_utc=interview.scheduled_start,
                    end_utc=interview.scheduled_end,
                    interview_mode=interview.interview_mode.value,
                    meeting_url=interview.meeting_url,
                    location=interview.location,
                    agency_name=agency_name,
                    is_candidate=True,
                )
                idempotency_key = f"invitation_{interview.id}_{cand_email}_{int(interview.scheduled_start.timestamp())}"
                out_cand = self.repo.enqueue_outbox(
                    event_type="INTERVIEW_SCHEDULED",
                    idempotency_key=idempotency_key,
                    recipient_email=cand_email,
                    recipient_name=cand_name,
                    subject=cand_subj,
                    body_html=cand_html,
                    body_text=cand_text,
                )
                if out_cand:
                    outbox_entries.append(out_cand)

            # 3. Email Outbox for Interviewers
            if prefs.email_enabled:
                for p in interview.participants:
                    if p.participant_email and p.participant_email.lower() != (cand_email or "").lower():
                        int_subj, int_html, int_text = render_interview_invitation(
                            recipient_name=p.participant_name,
                            job_title=job_title,
                            round_name=interview.round_name,
                            start_utc=interview.scheduled_start,
                            end_utc=interview.scheduled_end,
                            interview_mode=interview.interview_mode.value,
                            meeting_url=interview.meeting_url,
                            location=interview.location,
                            agency_name=agency_name,
                            is_candidate=False,
                        )
                        idempotency_key = f"invitation_{interview.id}_{p.participant_email.lower()}_{int(interview.scheduled_start.timestamp())}"
                        out_int = self.repo.enqueue_outbox(
                            event_type="INTERVIEW_SCHEDULED",
                            idempotency_key=idempotency_key,
                            recipient_email=p.participant_email,
                            recipient_name=p.participant_name,
                            subject=int_subj,
                            body_html=int_html,
                            body_text=int_text,
                        )
                        if out_int:
                            outbox_entries.append(out_int)

            self.db.commit()

            # Trigger background delivery for outbox items
            for out in outbox_entries:
                self._trigger_background_delivery(out.id)
        except Exception as exc:
            logger.error("Error in on_interview_scheduled notification hook: %s", exc, exc_info=True)

    def on_interview_rescheduled(
        self,
        interview: Interview,
        application: Application,
        actor: User,
        old_start: datetime,
        old_end: datetime,
        reason: Optional[str] = None,
    ):
        """Triggered after an interview is successfully rescheduled."""
        try:
            prefs = self.repo.get_or_create_preferences()
            if not prefs.interview_notifications_enabled:
                return

            agency = self.db.query(Agency).filter(Agency.id == self.agency_id).first()
            agency_name = agency.name if agency else "HireLens Agency"
            job_title = application.job.title if application.job else "Position"
            cand_name = application.candidate.full_name if application.candidate else "Candidate"
            cand_email = application.candidate.email if application.candidate else None

            # 1. In-App Notifications
            notified_user_ids = set()
            for p in interview.participants:
                if p.user_id and p.user_id not in notified_user_ids:
                    notified_user_ids.add(p.user_id)
                    self.repo.create_notification(
                        recipient_user_id=p.user_id,
                        notification_type=NotificationType.INTERVIEW_RESCHEDULED,
                        title=f"Interview Rescheduled: {interview.round_name}",
                        message=f"Interview '{interview.round_name}' for '{job_title}' was rescheduled by {actor.full_name}.",
                        related_entity_type="interview",
                        related_entity_id=interview.id,
                    )

            # 2. Email Outbox Entries
            outbox_entries = []
            recipients = []
            if prefs.candidate_email_updates_enabled and cand_email:
                recipients.append((cand_name, cand_email))

            for p in interview.participants:
                if p.participant_email and p.participant_email.lower() != (cand_email or "").lower():
                    recipients.append((p.participant_name, p.participant_email))

            if prefs.email_enabled:
                for name, email in recipients:
                    subj, html_content, text_content = render_interview_rescheduled(
                        recipient_name=name,
                        job_title=job_title,
                        round_name=interview.round_name,
                        new_start_utc=interview.scheduled_start,
                        new_end_utc=interview.scheduled_end,
                        old_start_utc=old_start,
                        old_end_utc=old_end,
                        reason=reason,
                        meeting_url=interview.meeting_url,
                        agency_name=agency_name,
                    )
                    idempotency_key = f"rescheduled_{interview.id}_{email.lower()}_{int(interview.scheduled_start.timestamp())}"
                    out = self.repo.enqueue_outbox(
                        event_type="INTERVIEW_RESCHEDULED",
                        idempotency_key=idempotency_key,
                        recipient_email=email,
                        recipient_name=name,
                        subject=subj,
                        body_html=html_content,
                        body_text=text_content,
                    )
                    if out:
                        outbox_entries.append(out)

            self.db.commit()
            for out in outbox_entries:
                self._trigger_background_delivery(out.id)
        except Exception as exc:
            logger.error("Error in on_interview_rescheduled notification hook: %s", exc, exc_info=True)

    def on_interview_confirmed(self, interview: Interview, application: Application, actor: User):
        """Triggered after an interview status transitions to CONFIRMED."""
        try:
            prefs = self.repo.get_or_create_preferences()
            if not prefs.interview_notifications_enabled:
                return

            agency = self.db.query(Agency).filter(Agency.id == self.agency_id).first()
            agency_name = agency.name if agency else "HireLens Agency"
            job_title = application.job.title if application.job else "Position"
            cand_name = application.candidate.full_name if application.candidate else "Candidate"
            cand_email = application.candidate.email if application.candidate else None

            notified_user_ids = set()
            for p in interview.participants:
                if p.user_id and p.user_id not in notified_user_ids:
                    notified_user_ids.add(p.user_id)
                    self.repo.create_notification(
                        recipient_user_id=p.user_id,
                        notification_type=NotificationType.INTERVIEW_CONFIRMED,
                        title=f"Interview Confirmed: {interview.round_name}",
                        message=f"Interview '{interview.round_name}' for '{job_title}' with {cand_name} is confirmed.",
                        related_entity_type="interview",
                        related_entity_id=interview.id,
                    )

            outbox_entries = []
            recipients = []
            if prefs.candidate_email_updates_enabled and cand_email:
                recipients.append((cand_name, cand_email))
            for p in interview.participants:
                if p.participant_email and p.participant_email.lower() != (cand_email or "").lower():
                    recipients.append((p.participant_name, p.participant_email))

            if prefs.email_enabled:
                for name, email in recipients:
                    subj, html_content, text_content = render_interview_confirmed(
                        recipient_name=name,
                        job_title=job_title,
                        round_name=interview.round_name,
                        start_utc=interview.scheduled_start,
                        end_utc=interview.scheduled_end,
                        agency_name=agency_name,
                    )
                    idempotency_key = f"confirmed_{interview.id}_{email.lower()}"
                    out = self.repo.enqueue_outbox(
                        event_type="INTERVIEW_CONFIRMED",
                        idempotency_key=idempotency_key,
                        recipient_email=email,
                        recipient_name=name,
                        subject=subj,
                        body_html=html_content,
                        body_text=text_content,
                    )
                    if out:
                        outbox_entries.append(out)

            self.db.commit()
            for out in outbox_entries:
                self._trigger_background_delivery(out.id)
        except Exception as exc:
            logger.error("Error in on_interview_confirmed notification hook: %s", exc, exc_info=True)

    def on_interview_cancelled(self, interview: Interview, application: Application, actor: User, reason: Optional[str] = None):
        """Triggered after an interview status transitions to CANCELLED."""
        try:
            prefs = self.repo.get_or_create_preferences()
            if not prefs.interview_notifications_enabled:
                return

            agency = self.db.query(Agency).filter(Agency.id == self.agency_id).first()
            agency_name = agency.name if agency else "HireLens Agency"
            job_title = application.job.title if application.job else "Position"
            cand_name = application.candidate.full_name if application.candidate else "Candidate"
            cand_email = application.candidate.email if application.candidate else None

            notified_user_ids = set()
            for p in interview.participants:
                if p.user_id and p.user_id not in notified_user_ids:
                    notified_user_ids.add(p.user_id)
                    self.repo.create_notification(
                        recipient_user_id=p.user_id,
                        notification_type=NotificationType.INTERVIEW_CANCELLED,
                        title=f"Interview Cancelled: {interview.round_name}",
                        message=f"Interview '{interview.round_name}' for '{job_title}' was cancelled by {actor.full_name}.",
                        related_entity_type="interview",
                        related_entity_id=interview.id,
                    )

            outbox_entries = []
            recipients = []
            if prefs.candidate_email_updates_enabled and cand_email:
                recipients.append((cand_name, cand_email))
            for p in interview.participants:
                if p.participant_email and p.participant_email.lower() != (cand_email or "").lower():
                    recipients.append((p.participant_name, p.participant_email))

            if prefs.email_enabled:
                for name, email in recipients:
                    subj, html_content, text_content = render_interview_cancelled(
                        recipient_name=name,
                        job_title=job_title,
                        round_name=interview.round_name,
                        start_utc=interview.scheduled_start,
                        end_utc=interview.scheduled_end,
                        reason=reason,
                        agency_name=agency_name,
                    )
                    idempotency_key = f"cancelled_{interview.id}_{email.lower()}"
                    out = self.repo.enqueue_outbox(
                        event_type="INTERVIEW_CANCELLED",
                        idempotency_key=idempotency_key,
                        recipient_email=email,
                        recipient_name=name,
                        subject=subj,
                        body_html=html_content,
                        body_text=text_content,
                    )
                    if out:
                        outbox_entries.append(out)

            self.db.commit()
            for out in outbox_entries:
                self._trigger_background_delivery(out.id)
        except Exception as exc:
            logger.error("Error in on_interview_cancelled notification hook: %s", exc, exc_info=True)

    def on_interview_completed(self, interview: Interview, application: Application, actor: User):
        """Triggered after an interview status transitions to COMPLETED."""
        try:
            prefs = self.repo.get_or_create_preferences()
            if not prefs.interview_notifications_enabled:
                return

            job_title = application.job.title if application.job else "Position"
            cand_name = application.candidate.full_name if application.candidate else "Candidate"

            # In-app notification for interviewers / recruiters to submit feedback
            notified_user_ids = set()
            for p in interview.participants:
                if p.user_id and p.user_id not in notified_user_ids:
                    notified_user_ids.add(p.user_id)
                    self.repo.create_notification(
                        recipient_user_id=p.user_id,
                        notification_type=NotificationType.INTERVIEW_COMPLETED,
                        title=f"Interview Completed: {interview.round_name}",
                        message=f"Interview round '{interview.round_name}' with {cand_name} is complete. Please submit your evaluation.",
                        related_entity_type="interview",
                        related_entity_id=interview.id,
                    )

            self.db.commit()
        except Exception as exc:
            logger.error("Error in on_interview_completed notification hook: %s", exc, exc_info=True)

    def on_application_stage_changed(
        self,
        application: Application,
        actor: User,
        old_stage: PipelineStageType,
        new_stage: PipelineStageType,
        reason: Optional[str] = None,
    ):
        """Triggered after an application pipeline stage change commits."""
        try:
            prefs = self.repo.get_or_create_preferences()
            if not prefs.application_status_notifications_enabled:
                return

            agency = self.db.query(Agency).filter(Agency.id == self.agency_id).first()
            agency_name = agency.name if agency else "HireLens Agency"
            job_title = application.job.title if application.job else "Position"
            cand_name = application.candidate.full_name if application.candidate else "Candidate"
            cand_email = application.candidate.email if application.candidate else None

            # 1. In-app notification for assigned recruiter if different from actor
            if application.assigned_recruiter_id and application.assigned_recruiter_id != actor.id:
                self.repo.create_notification(
                    recipient_user_id=application.assigned_recruiter_id,
                    notification_type=NotificationType.APPLICATION_STATUS_UPDATED,
                    title=f"Stage Changed: {cand_name}",
                    message=f"Application for {cand_name} ({job_title}) was moved to '{new_stage.value}' by {actor.full_name}.",
                    related_entity_type="application",
                    related_entity_id=application.id,
                )

            # 2. Candidate-facing notification email if enabled by agency settings
            outbox_entry = None
            if prefs.email_enabled and prefs.candidate_email_updates_enabled and cand_email:
                subj, html_content, text_content = render_application_status_update(
                    recipient_name=cand_name,
                    job_title=job_title,
                    new_stage=new_stage.value,
                    agency_name=agency_name,
                    is_candidate=True,
                )
                idempotency_key = f"app_stage_{application.id}_{new_stage.value}_{int(application.updated_at.timestamp()) if application.updated_at else 0}"
                outbox_entry = self.repo.enqueue_outbox(
                    event_type="APPLICATION_STATUS_UPDATED",
                    idempotency_key=idempotency_key,
                    recipient_email=cand_email,
                    recipient_name=cand_name,
                    subject=subj,
                    body_html=html_content,
                    body_text=text_content,
                )

            self.db.commit()
            if outbox_entry:
                self._trigger_background_delivery(outbox_entry.id)
        except Exception as exc:
            logger.error("Error in on_application_stage_changed notification hook: %s", exc, exc_info=True)
