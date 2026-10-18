import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.enums import (
    UserRole,
    AuditEventCategory,
    AuditSeverity,
    ConsentType,
    PrivacyRequestType,
    PrivacyRequestStatus,
    RetentionCategory,
    RetentionAction,
    RetentionExecutionType,
    RetentionStatus,
)
from app.models.governance import (
    UserSession,
    SecurityAuditEvent,
    CandidateConsentRecord,
    CandidatePrivacyRequest,
    AIGovernancePolicy,
    AIUsageLog,
    DataRetentionPolicy,
    RetentionExecutionLog,
)
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.application import Application
from app.services.governance_service import GovernanceService


def create_agency_and_user(
    client: TestClient, agency_name: str, email: str
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


def create_recruiter_user(
    client: TestClient, owner_token: str, email: str, name: str = "Recruiter User"
) -> tuple[str, str]:
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": email, "role": "RECRUITER"},
    )
    assert invite_res.status_code == 201, invite_res.text
    invite_token = invite_res.json()["token"]

    accept_res = client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": invite_token,
            "full_name": name,
            "password": "RecruiterPassword123!",
        },
    )
    assert accept_res.status_code == 201, accept_res.text

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "RecruiterPassword123!"},
    )
    assert login_res.status_code == 200, login_res.text
    recruiter_token = login_res.json()["tokens"]["access_token"]
    recruiter_id = login_res.json()["user"]["id"]
    return recruiter_token, recruiter_id


# =============================================================================
# 1. Security Audit Center & Immutability Tests
# =============================================================================
def test_security_audit_logging_and_filtering(client: TestClient, db_session: Session):
    """
    Tests security audit event logging, PII sanitization, and query filtering.
    """
    token, user_id, agency_id = create_agency_and_user(
        client, "Audit Agency", "audit_owner@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    service = GovernanceService(db_session, uuid.UUID(agency_id))
    # Log sensitive event with secret data
    service.log_security_event(
        event_category=AuditEventCategory.SECURITY_EVENT,
        severity=AuditSeverity.HIGH,
        action="API_KEY_ROTATED",
        resource_type="AgencyIntegration",
        resource_id=str(uuid.uuid4()),
        details={"token_secret": "my-secret-token", "provider": "Google"},
        actor_user_id=uuid.UUID(user_id),
        actor_email="audit_owner@corp.com",
    )

    # Fetch audit events via API
    res = client.get("/api/v1/governance/audit-events?category=SECURITY_EVENT", headers=headers)
    assert res.status_code == 200, res.text
    data = res.json()
    assert data["total"] >= 1
    event = data["items"][0]
    assert event["action"] == "API_KEY_ROTATED"
    assert event["severity"] == "HIGH"
    # Verify sanitization: token_secret was sanitized to [REDACTED]
    assert event["details"]["token_secret"] == "[REDACTED]"
    assert event["details"]["provider"] == "Google"


# =============================================================================
# 2. Server-Side Session Revocation Tests
# =============================================================================
def test_session_management_and_server_side_revocation(client: TestClient):
    """
    Validates server-side session creation during login, listing active sessions,
    and immediate 401 unauthorized rejection once session is revoked.
    """
    owner_token, _, _ = create_agency_and_user(
        client, "Session Agency", "session_admin@corp.com"
    )

    # Login to generate trackable session
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "session_admin@corp.com", "password": "SecurePassword123!"},
        headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
    )
    assert login_res.status_code == 200
    session_token = login_res.json()["tokens"]["access_token"]
    session_headers = {"Authorization": f"Bearer {session_token}"}

    # Verify session is listed and active
    sess_list = client.get("/api/v1/governance/sessions", headers=session_headers)
    assert sess_list.status_code == 200
    sessions = sess_list.json()
    assert len(sessions) >= 1
    active_session = sessions[0]
    assert active_session["is_active"] is True
    assert "Desktop" in active_session["device_info"]

    # Revoke this specific session
    del_res = client.delete(
        f"/api/v1/governance/sessions/{active_session['id']}",
        headers=session_headers,
    )
    assert del_res.status_code == 200
    assert del_res.json()["is_active"] is False

    # Immediate verification: subsequent request with this session token MUST fail with 401
    verify_blocked = client.get("/api/v1/governance/overview", headers=session_headers)
    assert verify_blocked.status_code == 401, verify_blocked.text
    assert "revoked" in verify_blocked.json()["detail"].lower()


def test_global_logout_invalidation(client: TestClient):
    """
    Tests global logout invalidating all user sessions and refresh tokens.
    """
    owner_token, user_id, _ = create_agency_and_user(
        client, "Global Logout Agency", "logout_admin@corp.com"
    )

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "logout_admin@corp.com", "password": "SecurePassword123!"},
    )
    tok = login_res.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {tok}"}

    # Execute global logout
    g_res = client.post("/api/v1/governance/sessions/global-logout", headers=headers)
    assert g_res.status_code == 200
    assert g_res.json()["status"] == "SUCCESS"

    # Token must now be rejected
    blocked = client.get("/api/v1/governance/overview", headers=headers)
    assert blocked.status_code == 401


