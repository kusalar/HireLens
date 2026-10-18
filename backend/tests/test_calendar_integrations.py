import uuid
import json
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.security import encrypt_token, decrypt_token
from app.core.timezone import parse_and_normalize_to_utc, convert_utc_to_timezone, DEFAULT_TIMEZONE
from app.models.enums import (
    UserRole,
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
)
from app.models.interview import Interview
from app.services.calendar.base import (
    BaseCalendarProvider,
    CalendarAuthException,
    CalendarRateLimitException,
    CalendarProviderException,
)
from app.services.calendar.mock import MockCalendarProvider
from app.services.calendar.factory import get_calendar_provider, get_mock_provider_instance
from app.services.calendar_sync_service import CalendarSyncService


# Helper fixtures & creators
def create_agency_and_user(
    client: TestClient, agency_name: str, email: str, role: str = "OWNER"
) -> tuple[str, str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "agency_name": agency_name,
            "full_name": f"{agency_name} Admin",
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["tokens"]["access_token"]
    user_id = reg.json()["user"]["id"]
    agency_id = reg.json()["user"]["agency_id"]
    return token, user_id, agency_id


def create_job(client: TestClient, token: str, title: str = "Senior Backend Engineer") -> dict:
    res = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "department": "Engineering",
            "description": "Design backend services.",
            "location": "Bengaluru, India",
            "work_mode": "HYBRID",
            "employment_type": "FULL_TIME",
            "minimum_experience": 4,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_candidate(client: TestClient, token: str, name: str = "Aarav Patel", email: str = "aarav@example.com") -> dict:
    res = client.post(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": name,
            "email": email,
            "phone": "+919876543210",
            "current_location": "Mumbai, India",
            "years_of_experience": 5,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_application(client: TestClient, token: str, job_id: str, candidate_id: str) -> dict:
    res = client.post(
        f"/api/v1/jobs/{job_id}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "candidate_id": candidate_id,
            "status": "APPLIED",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()



def schedule_interview_helper(
    client: TestClient, token: str, app_id: str, interviewer_user_id: str, start_dt: datetime, end_dt: datetime
) -> dict:
    res = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Technical Round 1",
            "round_type": "TECHNICAL",
            "title": "Core Systems Discussion",
            "interview_mode": "ONLINE",
            "scheduled_start": start_dt.isoformat(),
            "scheduled_end": end_dt.isoformat(),
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "participant_name": "Lead Interviewer",
                    "participant_email": "interviewer@example.com",
                    "participant_role": "INTERVIEWER",
                    "user_id": interviewer_user_id,
                }
            ],
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


# -----------------------------------------------------------------------------
# 1. Provider Abstraction Tests
# -----------------------------------------------------------------------------

def test_provider_abstraction_and_mock_adapter():
    """Verify provider interface contract, event creation, update, and meeting links."""
    provider = MockCalendarProvider("google")
    assert isinstance(provider, BaseCalendarProvider)

    # Authorization URL
    auth_url = provider.get_authorization_url(state="test_state", redirect_uri="http://localhost:3000/callback")
    assert "test_state" in auth_url
    assert "redirect_uri=" in auth_url

    # Token exchange
    tokens = provider.exchange_code_for_tokens("valid_code", "http://localhost:3000/callback")
    assert "access_token" in tokens
    assert "refresh_token" in tokens
    assert tokens["account_email"] == "recruiter@example.com"

    # Token refresh
    refreshed = provider.refresh_tokens(tokens["refresh_token"])
    assert "access_token" in refreshed

    # List calendars
    cals = provider.list_calendars(tokens["access_token"])
    assert len(cals) >= 1
    assert any(c["id"] == "primary" for c in cals)

    # Create event with Google Meet link
    start = datetime.now(timezone.utc) + timedelta(days=1)
    end = start + timedelta(hours=1)
    result = provider.create_event(
        access_token=tokens["access_token"],
        calendar_id="primary",
        title="Technical Interview",
        description="Core architecture discussion",
        start_time=start,
        end_time=end,
        timezone_str="Asia/Kolkata",
        attendees=[{"email": "candidate@example.com", "name": "Candidate"}],
        location="Online",
        generate_meeting=True,
    )
    assert result.event_id.startswith("mock_evt_")
    assert "meet.google.com" in result.meeting_link
    assert result.status == "confirmed"

    # Fetch event
    fetched = provider.get_event(tokens["access_token"], "primary", result.event_id)
    assert fetched is not None
    assert fetched.title == "Technical Interview"

    # Update event
    updated = provider.update_event(
        access_token=tokens["access_token"],
        calendar_id="primary",
        event_id=result.event_id,
        title="Updated Interview Title",
        description="Updated notes",
        start_time=start,
        end_time=end,
        timezone_str="Asia/Kolkata",
        attendees=[{"email": "candidate@example.com", "name": "Candidate"}],
    )
    assert updated.title == "Updated Interview Title"

    # Cancel event
    cancelled = provider.cancel_event(tokens["access_token"], "primary", result.event_id)
    assert cancelled is True
    cancelled_event = provider.get_event(tokens["access_token"], "primary", result.event_id)
    assert cancelled_event.status == "cancelled"


# -----------------------------------------------------------------------------
# 2. Security, OAuth & Token Encryption Tests
# -----------------------------------------------------------------------------

def test_oauth_state_tampering_and_csrf_protection(client: TestClient, db_session: Session):
    """Verify that OAuth state is cryptographically signed and tampered state is rejected."""
    token, user_id, agency_id = create_agency_and_user(client, "SecurityAgency", "sec@agency.com")

    # Initiate OAuth
    init_res = client.post(
        "/api/v1/integrations/calendars/init",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider": "GOOGLE"},
    )
    assert init_res.status_code == 200
    state = init_res.json()["state"]
    assert state is not None

    # Test tampering with state
    tampered_state = state[:-4] + "AAAA"
    cb_tampered = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "sample_auth_code", "state": tampered_state},
    )
    assert cb_tampered.status_code == 400
    assert "Invalid or tampered" in cb_tampered.json()["detail"]

    # Test cross-agency state spoofing
    token2, user2_id, agency2_id = create_agency_and_user(client, "CrossAgency", "cross@agency.com")
    cb_cross = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {token2}"},  # User from different agency uses state from agency 1
        json={"code": "sample_auth_code", "state": state},
    )
    assert cb_cross.status_code == 403
    assert "Cross-agency" in cb_cross.json()["detail"]


