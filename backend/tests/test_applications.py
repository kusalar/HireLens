import json
import uuid
import pytest
from fastapi.testclient import TestClient

from app.models.enums import (
    UserRole,
    PipelineStageType,
    JobStatus,
    WorkMode,
    EmploymentType,
    RequirementType,
    CandidateProfileStatus,
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


def create_job(client: TestClient, token: str, title: str = "Lead Backend Engineer") -> dict:
    res = client.post(
        "/api/v1/jobs",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": title,
            "department": "Engineering",
            "description": "Building high-performance distributed systems with Python.",
            "responsibilities": "Design microservices and data pipelines.",
            "location": "New York, NY",
            "work_mode": "HYBRID",
            "employment_type": "FULL_TIME",
            "minimum_experience": 4,
            "maximum_experience": 8,
            "requirements": [
                {
                    "requirement_text": "Python asynchronous frameworks",
                    "normalized_skill": "python",
                    "requirement_type": "SKILL",
                    "importance_weight": 1.0,
                    "is_mandatory": True,
                },
                {
                    "requirement_text": "PostgreSQL database optimization",
                    "normalized_skill": "postgresql",
                    "requirement_type": "SKILL",
                    "importance_weight": 0.8,
                    "is_mandatory": False,
                },
            ],
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_candidate(
    client: TestClient, token: str, name: str = "Alice Jenkins", email: str = "alice@example.com"
) -> dict:
    res = client.post(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": name,
            "email": email,
            "current_title": "Senior Software Engineer",
            "total_experience_months": 60,
            "current_location": "New York, NY",
            "professional_summary": "Extensive backend experience in Python and databases.",
            "profile_status": "ACTIVE",
            "skills": [
                {
                    "skill_name": "Python",
                    "normalized_skill": "python",
                    "proficiency": "EXPERT",
                    "evidence": "6 years building backend services.",
                },
                {
                    "skill_name": "PostgreSQL",
                    "normalized_skill": "postgresql",
                    "proficiency": "ADVANCED",
                    "evidence": "Optimized complex query execution plans.",
                },
            ],
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def test_application_creation_and_retrieval(client: TestClient):
    token, user_id, agency_id = create_agency_and_user(
        client, "Acme Staffing", "owner@acmestaffing.com"
    )
    job = create_job(client, token, "Senior Backend Engineer")
    candidate = create_candidate(client, token, "Devon Miles", "devon@miles.com")

    # 1. Create application
    res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "candidate_id": candidate["id"],
            "status": "APPLIED",
            "source": "AGENCY_SOURCED",
            "recruiter_summary": "Promising profile with 5 years backend experience.",
            "initial_note": "Spoke to candidate briefly; confirmed availability.",
        },
    )
    assert res.status_code == 201, res.text
    app_data = res.json()
    app_id = app_data["id"]

    assert app_data["job_id"] == job["id"]
    assert app_data["candidate_id"] == candidate["id"]
    assert app_data["status"] == "APPLIED"
    assert app_data["source"] == "AGENCY_SOURCED"
    assert app_data["recruiter_summary"] == "Promising profile with 5 years backend experience."
    assert app_data["candidate_name"] == "Devon Miles"
    assert app_data["job_title"] == "Senior Backend Engineer"
    assert app_data["shortlisted_at"] is None
    assert app_data["applied_at"] is not None
    assert app_data["last_activity_at"] is not None

    # 2. Get application detail
    detail_res = client.get(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200, detail_res.text
    detail = detail_res.json()
    assert detail["application"]["id"] == app_id
    assert detail["candidate"]["id"] == candidate["id"]
    assert detail["job"]["id"] == job["id"]

    # Verify initial stage history
    assert len(detail["stage_history"]) == 1
    hist = detail["stage_history"][0]
    assert hist["previous_stage"] is None
    assert hist["new_stage"] == "APPLIED"
    assert hist["changed_by"] == user_id

    # Verify initial note
    assert len(detail["notes"]) == 1
    assert detail["notes"][0]["content"] == "Spoke to candidate briefly; confirmed availability."

    # Verify activity history has APPLICATION_CREATED
    actions = [act["action"] for act in detail["activity"]]
    assert "APPLICATION_CREATED" in actions


def test_duplicate_application_prevention(client: TestClient):
    token, _, _ = create_agency_and_user(client, "TalentHub", "admin@talenthub.com")
    job = create_job(client, token, "DevOps Architect")
    candidate = create_candidate(client, token, "Sarah Connor", "sarah@resistance.com")

    # First application succeeds
    r1 = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    assert r1.status_code == 201

    # Second active application for same job and candidate fails with 409 Conflict
    r2 = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    assert r2.status_code == 409
    assert "already has an active application" in r2.json()["detail"]


def test_reapplication_allowed_after_withdrawn_or_archived(client: TestClient):
    token, _, _ = create_agency_and_user(client, "HireFlow", "lead@hireflow.com")
    job = create_job(client, token, "Full Stack Engineer")
    candidate = create_candidate(client, token, "John Doe", "john@doe.com")

    # 1. Create first application
    r1 = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app1_id = r1.json()["id"]

    # 2. Candidate withdraws application
    t_res = client.post(
        f"/api/v1/applications/{app1_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "WITHDRAWN", "reason": "Candidate accepted another offer"},
    )
    assert t_res.status_code == 200
    assert t_res.json()["status"] == "WITHDRAWN"

    # 3. Deliberate reapplication is now allowed!
    r2 = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "candidate_id": candidate["id"],
            "status": "APPLIED",
            "source": "REAPPLICATION",
        },
    )
    assert r2.status_code == 201
    assert r2.json()["id"] != app1_id
    assert r2.json()["status"] == "APPLIED"


