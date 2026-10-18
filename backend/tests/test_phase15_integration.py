import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import User, Agency, AgencyInvitation
from app.models.enums import UserRole, InvitationStatus, JobStatus
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.billing import SubscriptionPlan, AgencySubscription
from app.services.payment_gateways import MockPaymentAdapter


def create_agency_user(
    client: TestClient,
    agency_name: str,
    email: str,
    role: str = "OWNER",
) -> tuple[str, str, str]:
    """Helper creating an agency and returning (token, user_id, agency_id)."""
    res = client.post(
        "/api/v1/auth/register",
        json={
            "agency_name": agency_name,
            "full_name": f"{role} User",
            "email": email,
            "password": "Password123!",
        },
    )
    assert res.status_code == 201, res.text
    data = res.json()
    token = data["tokens"]["access_token"]
    user_id = data["user"]["id"]
    agency_id = data["user"]["agency_id"]

    if role != "OWNER":
        from app.db.session import SessionLocal
        db = SessionLocal()
        u = db.get(User, uuid.UUID(user_id))
        u.role = UserRole(role)
        db.commit()
        db.close()

    return token, user_id, agency_id


# =============================================================================
# 1. Platform Super Admin Authorization & Overview
# =============================================================================
def test_platform_admin_authorization_and_overview(client: TestClient, db_session: Session):
    token, user_id_str, agency_id_str = create_agency_user(
        client, "Platform Target Corp", "regular_owner@target.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Regular agency OWNER is blocked from platform endpoints with 403 Forbidden
    res = client.get("/api/v1/platform/overview", headers=headers)
    assert res.status_code == 403
    assert "Platform administrator privileges required" in res.json()["detail"]

    # 2. Grant PLATFORM_SUPER_ADMIN privilege
    user = db_session.get(User, uuid.UUID(user_id_str))
    user.is_platform_admin = True
    db_session.commit()

    # 3. Super admin succeeds
    res = client.get("/api/v1/platform/overview", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_agencies"] >= 1
    assert data["total_users"] >= 1
    assert "subscriptions_by_tier" in data
    assert "mrr_inr" in data
    assert "arr_inr" in data
    assert data["system_status"] in ["HEALTHY", "DEGRADED"]


# =============================================================================
# 2. Platform Agency Directory & Detailed Inspection
# =============================================================================
def test_platform_agency_directory_and_detail(client: TestClient, db_session: Session):
    token, user_id_str, agency_id_str = create_agency_user(
        client, "Directory Alpha Agency", "dir_admin@alpha.com"
    )
    user = db_session.get(User, uuid.UUID(user_id_str))
    user.is_platform_admin = True
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}

    # 1. List agencies with pagination
    res = client.get("/api/v1/platform/agencies?page=1&page_size=10", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total"] >= 1
    assert len(data["items"]) >= 1

    # Search for specific agency
    search_res = client.get("/api/v1/platform/agencies?search=Directory Alpha", headers=headers)
    assert search_res.status_code == 200
    assert any(a["id"] == agency_id_str for a in search_res.json()["items"])

    # 2. Inspect specific agency details
    detail_res = client.get(f"/api/v1/platform/agencies/{agency_id_str}", headers=headers)
    assert detail_res.status_code == 200
    agency_detail = detail_res.json()
    assert agency_detail["name"] == "Directory Alpha Agency"
    assert len(agency_detail["users"]) >= 1


# =============================================================================
# 3. Platform Agency Suspension & Reactivation with Audit
# =============================================================================
def test_platform_agency_suspension_and_reactivation_with_audit(
    client: TestClient, db_session: Session
):
    token_admin, admin_id, _ = create_agency_user(
        client, "Super Governance", "super_gov@hirelens.ai"
    )
    admin_u = db_session.get(User, uuid.UUID(admin_id))
    admin_u.is_platform_admin = True
    db_session.commit()

    token_target, _, target_agency_id = create_agency_user(
        client, "Suspension Candidate Ltd", "target_owner@suspend.com"
    )

    admin_headers = {"Authorization": f"Bearer {token_admin}"}
    target_headers = {"Authorization": f"Bearer {token_target}"}

    # 1. Suspend target agency
    suspend_res = client.patch(
        f"/api/v1/platform/agencies/{target_agency_id}/status",
        headers=admin_headers,
        json={"is_active": False, "reason": "Terms of Service Non-Compliance Investigation"},
    )
    assert suspend_res.status_code == 200
    assert suspend_res.json()["is_active"] is False

    # 2. Verify target user cannot access agency resources when suspended
    blocked_res = client.get("/api/v1/agency/profile", headers=target_headers)
    assert blocked_res.status_code == 403
    assert "Agency is inactive or not found" in blocked_res.json()["detail"]

    # 3. Reactivate agency
    reactivate_res = client.patch(
        f"/api/v1/platform/agencies/{target_agency_id}/status",
        headers=admin_headers,
        json={"is_active": True, "reason": "Compliance Verified and Reinstated"},
    )
    assert reactivate_res.status_code == 200
    assert reactivate_res.json()["is_active"] is True

    # 4. Target user can access resources again
    success_res = client.get("/api/v1/agency/profile", headers=target_headers)
    assert success_res.status_code == 200


# =============================================================================
# 4. Platform Audit Log Explorer
# =============================================================================
def test_platform_audit_log_explorer(client: TestClient, db_session: Session):
    token, user_id_str, agency_id_str = create_agency_user(
        client, "Audit Explorer Agency", "audit_explorer@corp.com"
    )
    user = db_session.get(User, uuid.UUID(user_id_str))
    user.is_platform_admin = True
    db_session.commit()

    headers = {"Authorization": f"Bearer {token}"}

    # Query cross-agency audit events
    res = client.get("/api/v1/platform/audit-logs?page=1&page_size=20", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data


# =============================================================================
# 5. System Health & Readiness Probes
# =============================================================================
def test_system_health_probes(client: TestClient, db_session: Session):
    # Public endpoints
    health_res = client.get("/health")
    assert health_res.status_code == 200
    assert health_res.json()["status"] == "healthy"

    live_res = client.get("/health/live")
    assert live_res.status_code == 200
    assert live_res.json()["status"] == "alive"

    ready_res = client.get("/health/ready")
    assert ready_res.status_code == 200
    assert ready_res.json()["status"] == "ready"
    assert ready_res.json()["database"] == "connected"

    # Protected platform health probe
    token, user_id_str, _ = create_agency_user(
        client, "Health Probe Agency", "health_admin@probe.com"
    )
    user = db_session.get(User, uuid.UUID(user_id_str))
    user.is_platform_admin = True
    db_session.commit()

    plat_health = client.get(
        "/api/v1/platform/health", headers={"Authorization": f"Bearer {token}"}
    )
    assert plat_health.status_code == 200
    h_data = plat_health.json()
    assert h_data["database"]["status"] == "UP"
    assert "storage" in h_data


# =============================================================================
# 6. Agency Admin Workspace & Recruiter Management
# =============================================================================
def test_agency_admin_overview_and_member_management(client: TestClient):
    token_owner, owner_id, agency_id = create_agency_user(
        client, "Agency Admin HQ", "hq_owner@agencyadmin.com"
    )
    headers = {"Authorization": f"Bearer {token_owner}"}

    # 1. Agency Overview endpoint
    overview_res = client.get("/api/v1/agency/overview", headers=headers)
    assert overview_res.status_code == 200
    ov = overview_res.json()
    assert ov["total_members"] >= 1
    assert "active_jobs_count" in ov
    assert "subscription_tier" in ov

    # 2. Invite a new recruiter
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        headers=headers,
        json={"email": "recruiter_new@agencyadmin.com", "role": "RECRUITER"},
    )
    assert invite_res.status_code == 201
    invite_data = invite_res.json()
    invite_id = invite_data["id"]

    # 3. List invitations
    invites_list = client.get("/api/v1/agency/invitations", headers=headers)
    assert invites_list.status_code == 200
    assert any(i["id"] == invite_id for i in invites_list.json())

    # 4. Revoke invitation
    cancel_res = client.delete(f"/api/v1/agency/invitations/{invite_id}", headers=headers)
    assert cancel_res.status_code == 200
    assert cancel_res.json()["status"] == "success"


# =============================================================================
# 7. Agency Member Status Toggle & Safety Guards
# =============================================================================
def test_agency_member_status_toggle_and_safety_guards(client: TestClient, db_session: Session):
    token_owner, owner_id_str, agency_id_str = create_agency_user(
        client, "Member Safety Agency", "safe_owner@safemembers.com"
    )
    headers = {"Authorization": f"Bearer {token_owner}"}

    # Register second recruiter
    from app.core.security import get_password_hash
    recruiter = User(
        id=uuid.uuid4(),
        agency_id=uuid.UUID(agency_id_str),
        email="recruiter_bob@safemembers.com",
        hashed_password=get_password_hash("Secret123!"),
        full_name="Bob Recruiter",
        role=UserRole.RECRUITER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(recruiter)
    db_session.commit()

    # 1. Deactivate recruiter Bob
    deact_res = client.patch(
        f"/api/v1/agency/members/{recruiter.id}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert deact_res.status_code == 200
    assert deact_res.json()["is_active"] is False

    # 2. Reactivate recruiter Bob
    react_res = client.patch(
        f"/api/v1/agency/members/{recruiter.id}/status",
        headers=headers,
        json={"is_active": True},
    )
    assert react_res.status_code == 200
    assert react_res.json()["is_active"] is True

    # 3. Safety Guard: Owner cannot deactivate themselves
    self_res = client.patch(
        f"/api/v1/agency/members/{owner_id_str}/status",
        headers=headers,
        json={"is_active": False},
    )
    assert self_res.status_code == 400
    assert "Cannot modify your own active status" in self_res.json()["detail"]


# =============================================================================
# 8. Cross-Agency Admin Isolation
# =============================================================================
def test_cross_agency_admin_isolation(client: TestClient):
    tok_a, _, _ = create_agency_user(client, "Isolated Tenant A", "owner_a@tenant.com")
    tok_b, _, _ = create_agency_user(client, "Isolated Tenant B", "owner_b@tenant.com")

    # Tenant B tries to invite someone to Tenant A (by calling using tok_b)
    # The invitation must strictly belong to Tenant B
    inv_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {tok_b}"},
        json={"email": "shared_invite@test.com", "role": "RECRUITER"},
    )
    assert inv_res.status_code == 201
    inv_b_id = inv_res.json()["id"]

    # Tenant A attempts to revoke Tenant B's invitation: MUST be 404
    cross_del = client.delete(
        f"/api/v1/agency/invitations/{inv_b_id}",
        headers={"Authorization": f"Bearer {tok_a}"},
    )
    assert cross_del.status_code == 404


# =============================================================================
# 9. Full End-to-End Multi-Tenant Lifecycle Integration
# =============================================================================
def test_end_to_end_saas_lifecycle_integration(client: TestClient, db_session: Session):
    # 1. Onboarding & Registration
    token, user_id_str, agency_id_str = create_agency_user(
        client, "Enterprise End2End Corp", "e2e_owner@corp.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Check initial FREE subscription
    sub_res = client.get("/api/v1/billing/subscription", headers=headers)
    assert sub_res.status_code == 200
    assert sub_res.json()["tier"] == "FREE"

    # 3. Create a Job
    job_res = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "title": "Principal AI Systems Engineer",
            "description": "Lead the engineering of next-generation multi-tenant recruitment AI.",
            "work_mode": "REMOTE",
            "employment_type": "FULL_TIME",
        },
    )
    assert job_res.status_code == 201

    # 4. Check real-time quota usage overview
    usage_res = client.get("/api/v1/billing/usage", headers=headers)
    assert usage_res.status_code == 200
    meters = usage_res.json()["meters"]
    assert "ACTIVE_JOBS" in meters


    # 5. Upgrade to PROFESSIONAL via Mock Gateway
    checkout_res = client.post(
        "/api/v1/billing/checkout",
        headers=headers,
        json={"plan_slug": "professional", "gateway": "MOCK"},
    )
    assert checkout_res.status_code == 200
    session_id = checkout_res.json()["session_id"]
    sig = MockPaymentAdapter().generate_valid_mock_signature(session_id)

    verify_res = client.post(
        "/api/v1/billing/verify-payment",
        headers=headers,
        json={"gateway": "MOCK", "session_id": session_id, "signature": sig},
    )
    assert verify_res.status_code == 200
    assert verify_res.json()["success"] is True
    assert verify_res.json()["subscription_status"] == "ACTIVE"

    # Verify subscription tier updated to PROFESSIONAL
    sub_updated = client.get("/api/v1/billing/subscription", headers=headers)
    assert sub_updated.status_code == 200
    assert sub_updated.json()["tier"] == "PROFESSIONAL"

    # 6. Verify invoice generation

    invoices_res = client.get("/api/v1/billing/invoices", headers=headers)
    assert invoices_res.status_code == 200
    assert len(invoices_res.json()) >= 1

    # 7. Super admin inspects this agency
    user = db_session.get(User, uuid.UUID(user_id_str))
    user.is_platform_admin = True
    db_session.commit()

    platform_detail = client.get(
        f"/api/v1/platform/agencies/{agency_id_str}", headers=headers
    )
    assert platform_detail.status_code == 200
    assert platform_detail.json()["subscription"]["tier"] == "PROFESSIONAL"