def test_token_encryption_at_rest_and_no_plaintext_leak(client: TestClient, db_session: Session):
    """Verify that OAuth access & refresh tokens are stored encrypted and never returned in plaintext."""
    token, user_id, agency_id = create_agency_and_user(client, "EncryptAgency", "enc@agency.com")

    init_res = client.post(
        "/api/v1/integrations/calendars/init",
        headers={"Authorization": f"Bearer {token}"},
        json={"provider": "GOOGLE"},
    )
    state = init_res.json()["state"]

    cb_res = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {token}"},
        json={"code": "valid_code", "state": state},
    )
    assert cb_res.status_code == 200
    conn_data = cb_res.json()
    conn_id = uuid.UUID(conn_data["id"])

    # Ensure API response does NOT contain tokens!
    assert "encrypted_access_token" not in conn_data
    assert "access_token" not in conn_data
    assert "refresh_token" not in conn_data

    # Inspect direct database record
    db_conn = db_session.scalar(select(CalendarConnection).where(CalendarConnection.id == conn_id))
    assert db_conn is not None
    assert db_conn.encrypted_access_token is not None
    assert not db_conn.encrypted_access_token.startswith("mock_access_token")  # Must be ciphertext

    # Decrypt and verify
    decrypted = decrypt_token(db_conn.encrypted_access_token)
    assert decrypted.startswith("mock_access_token_")


# -----------------------------------------------------------------------------
# 3. Connection Management & Multi-Tenancy Tests
# -----------------------------------------------------------------------------