def test_multiple_jobs_for_one_candidate(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Vertex Agency", "vertex@agency.com")
    job1 = create_job(client, token, "Frontend Specialist")
    job2 = create_job(client, token, "Mobile Developer")
    candidate = create_candidate(client, token, "Elena Rostova", "elena@tech.io")

    # Apply to Job 1
    r1 = client.post(
        f"/api/v1/jobs/{job1['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    assert r1.status_code == 201

    # Apply to Job 2
    r2 = client.post(
        f"/api/v1/jobs/{job2['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "UNDER_REVIEW"},
    )
    assert r2.status_code == 201

    # Query candidate's applications
    cand_apps_res = client.get(
        f"/api/v1/candidates/{candidate['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert cand_apps_res.status_code == 200
    cand_apps = cand_apps_res.json()
    assert len(cand_apps) == 2

    job_titles = {a["job_title"] for a in cand_apps}
    assert "Frontend Specialist" in job_titles
    assert "Mobile Developer" in job_titles


def test_tenant_isolation_cross_agency(client: TestClient):
    token1, _, agency1_id = create_agency_and_user(client, "Agency Alpha", "alpha@agency.com")
    token2, _, agency2_id = create_agency_and_user(client, "Agency Beta", "beta@agency.com")

    job_alpha = create_job(client, token1, "Job in Alpha")
    candidate_alpha = create_candidate(client, token1, "Alpha Candidate", "alpha@cand.com")

    job_beta = create_job(client, token2, "Job in Beta")
    candidate_beta = create_candidate(client, token2, "Beta Candidate", "beta@cand.com")

    # Agency Beta cannot create an application for Agency Alpha's job
    res1 = client.post(
        f"/api/v1/jobs/{job_alpha['id']}/applications",
        headers={"Authorization": f"Bearer {token2}"},
        json={"candidate_id": candidate_beta["id"]},
    )
    assert res1.status_code == 404

    # Agency Beta cannot create an application using Agency Alpha's candidate
    res2 = client.post(
        f"/api/v1/jobs/{job_beta['id']}/applications",
        headers={"Authorization": f"Bearer {token2}"},
        json={"candidate_id": candidate_alpha["id"]},
    )
    assert res2.status_code == 404

    # Agency Alpha creates an application
    create_res = client.post(
        f"/api/v1/jobs/{job_alpha['id']}/applications",
        headers={"Authorization": f"Bearer {token1}"},
        json={"candidate_id": candidate_alpha["id"]},
    )
    app_id = create_res.json()["id"]

    # Agency Beta cannot view Agency Alpha's application by UUID
    get_res = client.get(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert get_res.status_code == 404

    # Agency Beta cannot transition Agency Alpha's application
    trans_res = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token2}"},
        json={"new_stage": "SHORTLISTED"},
    )
    assert trans_res.status_code == 404


def test_stage_transitions_and_history_persistence(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Pipeline Pro", "recruiter@pipeline.com")
    job = create_job(client, token, "Site Reliability Engineer")
    candidate = create_candidate(client, token, "Ken Thompson", "ken@bell-labs.com")

    # Create application in APPLIED
    res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = res.json()["id"]
    assert res.json()["shortlisted_at"] is None

    # Step 1: Transition to UNDER_REVIEW
    t1 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "UNDER_REVIEW", "reason": "Initial screening of resume"},
    )
    assert t1.status_code == 200
    assert t1.json()["status"] == "UNDER_REVIEW"

    # Step 2: Transition to SHORTLISTED (verifying shortlisted_at timestamp is set)
    t2 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "SHORTLISTED", "reason": "Demonstrated strong distributed systems knowledge"},
    )
    assert t2.status_code == 200
    assert t2.json()["status"] == "SHORTLISTED"
    assert t2.json()["shortlisted_at"] is not None

    # Step 3: Transition to INTERVIEW
    t3 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "INTERVIEW", "reason": "Technical screen scheduled for Thursday 2pm"},
    )
    assert t3.status_code == 200
    assert t3.json()["status"] == "INTERVIEW"

    # Step 4: Transition to SELECTED
    t4 = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "SELECTED", "reason": "All rounds passed, offer extended"},
    )
    assert t4.status_code == 200
    assert t4.json()["status"] == "SELECTED"

    # Verify history persistence
    hist_res = client.get(
        f"/api/v1/applications/{app_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert hist_res.status_code == 200
    history = hist_res.json()
    assert len(history) == 5  # Initial + 4 transitions

    stages_sequence = [(h["previous_stage"], h["new_stage"]) for h in history]
    assert (None, "APPLIED") in stages_sequence
    assert ("APPLIED", "UNDER_REVIEW") in stages_sequence
    assert ("UNDER_REVIEW", "SHORTLISTED") in stages_sequence
    assert ("SHORTLISTED", "INTERVIEW") in stages_sequence
    assert ("INTERVIEW", "SELECTED") in stages_sequence


def test_invalid_stage_transitions(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Strict Pipeline", "strict@pipeline.com")
    job = create_job(client, token, "QA Automation Lead")
    candidate = create_candidate(client, token, "Grace Hopper", "grace@navy.mil")

    res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = res.json()["id"]

    # Transitioning to the exact same stage returns 400 Bad Request
    same_stage = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "APPLIED"},
    )
    assert same_stage.status_code == 400
    assert "already in 'APPLIED' stage" in same_stage.json()["detail"]


