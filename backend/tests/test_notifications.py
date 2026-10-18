import uuid
from datetime import datetime, timedelta, timezone
import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.models.enums import (
    UserRole,
    NotificationType,
    NotificationDeliveryStatus,
    PipelineStageType,
    InterviewMode,
)
from app.services.email.base import EmailMessage
from app.services.email.mock_provider import mock_email_provider
from app.services.email.factory import get_email_provider
from app.services.email.templates import (
    format_interview_ist_range,
    render_interview_invitation,
    render_interview_rescheduled,
    render_interview_confirmed,
    render_interview_cancelled,
    render_application_status_update,
)
from app.services.notification_service import NotificationService
from app.repositories.notification_repo import NotificationRepository


@pytest.fixture(autouse=True)
def setup_mock_email():
    prev_provider = settings.EMAIL_PROVIDER
    settings.EMAIL_PROVIDER = "mock"
    mock_email_provider.sent_messages.clear()
    mock_email_provider.fail_next = False
    mock_email_provider.failure_reason = None
    yield
    settings.EMAIL_PROVIDER = prev_provider
    mock_email_provider.sent_messages.clear()
    mock_email_provider.fail_next = False
    mock_email_provider.failure_reason = None


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


def create_secondary_user(
    client: TestClient, owner_token: str, agency_id: str, email: str, role: str = "RECRUITER"
) -> tuple[str, str]:
    inv_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": email, "role": role},
    )
    assert inv_res.status_code == 201, inv_res.text
    inv_token = inv_res.json()["token"]

    acc_res = client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": inv_token,
            "full_name": f"Test {role}",
            "password": "SecurePassword123!",
        },
    )
    assert acc_res.status_code == 201, acc_res.text
    user_id = acc_res.json()["id"]

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200, login_res.text
    token = login_res.json()["tokens"]["access_token"]
    return token, user_id


def create_job(client: TestClient, token: str, title: str = "Distributed Systems Engineer") -> dict:
    res = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "department": "Engineering",
            "description": "High performance engineering position.",
            "responsibilities": "Design distributed microservices.",
            "location": "Bengaluru, India",
            "work_mode": "HYBRID",
            "employment_type": "FULL_TIME",
            "minimum_experience": 5,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_candidate(
    client: TestClient, token: str, name: str = "Aarav Patel", email: str = "aarav@example.com"
) -> dict:
    res = client.post(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": name,
            "email": email,
            "current_title": "Senior Engineer",
            "total_experience_months": 60,
            "current_location": "Bengaluru, India",
            "profile_status": "ACTIVE",
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_application(client: TestClient, token: str, job_id: str, candidate_id: str) -> dict:
    res = client.post(
        f"/api/v1/jobs/{job_id}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate_id, "status": "APPLIED"},
    )
    assert res.status_code == 201, res.text
    return res.json()


# ============================================================
# 1. In-App Notification Center Tests
# ============================================================

def test_notification_creation_and_listing(client: TestClient, db_session):
    token, user_id, agency_id = create_agency_and_user(
        client, "Notif Agency", "owner@notifagency.com"
    )
    agency_uuid = uuid.UUID(agency_id)
    user_uuid = uuid.UUID(user_id)

    repo = NotificationRepository(db_session, agency_uuid)
    repo.create_notification(
        recipient_user_id=user_uuid,
        notification_type=NotificationType.SYSTEM,
        title="Welcome to HireLens",
        message="Workspace initialized successfully.",
    )
    repo.create_notification(
        recipient_user_id=user_uuid,
        notification_type=NotificationType.INTERVIEW_SCHEDULED,
        title="Technical Screen Scheduled",
        message="Interview scheduled with Aarav Patel.",
    )
    db_session.commit()

    # List all notifications
    res = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] == 2
    assert data["unread_count"] == 2
    assert len(data["items"]) == 2
    assert data["items"][0]["title"] == "Technical Screen Scheduled"
    assert "IST" in data["items"][0]["created_at_ist"]

    # Check unread count endpoint
    unread_res = client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert unread_res.status_code == 200
    assert unread_res.json()["unread_count"] == 2