def test_connection_management_and_tenant_isolation(client: TestClient, db_session: Session):
    """Verify connection listing, calendar selection, and strict agency isolation."""
    token1, user1_id, agency1_id = create_agency_and_user(client, "Tenant1", "t1@agency.com")
    token2, user2_id, agency2_id = create_agency_and_user(client, "Tenant2", "t2@agency.com")

    # Connect Google for Tenant 1
    init1 = client.post(
        "/api/v1/integrations/calendars/init",
        headers={"Authorization": f"Bearer {token1}"},
        json={"provider": "GOOGLE"},
    )
    cb1 = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {token1}"},
        json={"code": "code1", "state": init1.json()["state"]},
    )
    conn1_id = cb1.json()["id"]

    # Connect Microsoft for Tenant 2
    init2 = client.post(
        "/api/v1/integrations/calendars/init",
        headers={"Authorization": f"Bearer {token2}"},
        json={"provider": "MICROSOFT"},
    )
    cb2 = client.post(
        "/api/v1/integrations/calendars/callback",
        headers={"Authorization": f"Bearer {token2}"},
        json={"code": "code2", "state": init2.json()["state"]},
    )
    conn2_id = cb2.json()["id"]

    # Tenant 1 lists connections: sees ONLY their own
    list1 = client.get("/api/v1/integrations/calendars", headers={"Authorization": f"Bearer {token1}"})
    assert list1.status_code == 200
    ids1 = [c["id"] for c in list1.json()]
    assert conn1_id in ids1
    assert conn2_id not in ids1

    # Tenant 1 tries to disconnect Tenant 2's connection -> 404
    cross_del = client.delete(
        f"/api/v1/integrations/calendars/{conn2_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert cross_del.status_code == 404

    # Tenant 1 lists calendars for their connection
    cals_res = client.get(
        f"/api/v1/integrations/calendars/{conn1_id}/calendars",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert cals_res.status_code == 200
    assert len(cals_res.json()) >= 1

    # Tenant 1 updates selected calendar
    sel_res = client.patch(
        f"/api/v1/integrations/calendars/{conn1_id}/selection",
        headers={"Authorization": f"Bearer {token1}"},
        json={"calendar_id": "interviews_cal", "calendar_name": "HireLens Interviews"},
    )
    assert sel_res.status_code == 200
    assert sel_res.json()["selected_calendar_id"] == "interviews_cal"

    # Disconnect Tenant 1's connection
    del_res = client.delete(
        f"/api/v1/integrations/calendars/{conn1_id}",
        headers={"Authorization": f"Bearer {token1}"},
    )
    assert del_res.status_code == 204

    # Verify inactive
    db_conn = db_session.scalar(select(CalendarConnection).where(CalendarConnection.id == uuid.UUID(conn1_id)))
    assert db_conn.is_active is False
    assert db_conn.encrypted_access_token is None


# -----------------------------------------------------------------------------
# 4. Outbox Synchronization & Lifecycle Tests
# -----------------------------------------------------------------------------

def test_interview_lifecycle_calendar_sync(client: TestClient, db_session: Session):
    """
    Test end-to-end interview lifecycle synchronization:
    Scheduling creates external event -> Rescheduling updates it -> Cancellation cancels it.
    """
    token, user_id, agency_id = create_agency_and_user(client, "SyncAgency", "sync@agency.com")

    # Link user's calendar connection
    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})

    # Create job & candidate & application
    job = create_job(client, token)
    cand = create_candidate(client, token)
    app = create_application(client, token, job["id"], cand["id"])

    # 1. Schedule Interview
    start_dt = datetime.now(timezone.utc) + timedelta(days=2)
    end_dt = start_dt + timedelta(hours=1)
    interview = schedule_interview_helper(client, token, app["id"], user_id, start_dt, end_dt)
    interview_id = uuid.UUID(interview["id"])

    # Process outbox job synchronously for test assertion
    sync_service = CalendarSyncService(db_session, uuid.UUID(agency_id))
    pending_jobs = db_session.scalars(
        select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id, CalendarSyncJob.status == "PENDING")
    ).all()
    assert len(pending_jobs) >= 1
    for job_item in pending_jobs:
        success = sync_service.process_sync_job(job_item.id)
        assert success is True

    # Verify CalendarEventMapping created
    mapping = db_session.scalar(
        select(CalendarEventMapping).where(CalendarEventMapping.interview_id == interview_id)
    )
    assert mapping is not None
    assert mapping.sync_status == CalendarSyncStatus.SYNCED
    external_event_id = mapping.external_event_id

    # 2. Reschedule Interview
    new_start = start_dt + timedelta(hours=2)
    new_end = end_dt + timedelta(hours=2)
    resched_res = client.post(
        f"/api/v1/interviews/{interview_id}/reschedule",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "scheduled_start": new_start.isoformat(),
            "scheduled_end": new_end.isoformat(),
            "timezone": "Asia/Kolkata",
            "reason": "Interviewer requested 2-hour delay",
        },
    )
    assert resched_res.status_code == 200

    # Process reschedule outbox sync job
    resched_jobs = db_session.scalars(
        select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id, CalendarSyncJob.status == "PENDING")
    ).all()
    assert len(resched_jobs) >= 1
    for job_item in resched_jobs:
        sync_service.process_sync_job(job_item.id)

    db_session.refresh(mapping)
    assert mapping.external_event_id == external_event_id  # Preserves event mapping without duplicate!
    assert mapping.sync_status == CalendarSyncStatus.SYNCED

    # 3. Cancel Interview
    cancel_res = client.post(
        f"/api/v1/interviews/{interview_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Candidate withdrew application"},
    )
    assert cancel_res.status_code == 200

    # Process cancel sync job
    cancel_jobs = db_session.scalars(
        select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id, CalendarSyncJob.status == "PENDING")
    ).all()
    for job_item in cancel_jobs:
        sync_service.process_sync_job(job_item.id)

    db_session.refresh(mapping)
    assert mapping.sync_status == CalendarSyncStatus.CANCELLED