def test_recruiter_assignment_and_notes(client: TestClient):
    token, user_id, agency_id = create_agency_and_user(
        client, "Global Search", "head@globalsearch.com"
    )
    job = create_job(client, token, "Product Manager")
    candidate = create_candidate(client, token, "Ada Lovelace", "ada@analytical.org")

    res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = res.json()["id"]

    # Assign recruiter
    patch_res = client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"assigned_recruiter_id": user_id, "recruiter_summary": "Top tier candidate"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["assigned_recruiter_id"] == user_id
    assert patch_res.json()["assigned_recruiter_name"] == "Global Search Admin"

    # Query recruiter's applications
    rec_apps_res = client.get(
        f"/api/v1/recruiters/{user_id}/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert rec_apps_res.status_code == 200
    rec_apps = rec_apps_res.json()
    assert len(rec_apps) == 1
    assert rec_apps[0]["id"] == app_id

    # Add Note
    note_res = client.post(
        f"/api/v1/applications/{app_id}/notes",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Candidate requested $160k base salary."},
    )
    assert note_res.status_code == 201
    note_id = note_res.json()["id"]
    assert note_res.json()["author_id"] == user_id

    # Update Note
    patch_note_res = client.patch(
        f"/api/v1/applications/{app_id}/notes/{note_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Candidate requested $165k base salary (revised)."},
    )
    assert patch_note_res.status_code == 200
    assert patch_note_res.json()["content"] == "Candidate requested $165k base salary (revised)."