def test_mark_notification_as_read_and_mark_all_read(client: TestClient, db_session):
    token, user_id, agency_id = create_agency_and_user(
        client, "Read Agency", "owner@readagency.com"
    )
    agency_uuid = uuid.UUID(agency_id)
    user_uuid = uuid.UUID(user_id)

    repo = NotificationRepository(db_session, agency_uuid)
    n1 = repo.create_notification(
        recipient_user_id=user_uuid,
        notification_type=NotificationType.SYSTEM,
        title="Notice 1",
        message="First notice",
    )
    n2 = repo.create_notification(
        recipient_user_id=user_uuid,
        notification_type=NotificationType.SYSTEM,
        title="Notice 2",
        message="Second notice",
    )
    db_session.commit()

    # Mark single as read
    patch_res = client.patch(
        f"/api/v1/notifications/{n1.id}/read",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["is_read"] is True

    # Verify unread count is now 1
    count_res = client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert count_res.json()["unread_count"] == 1

    # Filter unread only
    unread_list = client.get("/api/v1/notifications?unread_only=true", headers={"Authorization": f"Bearer {token}"})
    assert unread_list.status_code == 200
    assert len(unread_list.json()["items"]) == 1
    assert unread_list.json()["items"][0]["id"] == str(n2.id)

    # Mark all read
    all_res = client.post("/api/v1/notifications/mark-all-read", headers={"Authorization": f"Bearer {token}"})
    assert all_res.status_code == 200
    assert all_res.json()["marked_count"] == 1

    # Verify 0 unread remain
    count_res2 = client.get("/api/v1/notifications/unread-count", headers={"Authorization": f"Bearer {token}"})
    assert count_res2.json()["unread_count"] == 0


def test_agency_isolation_and_recipient_authorization(client: TestClient, db_session):
    token1, user1_id, agency1_id = create_agency_and_user(
        client, "Agency Alpha", "alpha@agency.com"
    )
    token2, user2_id, agency2_id = create_agency_and_user(
        client, "Agency Beta", "beta@agency.com"
    )

    repo1 = NotificationRepository(db_session, uuid.UUID(agency1_id))
    n1 = repo1.create_notification(
        recipient_user_id=uuid.UUID(user1_id),
        notification_type=NotificationType.SYSTEM,
        title="Alpha Only Notice",
        message="Strictly confidential to Alpha.",
    )
    db_session.commit()

    # User 2 attempts to mark User 1's notification as read
    hack_res = client.patch(
        f"/api/v1/notifications/{n1.id}/read",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert hack_res.status_code == 404

    # User 2 listing should show 0 notifications
    list_res = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token2}"})
    assert list_res.status_code == 200
    assert list_res.json()["total"] == 0


# ============================================================
# 2. Agency Notification Preferences & RBAC Tests
# ============================================================

def test_agency_notification_preferences_and_rbac(client: TestClient):
    owner_token, owner_id, agency_id = create_agency_and_user(
        client, "Preferences Agency", "owner@prefs.com"
    )
    viewer_token, viewer_id = create_secondary_user(
        client, owner_token, agency_id, "viewer@prefs.com", role="VIEWER"
    )

    # Default settings
    get_res = client.get("/api/v1/notifications/settings", headers={"Authorization": f"Bearer {owner_token}"})
    assert get_res.status_code == 200, get_res.text
    defaults = get_res.json()
    assert defaults["email_enabled"] is True
    assert defaults["interview_notifications_enabled"] is True
    assert defaults["default_timezone"] == "Asia/Kolkata"

    # VIEWER can read
    viewer_get = client.get("/api/v1/notifications/settings", headers={"Authorization": f"Bearer {viewer_token}"})
    assert viewer_get.status_code == 200

    # VIEWER cannot modify settings (403 Forbidden)
    viewer_update = client.put(
        "/api/v1/notifications/settings",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"email_enabled": False},
    )
    assert viewer_update.status_code == 403

    # OWNER updates settings
    owner_update = client.put(
        "/api/v1/notifications/settings",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={
            "email_enabled": False,
            "candidate_email_updates_enabled": False,
        },
    )
    assert owner_update.status_code == 200
    updated = owner_update.json()
    assert updated["email_enabled"] is False
    assert updated["candidate_email_updates_enabled"] is False


# ============================================================
# 3. Email Templates & IST Formatting Tests
# ============================================================