def test_idempotent_event_creation(client: TestClient, db_session: Session):
    """Verify that multiple sync job executions for the same interview are idempotent and do not duplicate events."""
    token, user_id, agency_id = create_agency_and_user(client, "IdempAgency", "idemp@agency.com")

    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})

    job = create_job(client, token)
    cand = create_candidate(client, token)
    app = create_application(client, token, job["id"], cand["id"])

    start_dt = datetime.now(timezone.utc) + timedelta(days=3)
    interview = schedule_interview_helper(client, token, app["id"], user_id, start_dt, start_dt + timedelta(hours=1))
    interview_id = uuid.UUID(interview["id"])

    sync_service = CalendarSyncService(db_session, uuid.UUID(agency_id))
    jobs = db_session.scalars(
        select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id)
    ).all()
    job_id = jobs[0].id

    # Execute first time
    assert sync_service.process_sync_job(job_id) is True

    # Re-execute job directly
    assert sync_service.process_sync_job(job_id) is True

    # Verify only ONE mapping exists
    mappings = db_session.scalars(
        select(CalendarEventMapping).where(CalendarEventMapping.interview_id == interview_id)
    ).all()
    assert len(mappings) == 1


# -----------------------------------------------------------------------------
# 5. Two-Way Synchronization & Conflict Handling
# -----------------------------------------------------------------------------