# =============================================================================
# 3. Candidate Privacy & Consent Management Tests
# =============================================================================
def test_candidate_consent_grant_and_withdrawal(client: TestClient, db_session: Session):
    """
    Tests recording consent and subsequent withdrawal with auditable timestamps.
    """
    token, _, agency_id = create_agency_and_user(
        client, "Consent Agency", "consent_admin@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Create candidate
    cand_res = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"full_name": "Arjun Sharma", "email": "arjun@example.com"},
    )
    assert cand_res.status_code == 201
    cand_id = cand_res.json()["id"]

    # Record consent
    cons_res = client.post(
        "/api/v1/governance/consent",
        headers=headers,
        json={
            "candidate_id": cand_id,
            "consent_type": "DATA_PROCESSING",
            "policy_version": "v2.0",
            "purpose": "Evaluation for Engineering requisitions",
            "channel": "APPLICATION_PORTAL",
        },
    )
    assert cons_res.status_code == 200, cons_res.text
    consent_record = cons_res.json()
    assert consent_record["is_granted"] is True
    assert consent_record["policy_version"] == "v2.0"

    # Withdraw consent
    with_res = client.post(
        f"/api/v1/governance/consent/{consent_record['id']}/withdraw",
        headers=headers,
    )
    assert with_res.status_code == 200
    withdrawn = with_res.json()
    assert withdrawn["is_granted"] is False
    assert withdrawn["withdrawn_at"] is not None


def test_candidate_privacy_request_lifecycle(client: TestClient):
    """
    Tests logging and resolving a candidate privacy request.
    """
    token, _, _ = create_agency_and_user(
        client, "Privacy Request Agency", "dpo@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    cand_res = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"full_name": "Priya Nair", "email": "priya@privacy.in"},
    )
    cand_id = cand_res.json()["id"]

    # Create request
    pr_res = client.post(
        "/api/v1/governance/privacy-requests",
        headers=headers,
        json={
            "candidate_id": cand_id,
            "request_type": "DATA_ACCESS",
            "requested_by_email": "priya@privacy.in",
            "request_details": "Requesting full record export",
        },
    )
    assert pr_res.status_code == 200
    pr_id = pr_res.json()["id"]
    assert pr_res.json()["status"] == "PENDING"

    # Update request
    up_res = client.patch(
        f"/api/v1/governance/privacy-requests/{pr_id}",
        headers=headers,
        json={
            "status": "COMPLETED",
            "resolution_notes": "Data package exported and delivered via secure channel.",
        },
    )
    assert up_res.status_code == 200
    assert up_res.json()["status"] == "COMPLETED"
    assert up_res.json()["resolved_at"] is not None


def test_legal_hold_blocks_candidate_deletion(client: TestClient):
    """
    Verifies that an active legal hold strictly blocks candidate deletion requests.
    """
    token, _, _ = create_agency_and_user(
        client, "Legal Hold Agency", "legal@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    cand_res = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"full_name": "Vijay Kumar", "email": "vijay@legal.in"},
    )
    cand_id = cand_res.json()["id"]

    # Create deletion request with legal hold
    pr_res = client.post(
        "/api/v1/governance/privacy-requests",
        headers=headers,
        json={
            "candidate_id": cand_id,
            "request_type": "DATA_DELETION",
            "requested_by_email": "vijay@legal.in",
        },
    )
    pr_id = pr_res.json()["id"]

    # Place legal hold
    client.patch(
        f"/api/v1/governance/privacy-requests/{pr_id}",
        headers=headers,
        json={"has_legal_hold": True, "legal_hold_reason": "Pending compliance inquiry"},
    )

    # Attempt to complete deletion while under legal hold -> MUST fail with 400
    del_attempt = client.patch(
        f"/api/v1/governance/privacy-requests/{pr_id}",
        headers=headers,
        json={"status": "COMPLETED"},
    )
    assert del_attempt.status_code == 400
    assert "legal hold" in del_attempt.json()["detail"].lower()