def test_email_template_rendering_and_ist_formatting():
    start_utc = datetime(2026, 10, 20, 8, 30, tzinfo=timezone.utc)  # 14:00 IST
    end_utc = datetime(2026, 10, 20, 9, 30, tzinfo=timezone.utc)    # 15:00 IST

    # 1. Format IST range
    time_str = format_interview_ist_range(start_utc, end_utc)
    assert "20 Oct 2026" in time_str
    assert "02:00 PM - 03:00 PM IST (UTC+05:30)" in time_str

    # 2. Invitation template
    subj, html_content, text_content = render_interview_invitation(
        recipient_name="Kavita Rao",
        job_title="Lead Architect",
        round_name="Architecture Review",
        start_utc=start_utc,
        end_utc=end_utc,
        interview_mode="ONLINE",
        meeting_url="https://meet.hirelens.ai/arch-123",
        agency_name="Vertex Talent",
        is_candidate=True,
    )
    assert "Architecture Review" in subj
    assert "Lead Architect" in subj
    assert "02:00 PM - 03:00 PM IST (UTC+05:30)" in html_content
    assert "https://meet.hirelens.ai/arch-123" in html_content
    assert "https://meet.hirelens.ai/arch-123" in text_content

    # 3. Rescheduled template
    new_start = datetime(2026, 10, 21, 10, 0, tzinfo=timezone.utc)  # 15:30 IST
    new_end = datetime(2026, 10, 21, 11, 0, tzinfo=timezone.utc)    # 16:30 IST
    subj_r, html_r, text_r = render_interview_rescheduled(
        recipient_name="Kavita Rao",
        job_title="Lead Architect",
        round_name="Architecture Review",
        new_start_utc=new_start,
        new_end_utc=new_end,
        old_start_utc=start_utc,
        old_end_utc=end_utc,
        reason="Interviewer flight delay",
        agency_name="Vertex Talent",
    )
    assert "Rescheduled" in subj_r
    assert "Interviewer flight delay" in html_r
    assert "03:30 PM - 04:30 PM IST (UTC+05:30)" in html_r

    # 4. Status update privacy: Ensure internal recruiter notes are never exposed
    subj_s, html_s, text_s = render_application_status_update(
        recipient_name="Kavita Rao",
        job_title="Lead Architect",
        new_stage="SHORTLISTED",
        agency_name="Vertex Talent",
        is_candidate=True,
    )
    assert "Application Status Update" in subj_s
    assert "Shortlisted" in html_s
    # Strictly ensure no leaked private evaluation words
    assert "CONFIDENTIAL" not in html_s


# ============================================================
# 4. Lifecycle Event Integration Tests (Interview & Application)
# ============================================================

def test_interview_lifecycle_event_notifications(client: TestClient, db_session):
    mock_email_provider.clear()
    token, user_id, agency_id = create_agency_and_user(
        client, "Lifecycle Agency", "owner@lifecycle.com"
    )
    job = create_job(client, token, "Senior Backend Engineer")
    cand = create_candidate(client, token, "Nikhil Sen", "nikhil@talent.io")
    app = create_application(client, token, job["id"], cand["id"])

    now = datetime.now(timezone.utc)
    slot_start = now + timedelta(days=3, hours=10)
    slot_end = slot_start + timedelta(hours=1)

    # 1. Create Interview -> Triggers INTERVIEW_SCHEDULED notification and email outbox
    schedule_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Technical Deep Dive",
            "title": "Backend Architecture",
            "scheduled_start": slot_start.isoformat(),
            "scheduled_end": slot_end.isoformat(),
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "participant_name": "Lifecycle Admin",
                    "participant_email": "owner@lifecycle.com",
                    "user_id": user_id,
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert schedule_res.status_code == 201, schedule_res.text
    interview_id = schedule_res.json()["id"]

    # Verify notification created
    notifs = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}).json()
    assert any(n["notification_type"] == "INTERVIEW_SCHEDULED" for n in notifs["items"])

    # 2. Confirm Interview -> Triggers INTERVIEW_CONFIRMED notification
    confirm_res = client.post(
        f"/api/v1/interviews/{interview_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert confirm_res.status_code == 200

    notifs_after_confirm = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}).json()
    assert any(n["notification_type"] == "INTERVIEW_CONFIRMED" for n in notifs_after_confirm["items"])

    # 3. Reschedule Interview -> Triggers INTERVIEW_RESCHEDULED notification
    resched_start = slot_start + timedelta(days=1)
    resched_end = slot_end + timedelta(days=1)
    resched_res = client.post(
        f"/api/v1/interviews/{interview_id}/reschedule",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "scheduled_start": resched_start.isoformat(),
            "scheduled_end": resched_end.isoformat(),
            "timezone": "Asia/Kolkata",
            "reason": "Recruiter schedule adjustment",
        },
    )
    assert resched_res.status_code == 200

    notifs_after_resched = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}).json()
    assert any(n["notification_type"] == "INTERVIEW_RESCHEDULED" for n in notifs_after_resched["items"])

    # 4. Cancel Interview -> Triggers INTERVIEW_CANCELLED notification
    cancel_res = client.post(
        f"/api/v1/interviews/{interview_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Position filled internally"},
    )
    assert cancel_res.status_code == 200

    notifs_after_cancel = client.get("/api/v1/notifications", headers={"Authorization": f"Bearer {token}"}).json()
    assert any(n["notification_type"] == "INTERVIEW_CANCELLED" for n in notifs_after_cancel["items"])