def test_matching_result_integration_and_stale_detection(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Matching Co", "match@agency.com")
    job = create_job(client, token, "AI Engineer")
    cand = create_candidate(client, token, "Alan Turing", "alan@bletchley.uk")

    # 1. Run matching engine
    match_run_res = client.post(
        f"/api/v1/jobs/{job['id']}/match",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert match_run_res.status_code == 201, match_run_res.text
    assert match_run_res.json()["completed_count"] >= 1

    # Check match result
    matches_res = client.get(
        f"/api/v1/jobs/{job['id']}/matches",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert matches_res.status_code == 200
    assert len(matches_res.json()["items"]) >= 1
    match_score = matches_res.json()["items"][0]["overall_score"]

    # 2. Recruiter creates application — NOT automatically shortlisted!
    app_res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": cand["id"], "status": "APPLIED"},
    )
    assert app_res.status_code == 201
    assert app_res.json()["status"] == "APPLIED"
    assert app_res.json()["shortlisted_at"] is None

    # Application list shows matching score
    list_res = client.get(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert list_res.status_code == 200
    apps = list_res.json()["items"]
    assert len(apps) == 1
    assert apps[0]["latest_match_score"] == match_score
    assert apps[0]["is_stale_match"] is False

    # 3. Update candidate profile -> verify stale detection
    patch_cand = client.patch(
        f"/api/v1/candidates/{cand['id']}",
        headers={"Authorization": f"Bearer {token}"},
        json={"current_title": "Chief AI Scientist"},
    )
    assert patch_cand.status_code == 200

    # Query application again — should reflect stale status
    detail_res = client.get(
        f"/api/v1/applications/{app_res.json()['id']}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200
    assert detail_res.json()["latest_match_result"]["is_stale"] is True


def test_candidate_comparison(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Compare Partners", "compare@agency.com")
    job = create_job(client, token, "Cloud Architect")
    cand1 = create_candidate(client, token, "Candidate One", "one@cloud.com")
    cand2 = create_candidate(client, token, "Candidate Two", "two@cloud.com")

    # Run matching
    client.post(
        f"/api/v1/jobs/{job['id']}/match",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Compare via POST
    compare_res = client.post(
        f"/api/v1/jobs/{job['id']}/compare",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_ids": [cand1["id"], cand2["id"]]},
    )
    assert compare_res.status_code == 200
    comp = compare_res.json()
    assert comp["job_id"] == job["id"]
    assert len(comp["candidates"]) == 2
    assert len(comp["criteria_matrix"]) >= 1

    # Verify each row in criteria matrix contains evaluations for both candidates
    for row in comp["criteria_matrix"]:
        assert str(cand1["id"]) in row["evaluations"]
        assert str(cand2["id"]) in row["evaluations"]


def test_dashboard_stats_endpoint(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Analytics Firm", "stats@firm.com")
    job = create_job(client, token, "SecOps Engineer")
    cand1 = create_candidate(client, token, "Sec One", "one@sec.com")
    cand2 = create_candidate(client, token, "Sec Two", "two@sec.com")

    # Create one APPLIED and one SHORTLISTED
    client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": cand1["id"], "status": "APPLIED"},
    )
    client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": cand2["id"], "status": "SHORTLISTED"},
    )

    # Fetch dashboard stats
    stats_res = client.get(
        "/api/v1/applications/dashboard/stats",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert stats["total_active_applications"] >= 2
    assert stats["stage_counts"]["APPLIED"] >= 1
    assert stats["stage_counts"]["SHORTLISTED"] >= 1
    assert len(stats["job_summaries"]) >= 1
    assert len(stats["recent_activities"]) >= 2


def test_rbac_viewer_restrictions(client: TestClient):
    token_owner, _, agency_id = create_agency_and_user(
        client, "RBAC Agency", "owner@rbacagency.com"
    )
    job = create_job(client, token_owner, "Data Scientist")
    candidate = create_candidate(client, token_owner, "Claude Shannon", "claude@mit.edu")

    # Invite and accept a VIEWER
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "viewer@rbacagency.com", "role": "VIEWER"},
    )
    assert invite_res.status_code == 201
    invite_token = invite_res.json()["token"]

    accept_res = client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": invite_token,
            "full_name": "Read Only Viewer",
            "password": "SecurePassword123!",
        },
    )
    assert accept_res.status_code == 201

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@rbacagency.com", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    viewer_token = login_res.json()["tokens"]["access_token"]

    # 1. VIEWER can read applications list
    read_list = client.get(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert read_list.status_code == 200

    # 2. VIEWER cannot create an application (403 Forbidden)
    create_blocked = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    assert create_blocked.status_code == 403

    # Owner creates application
    owner_create = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = owner_create.json()["id"]

    # 3. VIEWER can read application detail
    read_detail = client.get(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
    )
    assert read_detail.status_code == 200

    # 4. VIEWER cannot transition stage (403 Forbidden)
    trans_blocked = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"new_stage": "SHORTLISTED"},
    )
    assert trans_blocked.status_code == 403

    # 5. VIEWER cannot update application (403 Forbidden)
    update_blocked = client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"recruiter_summary": "Attempt by viewer"},
    )
    assert update_blocked.status_code == 403

    # 6. VIEWER cannot add notes (403 Forbidden)
    note_blocked = client.post(
        f"/api/v1/applications/{app_id}/notes",
        headers={"Authorization": f"Bearer {viewer_token}"},
        json={"content": "Viewer trying to add note"},
    )
    assert note_blocked.status_code == 403


