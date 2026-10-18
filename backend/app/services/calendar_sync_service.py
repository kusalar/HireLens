import uuid
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional

from sqlalchemy.orm import Session
from sqlalchemy import select, and_, or_, update
from fastapi import HTTPException, status

from app.core.config import settings
from app.core.security import encrypt_token, decrypt_token
from app.core.timezone import parse_and_normalize_to_utc, convert_utc_to_timezone, DEFAULT_TIMEZONE
from app.models.enums import (

    CalendarProviderType,
    CalendarSyncStatus,
    CalendarSyncDirection,
    CalendarSyncOperation,
    MeetingProviderType,
    InterviewStatus,
)
from app.models.calendar import (
    CalendarConnection,
    CalendarEventMapping,
    CalendarSyncJob,
    CalendarSyncLog,
    CalendarWebhookSubscription,
)
from app.models.interview import Interview, InterviewParticipant
from app.models.entities import User
from app.services.calendar.base import (
    BaseCalendarProvider,
    CalendarEventResult,
    CalendarAuthException,
    CalendarRateLimitException,
    CalendarProviderException,
)
from app.services.calendar.factory import get_calendar_provider

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


class CalendarSyncService:

    """
    Comprehensive multi-tenant calendar integration and synchronization service.
    Coordinates OAuth connections, token encryption, durable outbox jobs, two-way sync,
    and safe conflict-checked interview rescheduling.
    """

    def __init__(self, db: Session, agency_id: uuid.UUID):
        self.db = db
        self.agency_id = agency_id

    # -------------------------------------------------------------------------
    # OAuth Connection Management
    # -------------------------------------------------------------------------

    def get_oauth_authorization_url(
        self,
        provider_type: CalendarProviderType,
        user_id: uuid.UUID,
        redirect_uri: Optional[str] = None,
    ) -> Dict[str, str]:
        """Generate secure OAuth authorization URL with signed state containing user and agency."""
        state_payload = {
            "agency_id": str(self.agency_id),
            "user_id": str(user_id),
            "provider": provider_type.value,
            "nonce": uuid.uuid4().hex,
            "exp": (datetime.now(timezone.utc) + timedelta(minutes=15)).timestamp(),
        }
        state_str = encrypt_token(json.dumps(state_payload))
        provider = get_calendar_provider(provider_type)

        target_redirect = redirect_uri
        if not target_redirect:
            if provider_type == CalendarProviderType.GOOGLE:
                target_redirect = settings.GOOGLE_REDIRECT_URI
            else:
                target_redirect = settings.MICROSOFT_REDIRECT_URI

        auth_url = provider.get_authorization_url(state=state_str, redirect_uri=target_redirect)
        return {
            "authorization_url": auth_url,
            "state": state_str,
        }

    def handle_oauth_callback(
        self,
        code: str,
        state: str,
        current_user: User,
        redirect_uri: Optional[str] = None,
    ) -> CalendarConnection:
        """
        Validate OAuth state, exchange authorization code, encrypt tokens,
        and persist/update the user's CalendarConnection.
        """
        if not state:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing OAuth state parameter.")

        try:
            state_json = decrypt_token(state)
            if not state_json:
                raise ValueError("State decryption resulted in empty payload")
            state_data = json.loads(state_json)
        except Exception:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid or tampered OAuth state parameter.")

        if state_data.get("agency_id") != str(self.agency_id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-agency OAuth callback attempt rejected.")
        if state_data.get("user_id") != str(current_user.id):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="OAuth user mismatch.")

        provider_name = state_data.get("provider", "mock").upper()
        try:
            provider_type = CalendarProviderType(provider_name)
        except ValueError:
            provider_type = CalendarProviderType.MOCK

        provider = get_calendar_provider(provider_type)

        target_redirect = redirect_uri
        if not target_redirect:
            if provider_type == CalendarProviderType.GOOGLE:
                target_redirect = settings.GOOGLE_REDIRECT_URI
            else:
                target_redirect = settings.MICROSOFT_REDIRECT_URI

        token_result = provider.exchange_code_for_tokens(code=code, redirect_uri=target_redirect)
        access_token = token_result.get("access_token")
        refresh_token = token_result.get("refresh_token")
        expires_in = token_result.get("expires_in", 3600)
        account_id = token_result.get("account_id")
        account_email = token_result.get("account_email") or current_user.email

        expires_at = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

        # Check existing connection
        stmt = select(CalendarConnection).where(
            CalendarConnection.agency_id == self.agency_id,
            CalendarConnection.user_id == current_user.id,
            CalendarConnection.provider == provider_type,
        )
        conn = self.db.scalars(stmt).first()

        now = datetime.now(timezone.utc)
        if not conn:
            conn = CalendarConnection(
                agency_id=self.agency_id,
                user_id=current_user.id,
                provider=provider_type,
                provider_account_id=account_id,
                provider_account_email=account_email,
                encrypted_access_token=encrypt_token(access_token),
                encrypted_refresh_token=encrypt_token(refresh_token) if refresh_token else None,
                access_token_expires_at=expires_at,
                selected_calendar_id="primary",
                selected_calendar_name="Primary Calendar",
                is_active=True,
                created_at=now,
                updated_at=now,
            )
            self.db.add(conn)
        else:
            conn.encrypted_access_token = encrypt_token(access_token)
            if refresh_token:
                conn.encrypted_refresh_token = encrypt_token(refresh_token)
            conn.access_token_expires_at = expires_at
            conn.provider_account_id = account_id or conn.provider_account_id
            conn.provider_account_email = account_email or conn.provider_account_email
            conn.is_active = True
            conn.last_error = None
            conn.updated_at = now

        self.db.commit()
        self.db.refresh(conn)

        # Retrieve available calendars to set the primary name if possible
        try:
            calendars = provider.list_calendars(access_token)
            if calendars:
                primary = next((c for c in calendars if c.get("primary")), calendars[0])
                conn.selected_calendar_id = primary.get("id", "primary")
                conn.selected_calendar_name = primary.get("name", "Primary Calendar")
                self.db.commit()
                self.db.refresh(conn)
        except Exception as e:
            logger.warning("Could not pre-fetch calendar list for connection %s: %s", conn.id, e)

        return conn

    def list_connections(self, user_id: Optional[uuid.UUID] = None) -> List[CalendarConnection]:
        """List active connections for an agency or specific user."""
        stmt = select(CalendarConnection).where(CalendarConnection.agency_id == self.agency_id)
        if user_id:
            stmt = stmt.where(CalendarConnection.user_id == user_id)
        return list(self.db.scalars(stmt).all())

    def get_connection(self, connection_id: uuid.UUID) -> Optional[CalendarConnection]:
        """Get single calendar connection enforcing tenant isolation."""
        stmt = select(CalendarConnection).where(
            CalendarConnection.id == connection_id,
            CalendarConnection.agency_id == self.agency_id,
        )
        return self.db.scalars(stmt).first()

    def disconnect_connection(self, connection_id: uuid.UUID, current_user: User) -> bool:
        """Disconnect and securely clean up external credentials."""
        conn = self.get_connection(connection_id)
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar connection not found.")

        # Recruiter can disconnect their own; OWNER/ADMIN can disconnect any in agency
        if current_user.role.value not in ("OWNER", "ADMIN") and conn.user_id != current_user.id:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to disconnect this connection.")

        conn.is_active = False
        conn.encrypted_access_token = None
        conn.encrypted_refresh_token = None
        conn.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        return True

    def list_connection_calendars(self, connection_id: uuid.UUID) -> List[Dict[str, Any]]:
        """List available calendars for the specified connection."""
        conn = self.get_connection(connection_id)
        if not conn or not conn.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active calendar connection not found.")

        token = self._ensure_valid_access_token(conn)
        provider = get_calendar_provider(conn.provider)
        return provider.list_calendars(token)

    def update_selected_calendar(self, connection_id: uuid.UUID, calendar_id: str, calendar_name: str) -> CalendarConnection:
        """Change the selected target calendar for future interview synchronization."""
        conn = self.get_connection(connection_id)
        if not conn or not conn.is_active:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Active calendar connection not found.")

        conn.selected_calendar_id = calendar_id
        conn.selected_calendar_name = calendar_name
        conn.updated_at = datetime.now(timezone.utc)
        self.db.commit()
        self.db.refresh(conn)
        return conn

    # -------------------------------------------------------------------------
    # Token Management
    # -------------------------------------------------------------------------

    def _ensure_valid_access_token(self, conn: CalendarConnection) -> str:
        """Decrypt and return valid access token, auto-refreshing if expired."""
        if not conn.encrypted_access_token:
            raise CalendarAuthException("No access token found for connection.")

        access_token = decrypt_token(conn.encrypted_access_token)
        now = datetime.now(timezone.utc)

        # If expired or expiring within 60 seconds, attempt refresh
        expires_at = conn.access_token_expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if expires_at and expires_at <= (now + timedelta(seconds=60)):
            if not conn.encrypted_refresh_token:
                raise CalendarAuthException("Access token expired and no refresh token available.")


            refresh_token = decrypt_token(conn.encrypted_refresh_token)
            provider = get_calendar_provider(conn.provider)
            try:
                refreshed = provider.refresh_tokens(refresh_token)
                new_access = refreshed["access_token"]
                new_refresh = refreshed.get("refresh_token") or refresh_token
                expires_in = refreshed.get("expires_in", 3600)

                conn.encrypted_access_token = encrypt_token(new_access)
                conn.encrypted_refresh_token = encrypt_token(new_refresh)
                conn.access_token_expires_at = now + timedelta(seconds=expires_in)
                conn.updated_at = now
                self.db.commit()
                return new_access
            except CalendarAuthException as e:
                conn.is_active = False
                conn.last_error = f"Authentication revoked: {str(e)}"
                conn.updated_at = now
                self.db.commit()
                raise e

        return access_token

    # -------------------------------------------------------------------------
    # Durable Outbox Synchronization Jobs
    # -------------------------------------------------------------------------

    def enqueue_sync_job(
        self,
        connection_id: uuid.UUID,
        interview_id: uuid.UUID,
        operation: CalendarSyncOperation,
        generate_meeting: bool = False,
    ) -> Optional[CalendarSyncJob]:
        """
        Durable outbox pattern: persist a pending sync job in the database.
        Committed atomically with interview actions.
        """
        now = datetime.now(timezone.utc)
        idempotency_key = f"{interview_id}_{connection_id}_{operation.value}_{uuid.uuid4().hex[:8]}"

        payload = json.dumps({"generate_meeting": generate_meeting})

        job = CalendarSyncJob(
            agency_id=self.agency_id,
            connection_id=connection_id,
            interview_id=interview_id,
            operation=operation,
            status="PENDING",
            attempt_count=0,
            max_attempts=5,
            idempotency_key=idempotency_key,
            scheduled_at=now,
            payload=payload,
            created_at=now,
            updated_at=now,
        )
        self.db.add(job)
        self.db.commit()
        # Asynchronously dispatch via Celery if Redis is available
        if is_redis_available():
            try:
                from app.tasks.calendar_tasks import dispatch_calendar_sync_job_task
                dispatch_calendar_sync_job_task.apply_async(
                    args=[str(job.id), str(self.agency_id)],
                    retry=False,
                )
            except Exception:
                pass

        return job


    def process_sync_job(self, job_id: uuid.UUID) -> bool:
        """
        Process a single durable calendar sync job.
        Implements bounded retries, rate-limit awareness, and idempotency.
        """
        stmt = select(CalendarSyncJob).where(
            CalendarSyncJob.id == job_id,
            CalendarSyncJob.agency_id == self.agency_id,
        )
        job = self.db.scalars(stmt).first()
        if not job or job.status in ("COMPLETED", "DEAD_LETTER"):
            return True

        job.status = "PROCESSING"
        job.attempt_count += 1
        job.last_attempt_at = datetime.now(timezone.utc)
        self.db.commit()

        conn = self.get_connection(job.connection_id)
        if not conn or not conn.is_active:
            job.status = "FAILED"
            job.last_error = "Connection is inactive or missing."
            self.db.commit()
            return False

        interview_stmt = select(Interview).where(
            Interview.id == job.interview_id,
            Interview.agency_id == self.agency_id,
        )
        interview = self.db.scalars(interview_stmt).first()
        if not interview:
            job.status = "FAILED"
            job.last_error = "Interview record not found."
            self.db.commit()
            return False

        # Parse job payload
        payload_data = {}
        if job.payload:
            try:
                payload_data = json.loads(job.payload)
            except Exception:
                pass
        generate_meeting = payload_data.get("generate_meeting", False)

        provider = get_calendar_provider(conn.provider)
        try:
            access_token = self._ensure_valid_access_token(conn)
            now = datetime.now(timezone.utc)

            if job.operation == CalendarSyncOperation.CREATE:
                self._execute_create_event(conn, interview, provider, access_token, generate_meeting)
            elif job.operation == CalendarSyncOperation.UPDATE:
                self._execute_update_event(conn, interview, provider, access_token)
            elif job.operation == CalendarSyncOperation.CANCEL:
                self._execute_cancel_event(conn, interview, provider, access_token)

            job.status = "COMPLETED"
            job.last_error = None
            conn.last_synced_at = now
            conn.last_error = None
            self.db.commit()

            # Record success log
            self._log_sync_action(
                connection_id=conn.id,
                interview_id=interview.id,
                direction=CalendarSyncDirection.OUTBOUND,
                operation=job.operation,
                status="SUCCESS",
                details=f"Successfully executed {job.operation.value} for interview {interview.id}",
            )
            return True

        except (CalendarRateLimitException, CalendarProviderException) as e:
            logger.warning("Transient calendar sync failure for job %s: %s", job.id, e)
            job.last_error = str(e)
            retry_seconds = getattr(e, "retry_after", None) or (2 ** job.attempt_count * 5)
            if job.attempt_count >= job.max_attempts:
                job.status = "DEAD_LETTER"
            else:
                job.status = "PENDING"
                job.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=retry_seconds)

            conn.last_error = str(e)
            self.db.commit()

            self._log_sync_action(
                connection_id=conn.id,
                interview_id=interview.id,
                direction=CalendarSyncDirection.OUTBOUND,
                operation=job.operation,
                status="FAILED",
                error_message=str(e),
            )
            return False

        except CalendarAuthException as e:
            logger.error("Authentication failure for calendar connection %s: %s", conn.id, e)
            job.status = "FAILED"
            job.last_error = f"Auth failed: {str(e)}"
            conn.is_active = False
            conn.last_error = str(e)
            self.db.commit()

            self._log_sync_action(
                connection_id=conn.id,
                interview_id=interview.id,
                direction=CalendarSyncDirection.OUTBOUND,
                operation=job.operation,
                status="FAILED",
                error_message=str(e),
            )
            return False

        except Exception as e:
            logger.error("Unexpected error in calendar sync job %s: %s", job.id, e, exc_info=True)
            job.status = "FAILED"
            job.last_error = str(e)
            self.db.commit()
            return False

    def _execute_create_event(
        self,
        conn: CalendarConnection,
        interview: Interview,
        provider: BaseCalendarProvider,
        access_token: str,
        generate_meeting: bool,
    ):
        """Execute creation of external event and store CalendarEventMapping."""
        # Check existing mapping to guarantee idempotency
        stmt = select(CalendarEventMapping).where(
            CalendarEventMapping.agency_id == self.agency_id,
            CalendarEventMapping.interview_id == interview.id,
            CalendarEventMapping.connection_id == conn.id,
        )
        existing = self.db.scalars(stmt).first()
        if existing:
            # Already mapped! Delegate to update to preserve idempotency
            return self._execute_update_event(conn, interview, provider, access_token)

        # Build attendees list safely without leaking internal recruiter feedback
        attendees = []
        for p in interview.participants:
            attendees.append({"email": p.participant_email, "name": p.participant_name})

        # Sanitize event description
        cand_name = interview.application.candidate.full_name if interview.application and interview.application.candidate else "Candidate"
        job_title = interview.application.job.title if interview.application and interview.application.job else "Role"
        desc = (
            f"HireLens Interview: {interview.round_name}\n"
            f"Candidate: {cand_name}\n"
            f"Role: {job_title}\n"
            f"Timezone: {interview.timezone}\n"
        )
        if interview.description:
            desc += f"\nNotes:\n{interview.description}\n"

        result = provider.create_event(
            access_token=access_token,
            calendar_id=conn.selected_calendar_id,
            title=f"Interview: {cand_name} - {interview.round_name}",
            description=desc,
            start_time=interview.scheduled_start,
            end_time=interview.scheduled_end,
            timezone_str=interview.timezone,
            attendees=attendees,
            location=interview.location,
            generate_meeting=generate_meeting,
        )

        meeting_prov = MeetingProviderType.NONE
        if result.meeting_link:
            if "meet.google" in result.meeting_link:
                meeting_prov = MeetingProviderType.GOOGLE_MEET
            elif "teams" in result.meeting_link:
                meeting_prov = MeetingProviderType.MS_TEAMS

            if not interview.meeting_url:
                interview.meeting_url = result.meeting_link

        now = datetime.now(timezone.utc)
        mapping = CalendarEventMapping(
            agency_id=self.agency_id,
            connection_id=conn.id,
            interview_id=interview.id,
            external_event_id=result.event_id,
            external_calendar_id=conn.selected_calendar_id,
            provider=conn.provider,
            meeting_link=result.meeting_link,
            meeting_provider=meeting_prov,
            sync_status=CalendarSyncStatus.SYNCED,
            last_synced_at=now,
            created_at=now,
            updated_at=now,
        )
        self.db.add(mapping)
        self.db.commit()

    def _execute_update_event(
        self,
        conn: CalendarConnection,
        interview: Interview,
        provider: BaseCalendarProvider,
        access_token: str,
    ):
        """Execute update of an existing external calendar event."""
        stmt = select(CalendarEventMapping).where(
            CalendarEventMapping.agency_id == self.agency_id,
            CalendarEventMapping.interview_id == interview.id,
            CalendarEventMapping.connection_id == conn.id,
        )
        mapping = self.db.scalars(stmt).first()
        if not mapping:
            # If mapping doesn't exist yet, create it
            return self._execute_create_event(conn, interview, provider, access_token, generate_meeting=False)

        cand_name = interview.application.candidate.full_name if interview.application and interview.application.candidate else "Candidate"
        job_title = interview.application.job.title if interview.application and interview.application.job else "Role"
        desc = (
            f"HireLens Interview: {interview.round_name}\n"
            f"Candidate: {cand_name}\n"
            f"Role: {job_title}\n"
            f"Timezone: {interview.timezone}\n"
        )
        if interview.description:
            desc += f"\nNotes:\n{interview.description}\n"

        attendees = [{"email": p.participant_email, "name": p.participant_name} for p in interview.participants]

        result = provider.update_event(
            access_token=access_token,
            calendar_id=mapping.external_calendar_id,
            event_id=mapping.external_event_id,
            title=f"Interview: {cand_name} - {interview.round_name}",
            description=desc,
            start_time=interview.scheduled_start,
            end_time=interview.scheduled_end,
            timezone_str=interview.timezone,
            attendees=attendees,
            location=interview.location,
            meeting_link=mapping.meeting_link,
        )

        now = datetime.now(timezone.utc)
        mapping.sync_status = CalendarSyncStatus.SYNCED
        mapping.last_synced_at = now
        mapping.last_error = None
        mapping.updated_at = now
        self.db.commit()

    def _execute_cancel_event(
        self,
        conn: CalendarConnection,
        interview: Interview,
        provider: BaseCalendarProvider,
        access_token: str,
    ):
        """Execute cancellation/deletion of an external calendar event."""
        stmt = select(CalendarEventMapping).where(
            CalendarEventMapping.agency_id == self.agency_id,
            CalendarEventMapping.interview_id == interview.id,
            CalendarEventMapping.connection_id == conn.id,
        )
        mapping = self.db.scalars(stmt).first()
        if not mapping:
            return

        provider.cancel_event(
            access_token=access_token,
            calendar_id=mapping.external_calendar_id,
            event_id=mapping.external_event_id,
        )

        now = datetime.now(timezone.utc)
        mapping.sync_status = CalendarSyncStatus.CANCELLED
        mapping.last_synced_at = now
        mapping.updated_at = now
        self.db.commit()

    # -------------------------------------------------------------------------
    # Two-Way Synchronization & Conflict-Safe Rescheduling
    # -------------------------------------------------------------------------

    def process_inbound_time_change(
        self,
        connection_id: uuid.UUID,
        external_event_id: str,
        new_start_utc: datetime,
        new_end_utc: datetime,
        new_timezone: Optional[str] = None,
        acting_user: Optional[User] = None,
    ) -> Dict[str, Any]:
        """
        Safely processes an external time change received via webhook or inbound polling.
        HIRELENS IS AUTHORITATIVE: Changes must flow through InterviewService.reschedule_interview,
        acquiring PostgreSQL advisory locks and executing deterministic conflict checks.
        If a conflict exists, the external change is rejected and recorded in CalendarSyncLog.
        """
        conn = self.get_connection(connection_id)
        if not conn:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Calendar connection not found.")

        # Find mapping
        mapping_stmt = select(CalendarEventMapping).where(
            CalendarEventMapping.agency_id == self.agency_id,
            CalendarEventMapping.connection_id == conn.id,
            CalendarEventMapping.external_event_id == external_event_id,
        )
        mapping = self.db.scalars(mapping_stmt).first()
        if not mapping:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mapped interview not found for external event.")

        interview_stmt = select(Interview).where(
            Interview.id == mapping.interview_id,
            Interview.agency_id == self.agency_id,
        )
        interview = self.db.scalars(interview_stmt).first()
        if not interview:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Interview not found.")

        if interview.status in (InterviewStatus.CANCELLED, InterviewStatus.COMPLETED):
            return {
                "status": "IGNORED",
                "reason": f"Interview is already {interview.status.value}.",
            }

        actor = acting_user or conn.user
        target_tz = new_timezone or interview.timezone or DEFAULT_TIMEZONE

        from app.schemas.interview import InterviewReschedule
        from app.services.interview_service import InterviewService

        reschedule_data = InterviewReschedule(
            scheduled_start=new_start_utc,
            scheduled_end=new_end_utc,
            timezone=target_tz,
            reason="External calendar time change (Two-Way Sync)",
        )

        try:
            service = InterviewService(self.db, self.agency_id)
            updated_read = service.reschedule_interview(
                interview_id=interview.id,
                current_user=actor,
                data=reschedule_data,
            )

            # Record success log
            self._log_sync_action(
                connection_id=conn.id,
                interview_id=interview.id,
                direction=CalendarSyncDirection.INBOUND,
                operation=CalendarSyncOperation.UPDATE,
                status="SUCCESS",
                details=f"Inbound sync updated interview {interview.id} to {new_start_utc.isoformat()}",
            )
            return {"status": "SUCCESS", "interview": updated_read}

        except HTTPException as he:
            # Caught conflict (409) or bad request (400)
            logger.warning("Inbound external calendar change rejected for interview %s: %s", interview.id, he.detail)
            self._log_sync_action(
                connection_id=conn.id,
                interview_id=interview.id,
                direction=CalendarSyncDirection.INBOUND,
                operation=CalendarSyncOperation.UPDATE,
                status="CONFLICT" if he.status_code == 409 else "FAILED",
                error_message=str(he.detail),
            )
            return {
                "status": "CONFLICT" if he.status_code == 409 else "REJECTED",
                "detail": he.detail,
            }

    # -------------------------------------------------------------------------
    # Lifecycle Hooks (Triggered from InterviewService)
    # -------------------------------------------------------------------------

    def on_interview_scheduled(self, interview: Interview, current_user: User, generate_meeting: bool = False):
        """Enqueue sync jobs for all active connections belonging to interview participants/creator."""
        connections = self._find_connections_for_interview(interview, current_user)
        for conn in connections:
            self.enqueue_sync_job(conn.id, interview.id, CalendarSyncOperation.CREATE, generate_meeting=generate_meeting)

    def on_interview_confirmed(self, interview: Interview, current_user: User):
        """Enqueue update/sync job upon confirmation."""
        connections = self._find_connections_for_interview(interview, current_user)
        for conn in connections:
            self.enqueue_sync_job(conn.id, interview.id, CalendarSyncOperation.UPDATE)

    def on_interview_rescheduled(self, interview: Interview, current_user: User):
        """Enqueue update sync jobs for existing mappings."""
        connections = self._find_connections_for_interview(interview, current_user)
        for conn in connections:
            self.enqueue_sync_job(conn.id, interview.id, CalendarSyncOperation.UPDATE)

    def on_interview_cancelled(self, interview: Interview, current_user: User):
        """Enqueue cancellation sync jobs."""
        connections = self._find_connections_for_interview(interview, current_user)
        for conn in connections:
            self.enqueue_sync_job(conn.id, interview.id, CalendarSyncOperation.CANCEL)

    def _find_connections_for_interview(self, interview: Interview, current_user: User) -> List[CalendarConnection]:
        """Find active calendar connections for the interview creator and participants."""
        user_ids = set()
        if current_user and current_user.id:
            user_ids.add(current_user.id)
        if interview.created_by:
            user_ids.add(interview.created_by)
        for p in interview.participants:
            if p.user_id:
                user_ids.add(p.user_id)

        if not user_ids:
            return []

        stmt = select(CalendarConnection).where(
            CalendarConnection.agency_id == self.agency_id,
            CalendarConnection.user_id.in_(list(user_ids)),
            CalendarConnection.is_active == True,
        )
        return list(self.db.scalars(stmt).all())

    # -------------------------------------------------------------------------
    # Logging and Diagnostics
    # -------------------------------------------------------------------------

    def _log_sync_action(
        self,
        connection_id: Optional[uuid.UUID],
        interview_id: Optional[uuid.UUID],
        direction: CalendarSyncDirection,
        operation: CalendarSyncOperation,
        status: str,
        details: Optional[str] = None,
        error_message: Optional[str] = None,
    ):
        """Durable log entry without storing plaintext tokens or confidential data."""
        log = CalendarSyncLog(
            agency_id=self.agency_id,
            connection_id=connection_id,
            interview_id=interview_id,
            direction=direction,
            operation=operation,
            status=status,
            details=details,
            error_message=error_message,
            created_at=datetime.now(timezone.utc),
        )
        self.db.add(log)
        self.db.commit()

    def list_sync_logs(self, limit: int = 50) -> List[CalendarSyncLog]:
        """Retrieve recent calendar sync logs for the agency."""
        stmt = (
            select(CalendarSyncLog)
            .where(CalendarSyncLog.agency_id == self.agency_id)
            .order_by(CalendarSyncLog.created_at.desc())
            .limit(limit)
        )
        return list(self.db.scalars(stmt).all())