def test_application_stage_change_notification_and_privacy(client: TestClient):
    token, user_id, agency_id = create_agency_and_user(
        client, "Stage Agency", "owner@stageagency.com"
    )
    recruiter_token, recruiter_id = create_secondary_user(
        client, token, agency_id, "assigned_recruiter@stageagency.com", role="RECRUITER"
    )

    job = create_job(client, token, "Full Stack Lead")
    cand = create_candidate(client, token, "Siddharth Rao", "siddharth@example.com")
    app = create_application(client, token, job["id"], cand["id"])

    # Assign recruiter to application
    client.patch(
        f"/api/v1/applications/{app['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_recruiter_id": recruiter_id},
    )

    # Actor (Owner) transitions stage from APPLIED to SHORTLISTED
    trans_res = client.post(
        f"/api/v1/applications/{app['id']}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "SHORTLISTED", "reason": "Strong profile"},
    )
    assert trans_res.status_code == 200

    # Assigned recruiter should receive in-app notification
    recruiter_notifs = client.get(
        "/api/v1/notifications", headers={"Authorization": f"Bearer {recruiter_token}"}
    ).json()
    assert any(
        n["notification_type"] == "APPLICATION_STATUS_UPDATED" and "Siddharth Rao" in n["title"]
        for n in recruiter_notifs["items"]
    )


# ============================================================
# 5. Outbox, Idempotency & Retry Tests
# ============================================================

def test_outbox_idempotency_and_duplicate_prevention(client: TestClient, db_session):
    agency_id = uuid.uuid4()
    repo = NotificationRepository(db_session, agency_id)

    idempotency_key = f"unique_event_key_{uuid.uuid4().hex}"

    # First enqueue
    out1 = repo.enqueue_outbox(
        event_type="TEST_EVENT",
        idempotency_key=idempotency_key,
        recipient_email="test@example.com",
        subject="Test Subject",
        body_html="<p>Test</p>",
        body_text="Test",
    )
    db_session.commit()
    assert out1 is not None

    # Duplicate enqueue with identical idempotency key returns existing record without creating duplicate
    out2 = repo.enqueue_outbox(
        event_type="TEST_EVENT",
        idempotency_key=idempotency_key,
        recipient_email="test@example.com",
        subject="Test Subject Duplicate",
        body_html="<p>Duplicate</p>",
        body_text="Duplicate",
    )
    db_session.commit()
    assert out1.id == out2.id