def test_candidate_master_profile_preserved(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Master Guard", "guard@agency.com")
    job = create_job(client, token, "Embedded Engineer")
    candidate = create_candidate(client, token, "Margaret Hamilton", "margaret@apollo.nasa.gov")

    original_name = candidate["full_name"]
    original_email = candidate["email"]
    original_exp = candidate["total_experience_months"]

    # Create application and transition stages
    r = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = r.json()["id"]

    client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "REJECTED", "reason": "Not enough embedded experience"},
    )

    # Verify candidate master profile in Candidate repository remains 100% unchanged
    cand_after = client.get(
        f"/api/v1/candidates/{candidate['id']}",
        headers={"Authorization": f"Bearer {token}"},
    ).json()

    assert cand_after["full_name"] == original_name
    assert cand_after["email"] == original_email
    assert cand_after["total_experience_months"] == original_exp
    assert cand_after["profile_status"] == "ACTIVE"  # Master profile status not affected by job application rejection


def test_concurrent_application_creation_and_database_uniqueness(client: TestClient, db_session):
    """
    Verify database-level partial unique index (uq_active_application_per_job_candidate)
    prevents duplicate active applications even under concurrent race conditions where
    two workers simultaneously pass the preliminary SELECT query.
    """
    from concurrent.futures import ThreadPoolExecutor
    from sqlalchemy.exc import IntegrityError
    from app.models.application import Application
    from app.services.application_service import ApplicationService
    from app.models.entities import User

    token, user_id, agency_id_str = create_agency_and_user(
        client, "Concurrency Agency", "concurrency@agency.com"
    )
    job = create_job(client, token, "Concurrent Backend Lead")
    candidate = create_candidate(client, token, "Concurrent Candidate", "conc@candidate.com")
    agency_id = uuid.UUID(agency_id_str)
    job_id = uuid.UUID(job["id"])
    cand_id = uuid.UUID(candidate["id"])

    # 1. ThreadPool concurrency test via API
    def attempt_create():
        return client.post(
            f"/api/v1/jobs/{job['id']}/applications",
            headers={"Authorization": f"Bearer {token}"},
            json={"candidate_id": candidate["id"], "status": "APPLIED"},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        f1 = executor.submit(attempt_create)
        f2 = executor.submit(attempt_create)
        r1 = f1.result()
        r2 = f2.result()

    status_codes = sorted([r1.status_code, r2.status_code])
    assert status_codes == [201, 409], f"Expected one 201 and one 409, got {status_codes}"

    # 2. Direct database-level partial unique constraint audit
    # Attempting to bypass service logic and directly insert a second active application
    # MUST raise IntegrityError from the database index
    with db_session.begin_nested():
        app_dup = Application(
            id=uuid.uuid4(),
            agency_id=agency_id,
            job_id=job_id,
            candidate_id=cand_id,
            status=PipelineStageType.UNDER_REVIEW,
            version=1,
        )
        db_session.add(app_dup)
        with pytest.raises(IntegrityError):
            db_session.flush()

    # 3. Verify exactly one active application survives in the database
    apps_list = client.get(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert apps_list.status_code == 200
    assert apps_list.json()["total"] == 1
    assert len(apps_list.json()["items"]) == 1


def test_deletion_integrity_preserves_application_history(client: TestClient, db_session):
    """
    Verify historical integrity:
    Attempting to physically delete a job with active/historical applications is blocked
    to protect recruitment history and prevent silent cascading data loss.
    """
    from app.services.job_service import JobService
    from app.models.entities import User
    from fastapi import HTTPException

    token, user_id, agency_id_str = create_agency_and_user(
        client, "Retention Agency", "retention@agency.com"
    )
    job = create_job(client, token, "DevOps Engineer")
    candidate = create_candidate(client, token, "Retention Candidate", "ret@cand.com")
    agency_id = uuid.UUID(agency_id_str)
    job_id = uuid.UUID(job["id"])

    # Create application, note, and stage transition
    create_res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = create_res.json()["id"]

    client.post(
        f"/api/v1/applications/{app_id}/notes",
        headers={"Authorization": f"Bearer {token}"},
        json={"content": "Important interview note for candidate."},
    )

    client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "UNDER_REVIEW", "reason": "Initial screening passed"},
    )

    # Attempting to delete the job must be rejected with 400 Bad Request
    user = db_session.query(User).filter(User.id == uuid.UUID(user_id)).first()
    job_service = JobService(db_session, agency_id)

    with pytest.raises(HTTPException) as exc_info:
        job_service.delete_job(user, job_id)

    assert exc_info.value.status_code == 400
    assert "associated application(s)" in exc_info.value.detail
    assert "Archive or close the job instead" in exc_info.value.detail

    # Verify application, notes, and stage history remain completely intact
    detail_res = client.get(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert len(detail["notes"]) == 1
    assert len(detail["stage_history"]) == 2


def test_recruiter_assignment_tenant_validation_and_unassignment(client: TestClient, db_session):
    """
    Audit Recruiter Assignment:
    - Assigned recruiter must belong to same agency.
    - Cross-agency assignment returns 404.
    - Unassignment works cleanly and is audit-logged.
    - VIEWER cannot modify assignments.
    """
    from app.models.entities import AuditLog

    # Create Agency Alpha and Recruiter Alpha
    token_alpha, owner_alpha_id, agency_alpha_str = create_agency_and_user(
        client, "Alpha Recruiters", "owner@alpha.com"
    )
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"email": "recruiter@alpha.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": invite_res.json()["token"],
            "full_name": "Recruiter Alpha",
            "password": "SecurePassword123!",
        },
    )
    login_rec_a = client.post(
        "/api/v1/auth/login",
        json={"email": "recruiter@alpha.com", "password": "SecurePassword123!"},
    )
    recruiter_alpha_id = login_rec_a.json()["user"]["id"]

    # Create Agency Beta and Recruiter Beta
    token_beta, _, _ = create_agency_and_user(
        client, "Beta Recruiters", "owner@beta.com"
    )
    invite_beta = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_beta}"},
        json={"email": "recruiter@beta.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": invite_beta.json()["token"],
            "full_name": "Recruiter Beta",
            "password": "SecurePassword123!",
        },
    )
    login_rec_b = client.post(
        "/api/v1/auth/login",
        json={"email": "recruiter@beta.com", "password": "SecurePassword123!"},
    )
    recruiter_beta_id = login_rec_b.json()["user"]["id"]

    job_alpha = create_job(client, token_alpha, "Alpha Machine Learning")
    cand_alpha = create_candidate(client, token_alpha, "Alpha ML Candidate", "ml@alpha.com")

    # 1. Create application in Agency Alpha
    app_res = client.post(
        f"/api/v1/jobs/{job_alpha['id']}/applications",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"candidate_id": cand_alpha["id"], "status": "APPLIED"},
    )
    app_id = app_res.json()["id"]

    # 2. Attempt cross-agency recruiter assignment (Agency Beta recruiter to Agency Alpha application) -> 404
    cross_assign = client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"assigned_recruiter_id": recruiter_beta_id},
    )
    assert cross_assign.status_code == 404
    assert "not found or does not belong to your agency" in cross_assign.json()["detail"]

    # 3. Non-existent UUID assignment -> 404
    random_uuid = str(uuid.uuid4())
    fake_assign = client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"assigned_recruiter_id": random_uuid},
    )
    assert fake_assign.status_code == 404

    # 4. Valid assignment within Agency Alpha -> 200
    valid_assign = client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"assigned_recruiter_id": recruiter_alpha_id},
    )
    assert valid_assign.status_code == 200
    assert valid_assign.json()["assigned_recruiter_id"] == recruiter_alpha_id
    assert valid_assign.json()["assigned_recruiter_name"] == "Recruiter Alpha"

    # 5. Unassign recruiter via unassign_recruiter: True -> 200
    unassign_res = client.patch(
        f"/api/v1/applications/{app_id}",
        headers={"Authorization": f"Bearer {token_alpha}"},
        json={"unassign_recruiter": True},
    )
    assert unassign_res.status_code == 200
    assert unassign_res.json()["assigned_recruiter_id"] is None
    assert unassign_res.json()["assigned_recruiter_name"] is None

    # Verify audit logs for RECRUITER_ASSIGNED and RECRUITER_UNASSIGNED
    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.agency_id == uuid.UUID(agency_alpha_str),
            AuditLog.resource_id == app_id,
        )
        .all()
    )
    logged_actions = {l.action for l in logs}
    assert "RECRUITER_ASSIGNED" in logged_actions
    assert "RECRUITER_UNASSIGNED" in logged_actions


