import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from app.models.enums import (
    UserRole,
    InterviewMode,
    InterviewStatus,
    InterviewRoundType,
    ParticipantRole,
    AttendanceStatus,
    FeedbackRecommendation,
    PipelineStageType,
)


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


def create_job(client: TestClient, token: str, title: str = "Lead Distributed Engineer") -> dict:
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
    client: TestClient, token: str, name: str = "Priya Sharma", email: str = "priya@example.com"
) -> dict:
    res = client.post(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": name,
            "email": email,
            "current_title": "Senior Systems Engineer",
            "total_experience_months": 72,
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
# 1. Interview Lifecycle Tests
# ============================================================

def test_create_and_retrieve_interview(client: TestClient):
    token, user_id, agency_id = create_agency_and_user(
        client, "Interview Agency", "owner@interviewagency.com"
    )
    job = create_job(client, token, "Staff Platform Engineer")
    cand = create_candidate(client, token, "Rohan Verma", "rohan@systems.io")
    app = create_application(client, token, job["id"], cand["id"])

    now = datetime.now(timezone.utc)
    start_time = now + timedelta(days=2, hours=10)
    end_time = start_time + timedelta(hours=1)

    # 1. Schedule Interview
    create_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round 1 - Architecture & Coding",
            "round_type": "TECHNICAL",
            "title": "Platform Architecture Deep Dive",
            "description": "Assess distributed databases and concurrent systems.",
            "interview_mode": "ONLINE",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "timezone": "Asia/Kolkata",
            "meeting_url": "https://meet.google.com/abc-defg-hij",
            "participants": [
                {
                    "user_id": user_id,
                    "participant_name": "Interview Agency Admin",
                    "participant_email": "owner@interviewagency.com",
                    "participant_role": "INTERVIEWER",
                },
                {
                    "participant_name": "External Advisor",
                    "participant_email": "advisor@external.com",
                    "participant_role": "OBSERVER",
                },
            ],
        },
    )
    assert create_res.status_code == 201, create_res.text
    int_data = create_res.json()
    interview_id = int_data["id"]

    assert int_data["round_name"] == "Round 1 - Architecture & Coding"
    assert int_data["round_type"] == "TECHNICAL"
    assert int_data["status"] == "SCHEDULED"
    assert int_data["candidate_name"] == "Rohan Verma"
    assert int_data["job_title"] == "Staff Platform Engineer"
    assert len(int_data["participants"]) == 2

    # 2. Retrieve Interview Detail
    detail_res = client.get(
        f"/api/v1/interviews/{interview_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["interview"]["id"] == interview_id
    assert detail["interview"]["status"] == "SCHEDULED"
    assert len(detail["participants"]) == 2
    assert len(detail["history"]) >= 1
    assert detail["history"][0]["action"] == "INTERVIEW_SCHEDULED"


def test_update_interview_details(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Update Corp", "update@corp.com")
    job = create_job(client, token, "Site Reliability Lead")
    cand = create_candidate(client, token, "Karan Singh", "karan@cloud.org")
    app = create_application(client, token, job["id"], cand["id"])

    start_time = datetime.now(timezone.utc) + timedelta(days=1)
    end_time = start_time + timedelta(minutes=45)

    create_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Screening",
            "round_type": "SCREENING",
            "title": "Initial Recruiter Screen",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = create_res.json()["id"]

    # Patch details
    patch_res = client.patch(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Recruiter Screen & Values Alignment",
            "description": "Updated assessment criteria for SRE role.",
            "meeting_url": "https://zoom.us/j/1234567890",
        },
    )
    assert patch_res.status_code == 200, patch_res.text
    assert patch_res.json()["title"] == "Recruiter Screen & Values Alignment"
    assert patch_res.json()["meeting_url"] == "https://zoom.us/j/1234567890"


def test_confirm_interview_and_idempotency(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Confirm Agency", "confirm@agency.com")
    job = create_job(client, token, "Security Architect")
    cand = create_candidate(client, token, "Vikram Seth", "vikram@sec.in")
    app = create_application(client, token, job["id"], cand["id"])

    start_time = datetime.now(timezone.utc) + timedelta(days=3)
    end_time = start_time + timedelta(hours=1)

    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Security Screen",
            "round_type": "TECHNICAL",
            "title": "Application Security Round",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Confirm
    conf1 = client.post(
        f"/api/v1/interviews/{int_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conf1.status_code == 200
    assert conf1.json()["status"] == "CONFIRMED"

    # Repeated confirmation is idempotent
    conf2 = client.post(
        f"/api/v1/interviews/{int_id}/confirm",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert conf2.status_code == 200
    assert conf2.json()["status"] == "CONFIRMED"


def test_reschedule_interview_and_history(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Reschedule Agency", "reschedule@agency.com")
    job = create_job(client, token, "Full Stack Lead")
    cand = create_candidate(client, token, "Sneha Patel", "sneha@dev.in")
    app = create_application(client, token, job["id"], cand["id"])

    orig_start = datetime.now(timezone.utc) + timedelta(days=2)
    orig_end = orig_start + timedelta(hours=1)

    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Full Stack Round",
            "round_type": "TECHNICAL",
            "title": "React & Python API Evaluation",
            "scheduled_start": orig_start.isoformat(),
            "scheduled_end": orig_end.isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    new_start = datetime.now(timezone.utc) + timedelta(days=4)
    new_end = new_start + timedelta(hours=1)

    # Reschedule
    resched = client.post(
        f"/api/v1/interviews/{int_id}/reschedule",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "scheduled_start": new_start.isoformat(),
            "scheduled_end": new_end.isoformat(),
            "reason": "Candidate requested postponement due to university exam.",
        },
    )
    assert resched.status_code == 200, resched.text
    assert resched.json()["status"] == "RESCHEDULED"

    # Verify history captures rescheduling
    hist_res = client.get(
        f"/api/v1/interviews/{int_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert hist_res.status_code == 200
    actions = [h["action"] for h in hist_res.json()]
    assert "INTERVIEW_RESCHEDULED" in actions


def test_cancel_interview_and_retention(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Cancel Agency", "cancel@agency.com")
    job = create_job(client, token, "DevOps Engineer")
    cand = create_candidate(client, token, "Amit Roy", "amit@infra.in")
    app = create_application(client, token, job["id"], cand["id"])

    start_time = datetime.now(timezone.utc) + timedelta(days=2)
    end_time = start_time + timedelta(hours=1)

    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Infra Round",
            "round_type": "TECHNICAL",
            "title": "Kubernetes & Cloud Networking",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Cancel
    cancel_res = client.post(
        f"/api/v1/interviews/{int_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Position put on hold by client."},
    )
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "CANCELLED"
    assert cancel_res.json()["cancellation_reason"] == "Position put on hold by client."

    # Cannot cancel again
    dup_cancel = client.post(
        f"/api/v1/interviews/{int_id}/cancel",
        headers={"Authorization": f"Bearer {token}"},
        json={"reason": "Trying to cancel again."},
    )
    assert dup_cancel.status_code == 400
    assert "already cancelled" in dup_cancel.json()["detail"]


def test_complete_interview(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Complete Agency", "complete@agency.com")
    job = create_job(client, token, "Lead Architect")
    cand = create_candidate(client, token, "Ananya Sen", "ananya@architect.com")
    app = create_application(client, token, job["id"], cand["id"])

    start_time = datetime.now(timezone.utc) - timedelta(hours=2)
    end_time = start_time + timedelta(hours=1)

    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Design Round",
            "round_type": "SYSTEM_DESIGN",
            "title": "System Design Evaluation",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Mark complete
    comp_res = client.post(
        f"/api/v1/interviews/{int_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "All questions answered with high depth."},
    )
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "COMPLETED"
    assert comp_res.json()["completed_at"] is not None

    # Cannot complete again
    dup_comp = client.post(
        f"/api/v1/interviews/{int_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "Completing again."},
    )
    assert dup_comp.status_code == 400


# ============================================================
# 2. Scheduling & Conflict Detection Tests
# ============================================================

def test_interviewer_scheduling_conflict_409(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Conflict Agency", "owner@conflict.com")
    job = create_job(client, token, "Senior Backend")
    cand1 = create_candidate(client, token, "Candidate 1", "cand1@test.com")
    cand2 = create_candidate(client, token, "Candidate 2", "cand2@test.com")
    app1 = create_application(client, token, job["id"], cand1["id"])
    app2 = create_application(client, token, job["id"], cand2["id"])

    start_time = datetime.now(timezone.utc) + timedelta(days=2, hours=14)
    end_time = start_time + timedelta(hours=1)

    # 1. Schedule interview for candidate 1 with user_id as interviewer
    r1 = client.post(
        f"/api/v1/applications/{app1['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round 1",
            "round_type": "TECHNICAL",
            "title": "Coding Round 1",
            "scheduled_start": start_time.isoformat(),
            "scheduled_end": end_time.isoformat(),
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "user_id": user_id,
                    "participant_name": "Lead Interviewer",
                    "participant_email": "owner@conflict.com",
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert r1.status_code == 201

    # 2. Attempt to schedule overlapping interview for candidate 2 with the SAME interviewer
    overlap_start = start_time + timedelta(minutes=30)
    overlap_end = overlap_start + timedelta(hours=1)

    r2 = client.post(
        f"/api/v1/applications/{app2['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round 1",
            "round_type": "TECHNICAL",
            "title": "Coding Round 2",
            "scheduled_start": overlap_start.isoformat(),
            "scheduled_end": overlap_end.isoformat(),
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "user_id": user_id,
                    "participant_name": "Lead Interviewer",
                    "participant_email": "owner@conflict.com",
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert r2.status_code == 409
    assert "Scheduling conflict" in r2.json()["detail"]


def test_invalid_timing_and_timezone(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Timing Agency", "timing@agency.com")
    job = create_job(client, token, "QA Lead")
    cand = create_candidate(client, token, "QA Candidate", "qa@test.com")
    app = create_application(client, token, job["id"], cand["id"])

    now = datetime.now(timezone.utc)

    # 1. End before start -> 400
    res1 = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Invalid Timing",
            "title": "Screening",
            "scheduled_start": (now + timedelta(hours=2)).isoformat(),
            "scheduled_end": (now + timedelta(hours=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    assert res1.status_code == 400
    assert "must be after start time" in res1.json()["detail"]

    # 2. Invalid timezone -> 400
    res2 = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Invalid TZ",
            "title": "Screening",
            "scheduled_start": (now + timedelta(hours=1)).isoformat(),
            "scheduled_end": (now + timedelta(hours=2)).isoformat(),
            "timezone": "Invalid/Fake_Zone",
        },
    )
    assert res2.status_code == 400
    assert "Invalid IANA timezone identifier" in res2.json()["detail"]


def test_archived_and_withdrawn_application_scheduling_blocked(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Archive Guard", "guard@agency.com")
    job = create_job(client, token, "Security Lead")
    cand = create_candidate(client, token, "Guard Candidate", "guard@test.com")
    app = create_application(client, token, job["id"], cand["id"])

    # 1. Archive the application
    client.patch(
        f"/api/v1/applications/{app['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"archived": True},
    )

    now = datetime.now(timezone.utc)
    res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Screening",
            "title": "Archived App Screening",
            "scheduled_start": (now + timedelta(days=1)).isoformat(),
            "scheduled_end": (now + timedelta(days=1, hours=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    assert res.status_code == 400
    assert "Cannot schedule an interview for an archived application" in res.json()["detail"]


# ============================================================
# 3. Feedback System & Privacy Tests
# ============================================================

def test_submit_feedback_and_duplicate_prevention(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Feedback Agency", "owner@feedback.com")
    job = create_job(client, token, "Senior Engineer")
    cand = create_candidate(client, token, "Feedback Candidate", "cand@feedback.com")
    app = create_application(client, token, job["id"], cand["id"])

    now = datetime.now(timezone.utc)
    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Technical Evaluation",
            "title": "Data Structures & Concurrency",
            "scheduled_start": (now + timedelta(hours=1)).isoformat(),
            "scheduled_end": (now + timedelta(hours=2)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # 1. First feedback submission succeeds -> 201
    f_res = client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "overall_rating": 4,
            "recommendation": "YES",
            "technical_assessment": "Demonstrated solid understanding of Python memory model.",
            "communication_assessment": "Clear, structured explanations.",
            "strengths": ["Fast problem solver", "Good distributed systems intuition"],
            "concerns": ["Slightly less experience in GraphQL"],
            "detailed_feedback": "Recommend moving candidate forward to final executive round.",
            "is_private": False,
        },
    )
    assert f_res.status_code == 201, f_res.text
    f_data = f_res.json()
    assert f_data["overall_rating"] == 4
    assert f_data["recommendation"] == "YES"
    assert len(f_data["strengths"]) == 2

    # 2. Duplicate feedback submission by the same reviewer is rejected -> 409 Conflict
    dup_res = client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "overall_rating": 5,
            "recommendation": "STRONG_YES",
            "detailed_feedback": "Trying to submit second review.",
        },
    )
    assert dup_res.status_code == 409
    assert "already submitted feedback" in dup_res.json()["detail"]


def test_private_feedback_protection(client: TestClient):
    token_owner, owner_id, _ = create_agency_and_user(client, "Privacy Agency", "owner@privacy.com")

    # Invite Recruiter 1
    inv1 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "rec1@privacy.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv1.json()["token"], "full_name": "Recruiter One", "password": "SecurePassword123!"},
    )
    rec1_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rec1@privacy.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    # Invite Recruiter 2
    inv2 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "rec2@privacy.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv2.json()["token"], "full_name": "Recruiter Two", "password": "SecurePassword123!"},
    )
    rec2_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rec2@privacy.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    job = create_job(client, token_owner, "Platform Architect")
    cand = create_candidate(client, token_owner, "Confidential Candidate", "conf@cand.com")
    app = create_application(client, token_owner, job["id"], cand["id"])

    now = datetime.now(timezone.utc)
    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={
            "round_name": "Technical Round",
            "title": "Private Evaluation Round",
            "scheduled_start": (now + timedelta(hours=1)).isoformat(),
            "scheduled_end": (now + timedelta(hours=2)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Recruiter 1 submits a PRIVATE feedback
    client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {rec1_token}"},
        json={
            "overall_rating": 2,
            "recommendation": "NO",
            "detailed_feedback": "Confidential compensation concern: candidate asked for 2x current salary.",
            "is_private": True,
        },
    )

    # 1. Author (Recruiter 1) CAN see their own private feedback
    detail_rec1 = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {rec1_token}"},
    )
    assert len(detail_rec1.json()["feedbacks"]) == 1
    assert detail_rec1.json()["feedbacks_count"] == 1
    assert detail_rec1.json()["average_rating"] == 2.0

    # 2. OWNER/ADMIN CAN see the private feedback
    detail_owner = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    )
    assert len(detail_owner.json()["feedbacks"]) == 1
    assert detail_owner.json()["feedbacks_count"] == 1
    assert detail_owner.json()["average_rating"] == 2.0

    # 3. Another recruiter (Recruiter 2) CANNOT see the private feedback, counts, or rating!
    detail_rec2 = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {rec2_token}"},
    )
    assert len(detail_rec2.json()["feedbacks"]) == 0
    assert detail_rec2.json()["feedbacks_count"] == 0
    assert detail_rec2.json()["average_rating"] is None


def test_interview_feedback_does_not_auto_change_application_stage(client: TestClient):
    token, _, _ = create_agency_and_user(client, "No Auto Agency", "noauto@agency.com")
    job = create_job(client, token, "Backend Developer")
    cand = create_candidate(client, token, "Candidate No Auto", "noauto@cand.com")
    app = create_application(client, token, job["id"], cand["id"])

    now = datetime.now(timezone.utc)
    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Final Interview",
            "title": "Evaluation",
            "scheduled_start": (now + timedelta(hours=1)).isoformat(),
            "scheduled_end": (now + timedelta(hours=2)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Submit a STRONG_YES review
    client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "overall_rating": 5,
            "recommendation": "STRONG_YES",
            "detailed_feedback": "Outstanding candidate.",
        },
    )

    # Complete the interview
    client.post(
        f"/api/v1/interviews/{int_id}/complete",
        headers={"Authorization": f"Bearer {token}"},
        json={"notes": "Round completed"},
    )

    # Verify Application stage remains APPLIED (NOT automatically changed to SELECTED)
    app_after = client.get(
        f"/api/v1/applications/{app['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert app_after.status_code == 200
    assert app_after.json()["application"]["status"] == "APPLIED"


# ============================================================
# 4. Multi-Tenancy & RBAC Tests
# ============================================================

def test_cross_agency_interview_access_blocked(client: TestClient):
    token_alpha, _, _ = create_agency_and_user(client, "Alpha Isolation", "alpha@isolation.com")
    token_beta, _, _ = create_agency_and_user(client, "Beta Isolation", "beta@isolation.com")

    job_alpha = create_job(client, token_alpha, "Alpha Job")
    cand_alpha = create_candidate(client, token_alpha, "Alpha Candidate", "alpha@cand.com")
    app_alpha = create_application(client, token_alpha, job_alpha["id"], cand_alpha["id"])

    now = datetime.now(timezone.utc)
    int_res = client.post(
        f"/api/v1/applications/{app_alpha['id']}/interviews",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={
            "round_name": "Technical",
            "title": "Alpha Technical Round",
            "scheduled_start": (now + timedelta(days=1)).isoformat(),
            "scheduled_end": (now + timedelta(days=1, hours=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Agency Beta cannot view Agency Alpha's interview -> 404
    get_res = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {token_beta}"},
    )
    assert get_res.status_code == 404

    # Agency Beta cannot cancel Agency Alpha's interview -> 404
    cancel_res = client.post(
        f"/api/v1/interviews/{int_id}/cancel",
        headers={"Authorization": f"Bearer {token_beta}"},
        json={"reason": "Attempting cross-tenant cancellation"},
    )
    assert cancel_res.status_code == 404


def test_rbac_viewer_mutation_restrictions(client: TestClient):
    token_owner, _, _ = create_agency_and_user(client, "Viewer Agency", "owner@vieweragency.com")
    job = create_job(client, token_owner, "Analytics Engineer")
    cand = create_candidate(client, token_owner, "Data Candidate", "data@cand.com")
    app = create_application(client, token_owner, job["id"], cand["id"])

    # Invite and activate a VIEWER
    inv = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "viewer@vieweragency.com", "role": "VIEWER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv.json()["token"], "full_name": "Read Only Viewer", "password": "SecurePassword123!"},
    )
    viewer_token = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@vieweragency.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    now = datetime.now(timezone.utc)

    # 1. VIEWER cannot schedule interview -> 403
    create_blocked = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "round_name": "Viewer Attempt",
            "title": "Attempt",
            "scheduled_start": (now + timedelta(days=1)).isoformat(),
            "scheduled_end": (now + timedelta(days=1, hours=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    assert create_blocked.status_code == 403

    # Owner creates interview
    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={
            "round_name": "Valid Round",
            "title": "Owner Scheduled Round",
            "scheduled_start": (now + timedelta(days=1)).isoformat(),
            "scheduled_end": (now + timedelta(days=1, hours=1)).isoformat(),
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # 2. VIEWER can view interview -> 200
    read_res = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert read_res.status_code == 200

    # 3. VIEWER cannot cancel interview -> 403
    cancel_blocked = client.post(
        f"/api/v1/interviews/{int_id}/cancel",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"reason": "Viewer trying to cancel"},
    )
    assert cancel_blocked.status_code == 403

    # 4. VIEWER cannot submit feedback -> 403
    feedback_blocked = client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={
            "overall_rating": 3,
            "recommendation": "MAYBE",
            "detailed_feedback": "Viewer trying to submit review",
        },
    )
    assert feedback_blocked.status_code == 403


# ============================================================
# Phase 6.1: Timezone Standardization & Production Hardening Tests
# ============================================================

def test_timezone_standardization_and_conversions(client: TestClient):
    """Verify naive Kolkata parsing, explicit +05:30 conversion, UTC storage, and invalid rejection."""
    token, user_id, agency_id = create_agency_and_user(
        client, "Timezone Agency", "tz@agency.com"
    )
    job = create_job(client, token, "Cloud Architect")
    cand = create_candidate(client, token, "Aarav Patel", "aarav@tz.com")
    app = create_application(client, token, job["id"], cand["id"])

    # 1. Naive Kolkata datetime: "2026-10-20T14:00:00" with timezone="Asia/Kolkata"
    # Expected UTC storage: 2026-10-20T08:30:00Z (since Kolkata is UTC+05:30)
    create_res1 = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round 1",
            "title": "System Design Round",
            "scheduled_start": "2026-10-20T14:00:00",
            "scheduled_end": "2026-10-20T15:00:00",
            "timezone": "Asia/Kolkata",
        },
    )
    assert create_res1.status_code == 201, create_res1.text
    int1 = create_res1.json()
    assert int1["timezone"] == "Asia/Kolkata"
    # Verify UTC storage
    assert "2026-10-20T08:30:00" in int1["scheduled_start"]
    assert "2026-10-20T09:30:00" in int1["scheduled_end"]
    # Verify calculated IST strings
    assert "IST" in int1.get("scheduled_start_ist", "")
    assert "2:00 PM" in int1.get("scheduled_start_ist", "")
    assert "3:00 PM" in int1.get("scheduled_end_ist", "")

    # 2. Explicit +05:30 offset: "2026-10-21T14:00:00+05:30"
    create_res2 = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round 2",
            "title": "Coding Round",
            "scheduled_start": "2026-10-21T14:00:00+05:30",
            "scheduled_end": "2026-10-21T15:00:00+05:30",
            "timezone": "Asia/Kolkata",
        },
    )
    assert create_res2.status_code == 201, create_res2.text
    int2 = create_res2.json()
    assert "2026-10-21T08:30:00" in int2["scheduled_start"]
    assert "2026-10-21T09:30:00" in int2["scheduled_end"]

    # 3. Explicit UTC with Z: "2026-10-22T08:30:00Z"
    create_res3 = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round 3",
            "title": "Culture Fit",
            "scheduled_start": "2026-10-22T08:30:00Z",
            "scheduled_end": "2026-10-22T09:30:00Z",
            "timezone": "Asia/Kolkata",
        },
    )
    assert create_res3.status_code == 201, create_res3.text
    int3 = create_res3.json()
    assert "2026-10-22T08:30:00" in int3["scheduled_start"]
    assert "2:00 PM" in int3.get("scheduled_start_ist", "")

    # 4. Invalid timezone rejection -> 422
    bad_tz_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Bad TZ Round",
            "title": "Invalid TZ",
            "scheduled_start": "2026-10-23T14:00:00",
            "scheduled_end": "2026-10-23T15:00:00",
            "timezone": "Moon/Base_Alpha",
        },
    )
    assert bad_tz_res.status_code in (400, 422)
    assert "Invalid IANA timezone identifier" in bad_tz_res.text

    # 5. Rescheduling conversion: reschedule int1 to 16:00 naive Kolkata
    # Expected UTC: 10:30:00Z
    reschedule_res = client.post(
        f"/api/v1/interviews/{int1['id']}/reschedule",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "scheduled_start": "2026-10-20T16:00:00",
            "scheduled_end": "2026-10-20T17:00:00",
            "timezone": "Asia/Kolkata",
            "reason": "Moved to 4 PM IST per candidate request",
        },
    )
    assert reschedule_res.status_code == 200, reschedule_res.text
    rescheduled = reschedule_res.json()
    assert "2026-10-20T10:30:00" in rescheduled["scheduled_start"]
    assert "2026-10-20T11:30:00" in rescheduled["scheduled_end"]
    assert "4:00 PM" in rescheduled.get("scheduled_start_ist", "")


def test_postgresql_advisory_lock_logic_and_deadlock_prevention(client: TestClient):
    """Verify deterministic 64-bit advisory lock key, sorted lock acquisition, and dialect safety."""
    from app.services.interview_service import InterviewService
    from app.core.timezone import parse_and_normalize_to_utc, validate_timezone

    # 1. Deterministic lock key calculation test
    agency_id = uuid.uuid4()
    user_id_1 = uuid.uuid4()
    user_id_2 = uuid.uuid4()

    key1 = InterviewService._compute_advisory_lock_key(agency_id, user_id_1)
    key1_repeat = InterviewService._compute_advisory_lock_key(agency_id, user_id_1)
    key2 = InterviewService._compute_advisory_lock_key(agency_id, user_id_2)

    assert isinstance(key1, int)
    assert key1 == key1_repeat  # Deterministic!
    assert key1 != key2  # Distinct interviewers have distinct keys!
    # Fits inside 64-bit signed integer
    assert -9223372036854775808 <= key1 <= 9223372036854775807

    # 2. Deadlock prevention: verify lock order is sorted ascending
    mock_db = MagicMock()
    mock_db.get_bind.return_value.dialect.name = "postgresql"

    service = InterviewService(mock_db, agency_id)
    # Pass unsorted IDs with None and duplicates
    unsorted_ids = [user_id_2, None, user_id_1, user_id_2]
    service._acquire_interviewer_locks(unsorted_ids)

    # Verify pg_advisory_xact_lock called for each unique interviewer in sorted UUID order
    expected_sorted = sorted([user_id_1, user_id_2])
    assert mock_db.execute.call_count == 2
    calls = mock_db.execute.call_args_list
    # execute(text("..."), {"key": lock_key}) passes dict in args[1]
    assert calls[0].args[1]["key"] == InterviewService.compute_advisory_lock_key(agency_id, expected_sorted[0])
    assert calls[1].args[1]["key"] == InterviewService.compute_advisory_lock_key(agency_id, expected_sorted[1])

    # 3. SQLite compatibility verification: dialect != postgresql skips pg_advisory_xact_lock
    mock_sqlite_db = MagicMock()
    mock_sqlite_db.get_bind.return_value.dialect.name = "sqlite"
    sqlite_service = InterviewService(mock_sqlite_db, agency_id)
    sqlite_service._acquire_interviewer_locks([user_id_1, user_id_2])
    assert mock_sqlite_db.execute.call_count == 0  # Safely bypassed on SQLite!


def test_private_feedback_count_and_average_masking_comprehensive(client: TestClient):
    """Verify that private feedback is fully masked from counts and averages for unauthorized recruiters and viewers."""
    token_owner, owner_id, agency_id = create_agency_and_user(
        client, "Privacy Masking Agency", "privacy_owner@mask.com"
    )

    # Recruiter 1
    inv1 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "rec1@mask.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv1.json()["token"], "full_name": "Recruiter One", "password": "SecurePassword123!"},
    )
    rec1_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rec1@mask.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    # Recruiter 2
    inv2 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "rec2@mask.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv2.json()["token"], "full_name": "Recruiter Two", "password": "SecurePassword123!"},
    )
    rec2_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rec2@mask.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    # Viewer
    inv3 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "viewer@mask.com", "role": "VIEWER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv3.json()["token"], "full_name": "Viewer User", "password": "SecurePassword123!"},
    )
    viewer_token = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@mask.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    job = create_job(client, token_owner, "Security Lead")
    cand = create_candidate(client, token_owner, "Rahul Nair", "rahul@mask.com")
    app = create_application(client, token_owner, job["id"], cand["id"])

    int_res = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={
            "round_name": "Final Panel",
            "title": "Executive Interview",
            "scheduled_start": "2026-10-25T14:00:00",
            "scheduled_end": "2026-10-25T15:00:00",
            "timezone": "Asia/Kolkata",
        },
    )
    int_id = int_res.json()["id"]

    # Recruiter 1 submits a PUBLIC feedback with rating = 5
    client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {rec1_token}"},
        json={
            "overall_rating": 5,
            "recommendation": "STRONG_YES",
            "detailed_feedback": "Excellent architectural knowledge.",
            "is_private": False,
        },
    )

    # Recruiter 2 submits a PRIVATE feedback with rating = 1
    client.post(
        f"/api/v1/interviews/{int_id}/feedback",
        headers={"Authorization": f"Bearer {rec2_token}"},
        json={
            "overall_rating": 1,
            "recommendation": "STRONG_NO",
            "detailed_feedback": "Private concern: integrity issue in previous role.",
            "is_private": True,
        },
    )

    # Check 1: Recruiter 1 (cannot see private feedback)
    # MUST see feedbacks_count == 1, average_rating == 5.0 (does not leak 1.0 or private presence)
    detail_rec1 = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {rec1_token}"},
    ).json()
    assert len(detail_rec1["feedbacks"]) == 1
    assert detail_rec1["feedbacks_count"] == 1
    assert detail_rec1["average_rating"] == 5.0

    # Check 2: VIEWER (cannot see private feedback)
    # MUST see feedbacks_count == 1, average_rating == 5.0
    detail_viewer = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    ).json()
    assert len(detail_viewer["feedbacks"]) == 1
    assert detail_viewer["feedbacks_count"] == 1
    assert detail_viewer["average_rating"] == 5.0

    # Check 3: Recruiter 2 (author of the private feedback)
    # CAN see both feedbacks: feedbacks_count == 2, average_rating == (5 + 1) / 2 = 3.0
    detail_rec2 = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {rec2_token}"},
    ).json()
    assert len(detail_rec2["feedbacks"]) == 2
    assert detail_rec2["feedbacks_count"] == 2
    assert detail_rec2["average_rating"] == 3.0

    # Check 4: OWNER (agency admin)
    # CAN see both feedbacks: feedbacks_count == 2, average_rating == 3.0
    detail_owner = client.get(
        f"/api/v1/interviews/{int_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
    ).json()
    assert len(detail_owner["feedbacks"]) == 2
    assert detail_owner["feedbacks_count"] == 2
    assert detail_owner["average_rating"] == 3.0

    # Check 5: Workspace interview list masking
    list_rec1 = client.get(
        "/api/v1/interviews",
        headers={"Authorization": f"Bearer {rec1_token}"},
    ).json()
    int_in_list = next(item for item in list_rec1["items"] if item["id"] == int_id)
    assert int_in_list["feedbacks_count"] == 1  # Masked!
    assert int_in_list["average_rating"] == 5.0  # Masked!