def test_candidate_data_anonymization_integrity(client: TestClient, db_session: Session):
    """
    Verifies that fulfilling a deletion request without legal hold anonymizes
    personal data while preserving candidate ID and application structure.
    """
    token, _, _ = create_agency_and_user(
        client, "Anonymize Agency", "anon_admin@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    cand_res = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"full_name": "Rohan Mehra", "email": "rohan@test.in", "phone": "+919876543210"},
    )
    cand_id = cand_res.json()["id"]

    # Create deletion request
    pr_res = client.post(
        "/api/v1/governance/privacy-requests",
        headers=headers,
        json={
            "candidate_id": cand_id,
            "request_type": "DATA_DELETION",
            "requested_by_email": "rohan@test.in",
        },
    )
    pr_id = pr_res.json()["id"]

    # Complete deletion without hold
    comp_res = client.patch(
        f"/api/v1/governance/privacy-requests/{pr_id}",
        headers=headers,
        json={"status": "COMPLETED", "resolution_notes": "Candidate data anonymized."},
    )
    assert comp_res.status_code == 200

    # Query candidate directly from database
    cand = db_session.get(Candidate, uuid.UUID(cand_id))
    assert cand is not None
    assert cand.full_name.startswith("Candidate-")
    assert "anonymized" in cand.email
    assert cand.phone_encrypted is None


# =============================================================================
# 4. AI Governance & Data Retention Tests
# =============================================================================
def test_ai_governance_policy_and_usage(client: TestClient):
    """
    Tests configuring agency AI policies and viewing token telemetry.
    """
    token, _, _ = create_agency_and_user(
        client, "AI Gov Agency", "ai_admin@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Update policy
    pol_res = client.put(
        "/api/v1/governance/ai-policy",
        headers=headers,
        json={
            "allowed_providers": ["OLLAMA", "HOSTED_OPEN_WEIGHT"],
            "max_tokens_per_request": 3500,
            "monthly_token_budget": 250000,
            "require_pii_masking": True,
            "safety_filter_enabled": True,
        },
    )
    assert pol_res.status_code == 200
    pol = pol_res.json()
    assert pol["max_tokens_per_request"] == 3500
    assert pol["monthly_token_budget"] == 250000

    # Get usage metrics
    usage_res = client.get("/api/v1/governance/ai-usage", headers=headers)
    assert usage_res.status_code == 200
    usage = usage_res.json()
    assert "total_tokens" in usage
    assert "provider_breakdown" in usage


def test_data_retention_dry_run_and_execution(client: TestClient):
    """
    Tests retention policy listing, dry-run preview, and execution.
    """
    token, _, _ = create_agency_and_user(
        client, "Retention Agency", "retention_admin@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # List policies
    p_res = client.get("/api/v1/governance/retention-policies", headers=headers)
    assert p_res.status_code == 200
    policies = p_res.json()
    assert len(policies) == 6  # 6 retention categories

    cand_policy = next(p for p in policies if p["data_category"] == "CANDIDATE_RECORDS")

    # Update policy
    up_res = client.put(
        f"/api/v1/governance/retention-policies/{cand_policy['id']}",
        headers=headers,
        json={"retention_days": 180, "action_type": "ANONYMIZE", "is_enabled": True},
    )
    assert up_res.status_code == 200
    assert up_res.json()["retention_days"] == 180

    # Dry-run preview
    prev_res = client.post(
        f"/api/v1/governance/retention-policies/{cand_policy['id']}/preview",
        headers=headers,
    )
    assert prev_res.status_code == 200
    prev = prev_res.json()
    assert prev["retention_days"] == 180
    assert "cutoff_date" in prev

    # Live execute
    exec_res = client.post(
        f"/api/v1/governance/retention-policies/{cand_policy['id']}/execute",
        headers=headers,
    )
    assert exec_res.status_code == 200
    exec_log = exec_res.json()
    assert exec_log["status"] == "COMPLETED"
    assert exec_log["execution_type"] == "EXECUTE"


def test_governance_rbac_and_cross_agency_isolation(client: TestClient):
    """
    Verifies that ordinary recruiters cannot modify policies and cross-tenant
    audit records cannot be accessed.
    """
    token_a, _, agency_a = create_agency_and_user(
        client, "Gov Agency A", "owner_a@govtest.com"
    )
    token_b, _, agency_b = create_agency_and_user(
        client, "Gov Agency B", "owner_b@govtest.com"
    )

    recruiter_token, _ = create_recruiter_user(
        client, token_a, "recruiter_a@govtest.com", "Recruiter A"
    )

    # 1. Recruiter cannot view security audit events (403)
    rec_audit = client.get(
        "/api/v1/governance/audit-events",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert rec_audit.status_code == 403

    # 2. Recruiter cannot update retention policy (403)
    p_res = client.get(
        "/api/v1/governance/retention-policies",
        headers={"Authorization": f"Bearer {token_a}"},
    )
    policy_id = p_res.json()[0]["id"]
    rec_update = client.put(
        f"/api/v1/governance/retention-policies/{policy_id}",
        headers={"Authorization": f"Bearer {recruiter_token}"},
        json={"retention_days": 90},
    )
    assert rec_update.status_code == 403

    # 3. Agency B cannot see Agency A audit events
    audit_b = client.get(
        "/api/v1/governance/audit-events",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert audit_b.status_code == 200
    # No events from Agency A should appear in Agency B
    for ev in audit_b.json()["items"]:
        assert ev["actor_email"] != "owner_a@govtest.com"