def test_two_way_sync_inbound_time_change_and_conflict_rejection(client: TestClient, db_session: Session):
    """
    Test two-way synchronization:
    1. External event time change arrives and successfully updates interview schedule.
    2. External event time change that conflicts with an existing interview is REJECTED without overwriting schedule.
    """
    token, user_id, agency_id = create_agency_and_user(client, "ConflictAgency", "conf@agency.com")

    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    conn_res = client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})
    conn_id = uuid.UUID(conn_res.json()["id"])

    job = create_job(client, token)
    cand1 = create_candidate(client, token, name="Candidate One", email="c1@example.com")
    cand2 = create_candidate(client, token, name="Candidate Two", email="c2@example.com")
    app1 = create_application(client, token, job["id"], cand1["id"])
    app2 = create_application(client, token, job["id"], cand2["id"])

    # Interview 1: Oct 25 10:00 - 11:00 UTC
    dt1_start = datetime(2026, 10, 25, 10, 0, tzinfo=timezone.utc)
    dt1_end = datetime(2026, 10, 25, 11, 0, tzinfo=timezone.utc)
    int1 = schedule_interview_helper(client, token, app1["id"], user_id, dt1_start, dt1_end)
    int1_id = uuid.UUID(int1["id"])

    # Interview 2: Oct 25 14:00 - 15:00 UTC
    dt2_start = datetime(2026, 10, 25, 14, 0, tzinfo=timezone.utc)
    dt2_end = datetime(2026, 10, 25, 15, 0, tzinfo=timezone.utc)
    int2 = schedule_interview_helper(client, token, app2["id"], user_id, dt2_start, dt2_end)
    int2_id = uuid.UUID(int2["id"])

    sync_service = CalendarSyncService(db_session, uuid.UUID(agency_id))
    # Sync interview 1
    jobs1 = db_session.scalars(select(CalendarSyncJob).where(CalendarSyncJob.interview_id == int1_id)).all()
    for j in jobs1:
        sync_service.process_sync_job(j.id)

    mapping1 = db_session.scalar(select(CalendarEventMapping).where(CalendarEventMapping.interview_id == int1_id))
    assert mapping1 is not None

    # 1. Inbound time change: Interview 1 is moved from 10:00 to 11:30 (No conflict)
    new_dt1_start = datetime(2026, 10, 25, 11, 30, tzinfo=timezone.utc)
    new_dt1_end = datetime(2026, 10, 25, 12, 30, tzinfo=timezone.utc)

    inbound_res = sync_service.process_inbound_time_change(
        connection_id=conn_id,
        external_event_id=mapping1.external_event_id,
        new_start_utc=new_dt1_start,
        new_end_utc=new_dt1_end,
    )
    assert inbound_res["status"] == "SUCCESS"

    db_interview1 = db_session.scalar(select(Interview).where(Interview.id == int1_id))
    assert db_interview1.status == InterviewStatus.RESCHEDULED

    # 2. Inbound conflict: Interview 1 is externally moved to 14:15 - 15:15 (CONFLICTS WITH Interview 2!)
    conflict_start = datetime(2026, 10, 25, 14, 15, tzinfo=timezone.utc)
    conflict_end = datetime(2026, 10, 25, 15, 15, tzinfo=timezone.utc)

    conflict_res = sync_service.process_inbound_time_change(
        connection_id=conn_id,
        external_event_id=mapping1.external_event_id,
        new_start_utc=conflict_start,
        new_end_utc=conflict_end,
    )
    assert conflict_res["status"] == "CONFLICT"
    assert "Scheduling conflict" in conflict_res["detail"]

    # CRITICAL: Verify HireLens interview was NOT corrupted or overwritten!
    db_session.refresh(db_interview1)
    # Start time should still be the valid previous schedule (11:30), not the conflicting 14:15!
    assert db_interview1.scheduled_start.hour == 11

    # Check that a conflict log was recorded
    logs = sync_service.list_sync_logs()
    assert any(log.status == "CONFLICT" for log in logs)


# -----------------------------------------------------------------------------
# 6. Fault Tolerance, Retries & Rate Limiting Tests
# -----------------------------------------------------------------------------

def test_rate_limit_and_exponential_backoff(client: TestClient, db_session: Session):
    """Verify rate-limit 429 response schedules backoff retry and does not crash worker."""
    token, user_id, agency_id = create_agency_and_user(client, "RateLimitAgency", "rate@agency.com")

    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})

    job = create_job(client, token)
    cand = create_candidate(client, token)
    app = create_application(client, token, job["id"], cand["id"])

    interview = schedule_interview_helper(
        client, token, app["id"], user_id,
        datetime.now(timezone.utc) + timedelta(days=4),
        datetime.now(timezone.utc) + timedelta(days=4, hours=1),
    )
    interview_id = uuid.UUID(interview["id"])

    sync_service = CalendarSyncService(db_session, uuid.UUID(agency_id))
    sync_job = db_session.scalar(select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id))

    # Inject rate limit fault into mock provider
    mock_provider = get_mock_provider_instance("google")
    mock_provider.should_rate_limit = True

    try:
        success = sync_service.process_sync_job(sync_job.id)
        assert success is False
        db_session.refresh(sync_job)
        assert sync_job.status == "PENDING"
        assert sync_job.attempt_count == 1
        sched = sync_job.scheduled_at
        if sched.tzinfo is None:
            sched = sched.replace(tzinfo=timezone.utc)
        assert sched > datetime.now(timezone.utc)

    finally:
        mock_provider.should_rate_limit = False