def test_outbox_retry_and_dead_letter_handling(client: TestClient, db_session):
    agency_id = uuid.uuid4()
    service = NotificationService(db_session, agency_id)
    repo = NotificationRepository(db_session, agency_id)

    idempotency_key = f"retry_key_{uuid.uuid4().hex}"
    out = repo.enqueue_outbox(
        event_type="FAIL_TEST",
        idempotency_key=idempotency_key,
        recipient_email="retry@example.com",
        subject="Retry Test Subject",
        body_html="<p>Body</p>",
        body_text="Body",
        max_retries=3,
    )
    db_session.commit()

    # Simulate provider failure
    mock_email_provider.fail_next = True
    mock_email_provider.failure_reason = "Simulated SMTP timeout"

    # Attempt 1 fails -> status FAILED, attempt_count 1
    success1 = service.dispatch_outbox_item(out.id)
    assert success1 is False
    db_session.refresh(out)
    assert out.status == NotificationDeliveryStatus.FAILED
    assert out.attempt_count == 1
    assert "Simulated SMTP timeout" in out.last_error

    # Attempt 2 fails -> status FAILED, attempt_count 2
    mock_email_provider.fail_next = True
    success2 = service.dispatch_outbox_item(out.id)
    assert success2 is False
    db_session.refresh(out)
    assert out.status == NotificationDeliveryStatus.FAILED
    assert out.attempt_count == 2

    # Attempt 3 fails -> reaches max_retries, transitions to DEAD_LETTER
    mock_email_provider.fail_next = True
    success3 = service.dispatch_outbox_item(out.id)
    assert success3 is False
    db_session.refresh(out)
    assert out.status == NotificationDeliveryStatus.DEAD_LETTER
    assert out.attempt_count == 3


def test_delivery_logs_rbac_and_manual_retry(client: TestClient, db_session):
    owner_token, owner_id, agency_id = create_agency_and_user(
        client, "Log Agency", "owner@logagency.com"
    )
    viewer_token, viewer_id = create_secondary_user(
        client, owner_token, agency_id, "viewer@logagency.com", role="VIEWER"
    )

    agency_uuid = uuid.UUID(agency_id)
    repo = NotificationRepository(db_session, agency_uuid)
    log = repo.record_delivery_log(
        recipient_email="failed_candidate@example.com",
        event_type="INTERVIEW_SCHEDULED",
        subject="Interview Invitation",
        provider="console",
        status=NotificationDeliveryStatus.FAILED,
        idempotency_key=f"log_test_{uuid.uuid4().hex}",
        attempt_count=1,
        error_message="Network unreachable",
    )
    db_session.commit()

    # VIEWER cannot access delivery logs (403)
    v_res = client.get("/api/v1/notifications/delivery-logs", headers={"Authorization": f"Bearer {viewer_token}"})
    assert v_res.status_code == 403

    # OWNER can view delivery logs
    o_res = client.get("/api/v1/notifications/delivery-logs", headers={"Authorization": f"Bearer {owner_token}"})
    assert o_res.status_code == 200
    data = o_res.json()
    assert data["total"] >= 1
    assert any(item["recipient_email"] == "failed_candidate@example.com" for item in data["items"])

    # OWNER retries failed delivery log
    retry_res = client.post(
        f"/api/v1/notifications/delivery-logs/{log.id}/retry",
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert retry_res.status_code == 200
    assert retry_res.json()["status"] == "SENT"


def test_failed_notification_does_not_rollback_core_interview(client: TestClient, monkeypatch):
    token, user_id, agency_id = create_agency_and_user(
        client, "Resilient Agency", "owner@resilient.com"
    )
    job = create_job(client, token, "Reliability Architect")
    cand = create_candidate(client, token, "Deepa Nair", "deepa@resilience.io")
    app = create_application(client, token, job["id"], cand["id"])

    now = datetime.now(timezone.utc)
    slot_start = now + timedelta(days=4, hours=10)
    slot_end = slot_start + timedelta(hours=1)

    # Force NotificationService to raise an unhandled exception inside on_interview_scheduled
    def broken_hook(self, *args, **kwargs):
        raise RuntimeError("Simulated catastrophic notification outage")

    monkeypatch.setattr(
        NotificationService,
        "on_interview_scheduled",
        broken_hook,
    )

    # Core interview scheduling MUST still commit and succeed with 201 Created!
    res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Core Resilience Test",
            "title": "System Design",
            "scheduled_start": slot_start.isoformat(),
            "scheduled_end": slot_end.isoformat(),
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "participant_name": "Resilient Admin",
                    "participant_email": "owner@resilient.com",
                    "user_id": user_id,
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert res.status_code == 201
    assert res.json()["round_name"] == "Core Resilience Test"