def test_concurrent_stage_transition_occ_protection(client: TestClient, db_session):
    """
    Audit Stage Transition Concurrency & OCC:
    - Atomic OCC version check prevents silent overwriting during concurrent stage changes.
    - A transition executed against a stale version triggers 409 Conflict.
    - Retried requests for the same stage return 400 Bad Request and do not append duplicate history.
    """
    from app.services.application_service import ApplicationService
    from app.schemas.application import ApplicationStageTransition
    from app.models.entities import User
    from app.models.application import Application
    from fastapi import HTTPException

    token, user_id, agency_id_str = create_agency_and_user(
        client, "OCC Transition Agency", "occ@agency.com"
    )
    job = create_job(client, token, "OCC Architect")
    candidate = create_candidate(client, token, "OCC Candidate", "occ@cand.com")
    agency_id = uuid.UUID(agency_id_str)

    # 1. Create application (starts at version = 1)
    app_res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json={"candidate_id": candidate["id"], "status": "APPLIED"},
    )
    app_id = uuid.UUID(app_res.json()["id"])

    user = db_session.query(User).filter(User.id == uuid.UUID(user_id)).first()
    service1 = ApplicationService(db_session, agency_id)

    # 2. First transition succeeds via API: APPLIED -> UNDER_REVIEW (increments version from 1 to 2)
    t1_res = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "UNDER_REVIEW", "reason": "Review round 1"},
    )
    assert t1_res.status_code == 200
    assert t1_res.json()["status"] == "UNDER_REVIEW"

    # 3. Retry idempotency check:
    # Retrying the exact same transition when application is already in UNDER_REVIEW returns 400 Bad Request
    retry_res = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": "UNDER_REVIEW", "reason": "Network retry"},
    )
    assert retry_res.status_code == 400
    assert "already in 'UNDER_REVIEW' stage" in retry_res.json()["detail"]

    # 4. Simulate concurrent race condition:
    # A second worker attempts to transition using an Application object loaded with stale version 1
    # Since current version in DB is 2, an update specifying version == 1 updates 0 rows and triggers 409 Conflict
    user = db_session.query(User).filter(User.id == uuid.UUID(user_id)).first()
    service1 = ApplicationService(db_session, agency_id)
    app_stale = service1.repo.get_with_details(app_id)
    app_stale.version = 1  # artificially set to stale version 1

    with pytest.raises(HTTPException) as exc_info:
        service1.transition_stage(
            app_id, user, ApplicationStageTransition(new_stage=PipelineStageType.SHORTLISTED, reason="Concurrent attempt")
        )
    assert exc_info.value.status_code == 409
    assert "Concurrent stage modification detected" in exc_info.value.detail

    # Verify stage history only has Initial (APPLIED) + first transition (UNDER_REVIEW)
    history_res = client.get(
        f"/api/v1/applications/{app_id}/history",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert history_res.status_code == 200
    assert len(history_res.json()) == 2


def test_notes_activity_integrity_and_author_rbac(client: TestClient, db_session):
    """
    Audit Recruiter Notes & Activity Integrity:
    - Notes are tenant-isolated.
    - Only note author or OWNER/ADMIN can edit a note.
    - Note updates are audit-logged (APPLICATION_NOTE_UPDATED).
    - Other recruiters cannot modify a colleague's note.
    - VIEWER cannot add or modify notes.
    """
    from app.models.entities import AuditLog

    token_owner, owner_id, agency_id_str = create_agency_and_user(
        client, "Notes Agency", "owner_notes@agency.com"
    )

    # Create Recruiter 1
    inv1 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "rec1@agency.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv1.json()["token"], "full_name": "Recruiter One", "password": "SecurePassword123!"},
    )
    rec1_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rec1@agency.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    # Create Recruiter 2
    inv2 = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "rec2@agency.com", "role": "RECRUITER"},
    )
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={"token": inv2.json()["token"], "full_name": "Recruiter Two", "password": "SecurePassword123!"},
    )
    rec2_token = client.post(
        "/api/v1/auth/login",
        json={"email": "rec2@agency.com", "password": "SecurePassword123!"},
    ).json()["tokens"]["access_token"]

    job = create_job(client, token_owner, "Staff Product Manager")
    cand = create_candidate(client, token_owner, "PM Candidate", "pm@candidate.com")

    # Create application
    app_res = client.post(
        f"/api/v1/jobs/{job['id']}/applications",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"candidate_id": cand["id"], "status": "APPLIED"},
    )
    app_id = app_res.json()["id"]

    # 1. Recruiter 1 adds a note -> 201
    note_res = client.post(
        f"/api/v1/applications/{app_id}/notes",
        headers={"Authorization": f"Bearer {rec1_token}"},
        json={"content": "Strong culture fit based on introductory call."},
    )
    assert note_res.status_code == 201
    note_id = note_res.json()["id"]
    assert note_res.json()["author_name"] == "Recruiter One"

    # 2. Recruiter 2 attempts to edit Recruiter 1's note -> 403 Forbidden
    rec2_edit = client.patch(
        f"/api/v1/applications/{app_id}/notes/{note_id}",
        headers={"Authorization": f"Bearer {rec2_token}"},
        json={"content": "Tampered note by Recruiter Two"},
    )
    assert rec2_edit.status_code == 403
    assert "do not have permission" in rec2_edit.json()["detail"]

    # 3. Recruiter 1 edits their own note -> 200 OK
    rec1_edit = client.patch(
        f"/api/v1/applications/{app_id}/notes/{note_id}",
        headers={"Authorization": f"Bearer {rec1_token}"},
        json={"content": "Strong culture fit and confirmed availability."},
    )
    assert rec1_edit.status_code == 200
    assert rec1_edit.json()["content"] == "Strong culture fit and confirmed availability."

    # 4. Owner edits Recruiter 1's note -> 200 OK (administrative privilege)
    owner_edit = client.patch(
        f"/api/v1/applications/{app_id}/notes/{note_id}",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"content": "Strong culture fit (verified by Partner)."},
    )
    assert owner_edit.status_code == 200
    assert owner_edit.json()["content"] == "Strong culture fit (verified by Partner)."

    # 5. Verify AuditLog entries for note actions
    logs = (
        db_session.query(AuditLog)
        .filter(
            AuditLog.agency_id == uuid.UUID(agency_id_str),
            AuditLog.resource_id == app_id,
        )
        .all()
    )
    actions = [l.action for l in logs]
    assert "APPLICATION_NOTE_ADDED" in actions
    assert "APPLICATION_NOTE_UPDATED" in actions