def test_dead_letter_queue_on_permanent_failure(client: TestClient, db_session: Session):
    """Verify sync job transitions to DEAD_LETTER after max retry attempts."""
    token, user_id, agency_id = create_agency_and_user(client, "DeadLetterAgency", "dl@agency.com")

    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})

    job = create_job(client, token)
    cand = create_candidate(client, token)
    app = create_application(client, token, job["id"], cand["id"])

    interview = schedule_interview_helper(
        client, token, app["id"], user_id,
        datetime.now(timezone.utc) + timedelta(days=5),
        datetime.now(timezone.utc) + timedelta(days=5, hours=1),
    )
    interview_id = uuid.UUID(interview["id"])

    sync_service = CalendarSyncService(db_session, uuid.UUID(agency_id))
    sync_job = db_session.scalar(select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id))
    sync_job.attempt_count = 4  # max is 5

    mock_provider = get_mock_provider_instance("google")
    mock_provider.should_fail_transient = True

    try:
        success = sync_service.process_sync_job(sync_job.id)
        assert success is False
        db_session.refresh(sync_job)
        assert sync_job.status == "DEAD_LETTER"
        assert sync_job.attempt_count == 5
    finally:
        mock_provider.should_fail_transient = False


# -----------------------------------------------------------------------------
# 7. Meeting Links & Privacy Protection
# -----------------------------------------------------------------------------

def test_meeting_link_generation_and_candidate_privacy(client: TestClient, db_session: Session):
    """Verify conference link generation and that internal feedback/notes are never leaked."""
    token, user_id, agency_id = create_agency_and_user(client, "PrivacyAgency", "priv@agency.com")

    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})

    job = create_job(client, token)
    cand = create_candidate(client, token, name="Divya Roy", email="divya@example.com")
    app = create_application(client, token, job["id"], cand["id"])

    interview = schedule_interview_helper(
        client, token, app["id"], user_id,
        datetime.now(timezone.utc) + timedelta(days=6),
        datetime.now(timezone.utc) + timedelta(days=6, hours=1),
    )
    interview_id = uuid.UUID(interview["id"])

    # Generate meeting link via endpoint
    meet_res = client.post(
        f"/api/v1/integrations/interviews/{interview_id}/meeting-link",
        headers={"Authorization": f"Bearer {token}"},
        json={"meeting_provider": "GOOGLE_MEET"},
    )
    assert meet_res.status_code == 200
    assert "meet.google.com" in meet_res.json()["meeting_url"]

    # Verify event description in provider does not leak confidential fields
    mock_provider = get_mock_provider_instance("google")
    mapping = db_session.scalar(select(CalendarEventMapping).where(CalendarEventMapping.interview_id == interview_id))
    assert mapping is not None

    stored_event = mock_provider.events.get(mapping.external_event_id)
    assert stored_event is not None
    desc = stored_event["description"]

    assert "Candidate: Divya Roy" in desc
    # Ensure no internal private notes or candidate salary/score leaked into calendar invite
    assert "feedback" not in desc.lower()
    assert "score" not in desc.lower()


# -----------------------------------------------------------------------------
# 8. Webhook Handshake & RBAC Tests
# -----------------------------------------------------------------------------