def test_interview_participant_update_conflict_detection(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Participant Agency", "part@agency.com")
    owner_user = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    owner_id = owner_user["id"]

    # Invite an additional interviewer
    inv = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"email": "interviewer2@agency.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv.json()["token"], "full_name": "Interviewer Two", "password": "SecurePassword123!"},
    )
    user2_token = client.post(
        "/api/v1/auth/login",
        json={"email": "interviewer2@agency.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]
    user2 = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {user2_token}"}).json()
    user2_id = user2["id"]

    job = create_job(client, token, "DevOps Engineer")
    cand = create_candidate(client, token, "Vikram Seth", "vikram@agency.com")
    app = create_application(client, token, job["id"], cand["id"])

    # 1. Schedule Interview A with Owner as participant from 14:00 to 15:00
    int_a = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round A",
            "title": "Initial Screen",
            "scheduled_start": "2026-10-28T14:00:00",
            "scheduled_end": "2026-10-28T15:00:00",
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "participant_name": "Owner",
                    "participant_email": "part@agency.com",
                    "user_id": owner_id,
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert int_a.status_code == 201

    # 2. Schedule Interview B with Interviewer 2 from 14:00 to 15:00 (no conflict initially)
    int_b = client.post(
        f"/api/v1/applications/{app['id']}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Round B",
            "title": "Second Round",
            "scheduled_start": "2026-10-28T14:00:00",
            "scheduled_end": "2026-10-28T15:00:00",
            "timezone": "Asia/Kolkata",
            "participants": [
                {
                    "participant_name": "Interviewer Two",
                    "participant_email": "interviewer2@agency.com",
                    "user_id": user2_id,
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert int_b.status_code == 201
    int_b_id = int_b.json()["id"]

    # 3. Attempt to update Interview B to assign Owner as participant -> 409 CONFLICT!
    patch_conflict = client.patch(
        f"/api/v1/interviews/{int_b_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "participants": [
                {
                    "participant_name": "Owner",
                    "participant_email": "part@agency.com",
                    "user_id": owner_id,
                    "participant_role": "INTERVIEWER",
                }
            ]
        },
    )
    assert patch_conflict.status_code == 409
    assert "Scheduling conflict" in patch_conflict.json()["detail"]

    # 4. Update Interview B with a non-internal participant or non-conflicting participant -> 200 OK
    patch_ok = client.patch(
        f"/api/v1/interviews/{int_b_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "participants": [
                {
                    "participant_name": "External Evaluator",
                    "participant_email": "external@advisor.com",
                    "participant_role": "OBSERVER",
                }
            ]
        },
    )
    assert patch_ok.status_code == 200
    detail_b = client.get(
        f"/api/v1/interviews/{int_b_id}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()
    assert len(detail_b["participants"]) == 1
    assert detail_b["participants"][0]["participant_email"] == "external@advisor.com"


