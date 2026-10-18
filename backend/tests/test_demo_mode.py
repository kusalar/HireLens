"""
Tests for Live Demo Mode (Dev Week 2 Challenge)
Verifies:
1. 1-Click demo session token minting.
2. IP rate-limiting protection.
3. Multi-tenant isolation for demo accounts.
4. Mutation guards preventing deletion or destructive edits of demo assets.
5. Unhindered exploration for judges and normal recruiters.
6. Self-healing ephemeral resume generation.
"""

import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.entities import Agency, User
from app.models.enums import UserRole, JobStatus
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.resume import Resume
from app.services.demo_service import (
    DEMO_USER_EMAIL,
    DEMO_AGENCY_SLUG,
    generate_synthetic_resume_pdf,
    check_demo_rate_limit,
)
from app.core.security import create_access_token


@pytest.fixture
def demo_fixture(db_session: Session):
    """Seed minimal demo agency and recruiter in test SQLite database."""
    agency = Agency(
        id=uuid.uuid4(),
        name="Apex Talent Partners [DEMO]",
        slug=DEMO_AGENCY_SLUG,
        country="IN",
        is_active=True,
    )
    db_session.add(agency)
    db_session.flush()

    user = User(
        id=uuid.uuid4(),
        agency_id=agency.id,
        email=DEMO_USER_EMAIL,
        hashed_password="hashed_demo_pw",
        full_name="Alex Morgan (Demo Recruiter)",
        role=UserRole.OWNER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(user)

    job = Job(
        id=uuid.uuid4(),
        agency_id=agency.id,
        created_by=user.id,
        title="Senior Full-Stack Engineer",
        status=JobStatus.ACTIVE,
    )
    db_session.add(job)

    cand = Candidate(
        id=uuid.uuid4(),
        agency_id=agency.id,
        full_name="Elena Rostova [Synthetic]",
        email="elena.rostova@synthetic-example.com",
        current_title="Senior Full-Stack Engineer",
    )
    db_session.add(cand)

    db_session.commit()
    return {"agency": agency, "user": user, "job": job, "candidate": cand}


def test_demo_session_endpoint(client: TestClient, demo_fixture):
    """Test 1-click demo session endpoint returns valid JWT and demo indicators."""
    response = client.post("/api/v1/auth/demo-session")
    assert response.status_code == 200
    data = response.json()

    assert "tokens" in data
    assert "access_token" in data["tokens"]
    assert data["user"]["email"] == DEMO_USER_EMAIL
    assert data["user"]["is_demo"] is True
    assert data["agency"]["is_demo"] is True
    assert data["agency"]["slug"] == DEMO_AGENCY_SLUG


def test_demo_rate_limiting():
    """Verify rate limiter blocks excessive requests from same IP."""
    test_ip = "192.168.99.1"
    # First 15 should pass
    for _ in range(15):
        assert check_demo_rate_limit(test_ip, max_requests=15, window_seconds=60) is True
    # 16th should fail
    assert check_demo_rate_limit(test_ip, max_requests=15, window_seconds=60) is False


def test_demo_recruiter_blocked_from_deleting_jobs(client: TestClient, demo_fixture):
    """Verify demo recruiter cannot delete jobs (mutation protection guard)."""
    token = create_access_token(demo_fixture["user"].id)
    headers = {"Authorization": f"Bearer {token}"}

    job_id = demo_fixture["job"].id
    del_resp = client.delete(f"/api/v1/jobs/{job_id}", headers=headers)

    assert del_resp.status_code == 403
    assert "Action restricted in Live Demo Mode" in del_resp.json()["detail"]


def test_demo_recruiter_blocked_from_billing_checkout(client: TestClient, demo_fixture):
    """Verify demo recruiter cannot initiate real checkout sessions."""
    token = create_access_token(demo_fixture["user"].id)
    headers = {"Authorization": f"Bearer {token}"}

    checkout_payload = {
        "plan_slug": "enterprise",
        "billing_interval": "MONTHLY",
        "gateway": "MOCK",
    }
    resp = client.post("/api/v1/billing/checkout", json=checkout_payload, headers=headers)
    assert resp.status_code == 403
    assert "Action restricted in Live Demo Mode" in resp.json()["detail"]


def test_demo_recruiter_blocked_from_inviting_members(client: TestClient, demo_fixture):
    """Verify demo recruiter cannot invite real external users to demo agency."""
    token = create_access_token(demo_fixture["user"].id)
    headers = {"Authorization": f"Bearer {token}"}

    invite_payload = {
        "email": "external_judge@example.com",
        "role": "RECRUITER",
    }
    resp = client.post("/api/v1/agency/members/invite", json=invite_payload, headers=headers)
    assert resp.status_code == 403
    assert "Action restricted in Live Demo Mode" in resp.json()["detail"]


def test_demo_recruiter_can_explore_safely(client: TestClient, demo_fixture):
    """Verify demo recruiter can freely browse jobs and candidates without error."""
    token = create_access_token(demo_fixture["user"].id)
    headers = {"Authorization": f"Bearer {token}"}

    # Can list jobs
    jobs_resp = client.get("/api/v1/jobs", headers=headers)
    assert jobs_resp.status_code == 200
    assert len(jobs_resp.json()) >= 1

    # Can list candidates
    cands_resp = client.get("/api/v1/candidates", headers=headers)
    assert cands_resp.status_code == 200
    assert len(cands_resp.json()) >= 1


def test_regular_recruiter_unhindered(client: TestClient, db_session: Session):
    """Verify regular agency users are unaffected by demo restrictions."""
    reg_agency = Agency(
        id=uuid.uuid4(),
        name="Real Recruitment Corp",
        slug="real-recruitment-corp",
        country="IN",
        is_active=True,
    )
    db_session.add(reg_agency)
    db_session.flush()

    reg_user = User(
        id=uuid.uuid4(),
        agency_id=reg_agency.id,
        email="recruiter@realcorp.com",
        hashed_password="pw",
        full_name="Normal Recruiter",
        role=UserRole.OWNER,
        is_active=True,
        is_verified=True,
    )
    db_session.add(reg_user)

    reg_job = Job(
        id=uuid.uuid4(),
        agency_id=reg_agency.id,
        created_by=reg_user.id,
        title="Software Engineer",
        status=JobStatus.ACTIVE,
    )
    db_session.add(reg_job)
    db_session.commit()

    assert reg_user.is_demo is False
    assert reg_agency.is_demo is False

    token = create_access_token(reg_user.id)
    headers = {"Authorization": f"Bearer {token}"}

    # Normal user CAN delete their own job
    del_resp = client.delete(f"/api/v1/jobs/{reg_job.id}", headers=headers)
    assert del_resp.status_code == 200
    assert del_resp.json()["message"] == "Job successfully deleted."


def test_demo_tenant_isolation(client: TestClient, demo_fixture, db_session: Session):
    """Verify demo recruiter cannot see or access jobs belonging to other agencies."""
    other_agency = Agency(
        id=uuid.uuid4(),
        name="Confidential Executive Search",
        slug="confidential-exec-search",
        country="US",
        is_active=True,
    )
    db_session.add(other_agency)
    db_session.flush()

    secret_job = Job(
        id=uuid.uuid4(),
        agency_id=other_agency.id,
        title="Confidential Chief Security Officer",
        status=JobStatus.ACTIVE,
    )
    db_session.add(secret_job)
    db_session.commit()

    token = create_access_token(demo_fixture["user"].id)
    headers = {"Authorization": f"Bearer {token}"}

    # List jobs returns only demo agency jobs
    jobs_resp = client.get("/api/v1/jobs", headers=headers)
    job_titles = [j["title"] for j in jobs_resp.json()]
    assert "Confidential Chief Security Officer" not in job_titles

    # Direct access to secret job ID fails with 404
    direct_resp = client.get(f"/api/v1/jobs/{secret_job.id}", headers=headers)
    assert direct_resp.status_code == 404


def test_synthetic_resume_pdf_generation():
    """Verify PyMuPDF synthesizes valid PDF bytes for demo candidates."""
    pdf_bytes = generate_synthetic_resume_pdf(
        candidate_name="Elena Rostova",
        title="Senior Full-Stack Engineer",
        skills=["Python", "FastAPI", "React", "PostgreSQL"],
        summary="Experienced engineer with strong distributed systems background.",
        experience_highlights=["Built high throughput services", "Managed database migrations"],
    )
    assert len(pdf_bytes) > 500
    assert pdf_bytes.startswith(b"%PDF")