def test_webhooks_and_rbac(client: TestClient, db_session: Session):
    """Test webhook handshakes for Google and Microsoft Graph, and VIEWER RBAC enforcement."""
    # 1. Microsoft validation token handshake
    ms_handshake = client.post("/api/v1/integrations/webhooks/microsoft?validationToken=test_validation_token_12345")
    assert ms_handshake.status_code == 200
    assert ms_handshake.text == "test_validation_token_12345"

    # 2. Google sync handshake
    google_handshake = client.post(
        "/api/v1/integrations/webhooks/google",
        headers={
            "x-goog-channel-id": "channel_uuid_123",
            "x-goog-resource-state": "sync",
        },
    )
    assert google_handshake.status_code == 200

    # 3. VIEWER RBAC restriction
    owner_token, owner_id, agency_id = create_agency_and_user(client, "RbacAgency", "owner@rbac.com")
    viewer_token, viewer_id, _ = create_agency_and_user(client, "ViewerAgency", "viewer@rbac.com")

    # Change user to VIEWER role inside RbacAgency
    from app.models.entities import User
    db_viewer = db_session.scalar(select(User).where(User.id == uuid.UUID(viewer_id)))
    db_viewer.role = UserRole.VIEWER
    db_viewer.agency_id = uuid.UUID(agency_id)
    db_session.commit()

    # VIEWER can view connections & logs

    v_list = client.get("/api/v1/integrations/calendars", headers={"Authorization": f"Bearer {viewer_token}"})
    assert v_list.status_code == 200

    v_logs = client.get("/api/v1/integrations/calendars/sync-logs", headers={"Authorization": f"Bearer {viewer_token}"})
    assert v_logs.status_code == 200

    # VIEWER CANNOT initiate connection
    v_init = client.post(
        "/api/v1/integrations/calendars/init",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"provider": "GOOGLE"},
    )
    assert v_init.status_code == 403

    # VIEWER CANNOT disconnect
    v_del = client.post(
        f"/api/v1/integrations/calendars/{uuid.uuid4()}/sync",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert v_del.status_code == 403


def test_batch_sweep_recovery(client: TestClient, db_session: Session):
    """Verify background batch task sweeps and processes pending sync jobs after worker restart."""
    token, user_id, agency_id = create_agency_and_user(client, "BatchAgency", "batch@agency.com")

    init = client.post("/api/v1/integrations/calendars/init", headers={"Authorization": f"Bearer {token}"}, json={"provider": "GOOGLE"})
    client.post("/api/v1/integrations/calendars/callback", headers={"Authorization": f"Bearer {token}"}, json={"code": "c", "state": init.json()["state"]})

    job = create_job(client, token)
    cand = create_candidate(client, token)
    app = create_application(client, token, job["id"], cand["id"])

    interview = schedule_interview_helper(
        client, token, app["id"], user_id,
        datetime.now(timezone.utc) + timedelta(days=7),
        datetime.now(timezone.utc) + timedelta(days=7, hours=1),
    )
    interview_id = uuid.UUID(interview["id"])

    # Simulate worker restart: job is left as PENDING in DB
    sync_job = db_session.scalar(select(CalendarSyncJob).where(CalendarSyncJob.interview_id == interview_id))
    assert sync_job.status == "PENDING"

    # Trigger batch sweep
    from app.tasks.calendar_tasks import process_calendar_sync_batch_task
    result = process_calendar_sync_batch_task(agency_id_str=agency_id, limit=10, db_override=db_session)
    assert result["status"] == "SUCCESS"

    assert result["processed_count"] >= 1

    db_session.refresh(sync_job)
    assert sync_job.status == "COMPLETED"


def test_timezone_conversion_and_ist_formatting():
    """Verify UTC storage and Asia/Kolkata (IST) display conversion integrity."""
    # Local IST time: 2:00 PM (14:00) IST
    ist_tz = ZoneInfo("Asia/Kolkata")
    dt_local = datetime(2026, 10, 20, 14, 0, tzinfo=ist_tz)

    # Normalize to UTC
    dt_utc = parse_and_normalize_to_utc(dt_local, "Asia/Kolkata")
    assert dt_utc.tzinfo == timezone.utc
    assert dt_utc.hour == 8
    assert dt_utc.minute == 30

    # Convert back to target timezone
    dt_back_ist = convert_utc_to_timezone(dt_utc, "Asia/Kolkata")
    assert dt_back_ist.hour == 14
    assert dt_back_ist.minute == 0

