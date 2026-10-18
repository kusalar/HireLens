import uuid
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pytest
from fastapi.testclient import TestClient

from app.models.enums import (
    UserRole,
    InterviewMode,
    InterviewStatus,
    InterviewRoundType,
    PipelineStageType,
    ExpenseCategory,
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


def create_job(client: TestClient, token: str, title: str = "Staff Backend Engineer") -> dict:
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
    client: TestClient,
    token: str,
    name: str = "Rahul Verma",
    email: str = "rahul@example.com",
    source: str = "LINKEDIN",
) -> dict:
    res = client.post(
        "/api/v1/candidates",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "full_name": name,
            "email": email,
            "current_title": "Senior Systems Engineer",
            "total_experience_months": 60,
            "current_location": "Bengaluru, India",
            "profile_status": "ACTIVE",
            "source": source,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()


def create_application(
    client: TestClient,
    token: str,
    job_id: str,
    candidate_id: str,
    source: str = "LINKEDIN",
    assigned_recruiter_id: str = None,
) -> dict:
    payload = {
        "candidate_id": candidate_id,
        "status": "APPLIED",
        "source": source,
    }
    if assigned_recruiter_id:
        payload["assigned_recruiter_id"] = assigned_recruiter_id

    res = client.post(
        f"/api/v1/jobs/{job_id}/applications",
        headers={"Authorization": f"Bearer {token}"},
        json=payload,
    )
    assert res.status_code == 201, res.text
    return res.json()


def transition_stage(
    client: TestClient,
    token: str,
    app_id: str,
    new_stage: str,
    reason: str = "Stage progression",
) -> dict:
    res = client.post(
        f"/api/v1/applications/{app_id}/transition",
        headers={"Authorization": f"Bearer {token}"},
        json={"new_stage": new_stage, "reason": reason},
    )
    assert res.status_code == 200, res.text
    return res.json()


def create_interview(
    client: TestClient,
    token: str,
    app_id: str,
    title: str = "Technical Round 1",
    status_val: str = "SCHEDULED",
) -> dict:
    now = datetime.now(timezone.utc)
    start = now + timedelta(days=1)
    end = start + timedelta(hours=1)
    res = client.post(
        f"/api/v1/applications/{app_id}/interviews",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "round_name": "Technical Round 1",
            "round_type": "TECHNICAL",
            "title": title,
            "interview_mode": "ONLINE",
            "scheduled_start": start.isoformat(),
            "scheduled_end": end.isoformat(),
            "timezone": "Asia/Kolkata",
            "meeting_url": "https://meet.google.com/test-123",
            "participants": [
                {
                    "participant_name": "Interviewer One",
                    "participant_email": "interviewer@example.com",
                    "participant_role": "INTERVIEWER",
                }
            ],
        },
    )
    assert res.status_code == 201, res.text
    interview = res.json()

    if status_val == "COMPLETED":
        # Transition to completed
        comp_res = client.post(
            f"/api/v1/interviews/{interview['id']}/complete",
            headers={"Authorization": f"Bearer {token}"},
            json={"notes": "Candidate performed well"},
        )
        assert comp_res.status_code == 200, comp_res.text
        return comp_res.json()
    elif status_val == "CANCELLED":
        canc_res = client.post(
            f"/api/v1/interviews/{interview['id']}/cancel",
            headers={"Authorization": f"Bearer {token}"},
            json={"reason": "Candidate withdrew"},
        )
        assert canc_res.status_code == 200, canc_res.text
        return canc_res.json()

    return interview


# ======================================================================
# 1. Empty State & Clean Zero Handling
# ======================================================================

def test_empty_analytics_dashboard(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Fresh Agency", "owner@freshagency.com")

    # Overview
    ov = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {token}"})
    assert ov.status_code == 200, ov.text
    data = ov.json()
    assert data["total_active_jobs"] == 0
    assert data["total_candidates"] == 0
    assert data["total_applications"] == 0
    assert data["successful_hires"] == 0
    assert data["reporting_period"]["timezone"] == "Asia/Kolkata"

    # Funnel
    fn = client.get("/api/v1/analytics/funnel", headers={"Authorization": f"Bearer {token}"})
    assert fn.status_code == 200, fn.text
    assert fn.json()["overall_application_to_hire_rate"] == 0.0

    # Hiring Performance
    hp = client.get("/api/v1/analytics/hiring-performance", headers={"Authorization": f"Bearer {token}"})
    assert hp.status_code == 200, hp.text
    hp_data = hp.json()
    assert hp_data["time_to_hire"]["average_days"] is None
    assert hp_data["time_to_hire"]["median_days"] is None
    assert hp_data["time_to_hire"]["hired_sample_size"] == 0
    assert hp_data["interview_conversion"]["interviews_per_application"] == 0.0

    # Costs
    cs = client.get("/api/v1/analytics/costs", headers={"Authorization": f"Bearer {token}"})
    assert cs.status_code == 200, cs.text
    assert cs.json()["has_cost_data"] is False
    assert "Insufficient cost data" in cs.json()["status_message"]


# ======================================================================
# 2. Overview Metrics & Controlled Data Calculation
# ======================================================================

def test_overview_metrics_calculation(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Metrics Agency", "owner@metrics.com")
    job = create_job(client, token, "Backend Lead")
    cand1 = create_candidate(client, token, "Aarav Kumar", "aarav@example.com", "LINKEDIN")
    cand2 = create_candidate(client, token, "Sneha Patel", "sneha@example.com", "REFERRAL")

    app1 = create_application(client, token, job["id"], cand1["id"], "LINKEDIN", user_id)
    app2 = create_application(client, token, job["id"], cand2["id"], "REFERRAL", user_id)

    # Transition app1 to SELECTED (hired)
    transition_stage(client, token, app1["id"], "UNDER_REVIEW")
    transition_stage(client, token, app1["id"], "SHORTLISTED")
    transition_stage(client, token, app1["id"], "INTERVIEW")
    transition_stage(client, token, app1["id"], "SELECTED")

    # Conduct interview for app2
    create_interview(client, token, app2["id"], "Initial Screening", status_val="COMPLETED")

    res = client.get("/api/v1/analytics/overview?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_active_jobs"] == 1
    assert data["total_candidates"] == 2
    assert data["total_applications"] == 2
    assert data["applications_in_period"] == 2
    assert data["successful_hires"] == 1
    assert data["interviews_completed"] == 1
    assert data["active_applications"] == 1  # app2 is still active, app1 is SELECTED (terminal)


# ======================================================================
# 3. Recruitment Funnel & Conversion Rates
# ======================================================================

def test_recruitment_funnel_and_conversions(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Funnel Agency", "owner@funnel.com")
    job = create_job(client, token, "Data Architect")

    c1 = create_candidate(client, token, "Candidate 1", "c1@example.com")
    c2 = create_candidate(client, token, "Candidate 2", "c2@example.com")
    c3 = create_candidate(client, token, "Candidate 3", "c3@example.com")

    a1 = create_application(client, token, job["id"], c1["id"])
    a2 = create_application(client, token, job["id"], c2["id"])
    a3 = create_application(client, token, job["id"], c3["id"])

    # a1 goes: APPLIED -> UNDER_REVIEW -> SHORTLISTED -> INTERVIEW -> SELECTED
    transition_stage(client, token, a1["id"], "UNDER_REVIEW")
    transition_stage(client, token, a1["id"], "SHORTLISTED")
    transition_stage(client, token, a1["id"], "INTERVIEW")
    transition_stage(client, token, a1["id"], "SELECTED")

    # a2 goes: APPLIED -> UNDER_REVIEW -> REJECTED
    transition_stage(client, token, a2["id"], "UNDER_REVIEW")
    transition_stage(client, token, a2["id"], "REJECTED")

    # a3 stays in APPLIED

    res = client.get("/api/v1/analytics/funnel?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    stages_by_name = {s["stage"]: s for s in data["stages"]}
    assert stages_by_name["APPLIED"]["current_count"] == 1
    assert stages_by_name["SELECTED"]["current_count"] == 1
    assert stages_by_name["REJECTED"]["current_count"] == 1

    # Check drop-offs: a2 dropped off at UNDER_REVIEW to REJECTED
    assert stages_by_name["UNDER_REVIEW"]["drop_off_count"] == 1

    # Overall conversion: 1 hire out of 3 applications = 33.33%
    assert data["overall_application_to_hire_rate"] == 33.33


# ======================================================================
# 4. Time-to-Hire Calculations
# ======================================================================

def test_time_to_hire_calculation(client: TestClient):
    token, _, _ = create_agency_and_user(client, "TTH Agency", "owner@tth.com")
    job = create_job(client, token, "Security Engineer")

    c1 = create_candidate(client, token, "Dev 1", "dev1@tth.com")
    c2 = create_candidate(client, token, "Dev 2", "dev2@tth.com")

    a1 = create_application(client, token, job["id"], c1["id"])
    a2 = create_application(client, token, job["id"], c2["id"])

    # Complete a1 and a2 hiring journeys
    transition_stage(client, token, a1["id"], "SELECTED")
    transition_stage(client, token, a2["id"], "SELECTED")

    res = client.get("/api/v1/analytics/hiring-performance?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    tth = res.json()["time_to_hire"]

    assert tth["hired_sample_size"] == 2
    assert tth["average_days"] is not None
    assert tth["median_days"] is not None
    assert tth["average_days"] >= 0.0


# ======================================================================
# 5. Interview Conversion & Exclusion of Cancelled Interviews
# ======================================================================

def test_interview_conversion_metrics(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Interview Metrics Agency", "owner@intmetrics.com")
    job = create_job(client, token, "DevOps Specialist")
    cand = create_candidate(client, token, "Aditya Roy", "aditya@example.com")
    app = create_application(client, token, job["id"], cand["id"])

    # Create 1 completed interview and 1 cancelled interview
    create_interview(client, token, app["id"], "Round 1", status_val="COMPLETED")
    create_interview(client, token, app["id"], "Round 2", status_val="CANCELLED")

    res = client.get("/api/v1/analytics/hiring-performance?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    conv = res.json()["interview_conversion"]

    assert conv["total_interviews_conducted"] == 1
    assert conv["cancelled_interviews_excluded"] == 1
    assert conv["applications_with_interviews"] == 1


# ======================================================================
# 6. Job Performance Analytics & Zero Applicant Jobs
# ======================================================================

def test_job_performance_analytics(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Job Analytics Agency", "owner@jobanalytics.com")
    job1 = create_job(client, token, "Full Stack Engineer")
    job2 = create_job(client, token, "Unpopular Role Without Applicants")

    cand = create_candidate(client, token, "Karan Singh", "karan@example.com")
    create_application(client, token, job1["id"], cand["id"])

    res = client.get("/api/v1/analytics/jobs?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_jobs_evaluated"] == 2
    assert data["jobs_with_zero_applications"] == 1

    job_entries = {j["job_id"]: j for j in data["jobs"]}
    assert job_entries[job1["id"]]["applications_count"] == 1
    assert job_entries[job2["id"]]["applications_count"] == 0


# ======================================================================
# 7. Recruiter Workload & Attribution Analytics
# ======================================================================

def test_recruiter_performance_attribution(client: TestClient):
    token, user_id, _ = create_agency_and_user(client, "Recruiter Agency", "owner@recruiteragency.com")
    job = create_job(client, token, "QA Lead")

    cand1 = create_candidate(client, token, "Tester 1", "test1@example.com")
    cand2 = create_candidate(client, token, "Tester 2", "test2@example.com")

    # Assign both applications to user_id
    a1 = create_application(client, token, job["id"], cand1["id"], assigned_recruiter_id=user_id)
    a2 = create_application(client, token, job["id"], cand2["id"], assigned_recruiter_id=user_id)

    # Hire a1
    transition_stage(client, token, a1["id"], "SELECTED")

    res = client.get("/api/v1/analytics/recruiters?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    assert len(data["recruiters"]) >= 1
    rec = next(r for r in data["recruiters"] if r["recruiter_id"] == user_id)
    assert rec["applications_handled"] == 2
    assert rec["attributable_hires"] == 1
    assert rec["active_workload"] == 1  # a2 is active, a1 is hired


# ======================================================================
# 8. Candidate Source Effectiveness & Honest Unattributed Handling
# ======================================================================

def test_source_performance_analytics(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Source Agency", "owner@sourceagency.com")
    job = create_job(client, token, "Data Engineer")

    # Sourced candidate
    cand_li = create_candidate(client, token, "LinkedIn Cand", "li@example.com", source="LINKEDIN")
    app_li = create_application(client, token, job["id"], cand_li["id"], source="LINKEDIN")
    transition_stage(client, token, app_li["id"], "SELECTED")

    # Unattributed candidate
    cand_un = create_candidate(client, token, "Mystery Cand", "mystery@example.com", source=None)
    app_un = create_application(client, token, job["id"], cand_un["id"], source=None)

    res = client.get("/api/v1/analytics/sources?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    src_map = {s["source"]: s for s in data["sources"]}
    assert "LINKEDIN" in src_map
    assert src_map["LINKEDIN"]["hires_count"] == 1
    assert src_map["LINKEDIN"]["conversion_rate"] == 100.0

    # Ensure unattributed is reported honestly without hallucination
    assert "Unattributed" in src_map or data["unattributed_candidates_count"] > 0


# ======================================================================
# 9. Expense CRUD, Validation & Audit Trail
# ======================================================================

def test_expense_crud_and_validation(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Expense Agency", "owner@expenseagency.com")
    job = create_job(client, token, "Mobile Architect")

    # 1. Invalid amount (<= 0)
    inv = client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Bad Expense",
            "amount": -50.0,
            "currency": "INR",
            "category": "JOB_ADVERTISING",
            "expense_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert inv.status_code == 422

    # 2. Invalid currency code
    inv_curr = client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Bad Currency",
            "amount": 100.0,
            "currency": "TOOLONG",
            "category": "JOB_ADVERTISING",
            "expense_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert inv_curr.status_code == 422

    # 3. Create valid expense
    exp_res = client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "LinkedIn Job Slot",
            "amount": 25000.0,
            "currency": "inr",  # test normalization to INR
            "category": "JOB_ADVERTISING",
            "expense_date": datetime.now(timezone.utc).isoformat(),
            "job_id": job["id"],
            "description": "Sponsored post for mobile architect",
        },
    )
    assert exp_res.status_code == 201, exp_res.text
    exp_id = exp_res.json()["id"]
    assert exp_res.json()["currency"] == "INR"
    assert exp_res.json()["amount"] == 25000.0
    assert exp_res.json()["job_title"] == "Mobile Architect"

    # 4. List expenses
    lst = client.get("/api/v1/analytics/expenses", headers={"Authorization": f"Bearer {token}"})
    assert lst.status_code == 200
    assert lst.json()["total"] == 1

    # 5. Update expense
    upd = client.patch(
        f"/api/v1/analytics/expenses/{exp_id}",
        headers={"Authorization": f"Bearer {token}"},
        json={"amount": 28000.0, "title": "LinkedIn Premium Job Slot"},
    )
    assert upd.status_code == 200
    assert upd.json()["amount"] == 28000.0
    assert upd.json()["title"] == "LinkedIn Premium Job Slot"

    # 6. Delete expense
    del_res = client.delete(f"/api/v1/analytics/expenses/{exp_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 204

    # 7. Confirm deleted
    chk = client.get(f"/api/v1/analytics/expenses/{exp_id}", headers={"Authorization": f"Bearer {token}"})
    assert chk.status_code == 404


# ======================================================================
# 10. Cost-Per-Hire & Multi-Currency Isolation
# ======================================================================

def test_cost_per_hire_and_multi_currency(client: TestClient):
    token, _, _ = create_agency_and_user(client, "CostPerHire Agency", "owner@cphagency.com")
    job = create_job(client, token, "Cloud Architect")

    # 2 hires
    c1 = create_candidate(client, token, "Hired 1", "h1@cph.com")
    c2 = create_candidate(client, token, "Hired 2", "h2@cph.com")
    a1 = create_application(client, token, job["id"], c1["id"])
    a2 = create_application(client, token, job["id"], c2["id"])
    transition_stage(client, token, a1["id"], "SELECTED")
    transition_stage(client, token, a2["id"], "SELECTED")

    # Add INR expense 40,000 and USD expense 600
    client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "Naukri Portal Subscription",
            "amount": 40000.0,
            "currency": "INR",
            "category": "RECRUITMENT_PLATFORMS",
            "expense_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token}"},
        json={
            "title": "HackerRank Assessment Suite",
            "amount": 600.0,
            "currency": "USD",
            "category": "ASSESSMENT_COSTS",
            "expense_date": datetime.now(timezone.utc).isoformat(),
        },
    )

    res = client.get("/api/v1/analytics/costs?period=LAST_30_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["has_cost_data"] is True
    assert data["total_attributable_hires"] == 2

    # Cost per hire must be calculated independently without blending currencies
    cph = data["cost_per_hire_by_currency"]
    assert cph["INR"] == 20000.0  # 40000 / 2 hires
    assert cph["USD"] == 300.0    # 600 / 2 hires
    assert "Sufficient cost data" in data["status_message"]


# ======================================================================
# 11. Reporting Period Presets & Timezone Boundaries
# ======================================================================

def test_reporting_period_presets(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Period Agency", "owner@periodagency.com")

    presets = [
        "TODAY",
        "LAST_7_DAYS",
        "LAST_30_DAYS",
        "LAST_90_DAYS",
        "THIS_MONTH",
        "PREVIOUS_MONTH",
        "THIS_QUARTER",
    ]

    for p in presets:
        res = client.get(f"/api/v1/analytics/overview?period={p}", headers={"Authorization": f"Bearer {token}"})
        assert res.status_code == 200, f"Preset {p} failed: {res.text}"
        period = res.json()["reporting_period"]
        assert period["preset"] == p
        assert period["timezone"] == "Asia/Kolkata"
        assert period["start_date_ist"] <= period["end_date_ist"]


# ======================================================================
# 12. Custom Date Range Validation
# ======================================================================

def test_custom_date_range_validation(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Custom Date Agency", "owner@customdate.com")

    # Missing dates for CUSTOM
    r1 = client.get("/api/v1/analytics/overview?period=CUSTOM", headers={"Authorization": f"Bearer {token}"})
    assert r1.status_code == 400
    assert "start_date and end_date" in r1.text

    # Invalid date format
    r2 = client.get(
        "/api/v1/analytics/overview?period=CUSTOM&start_date=10-2026-01&end_date=2026-10-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r2.status_code == 400
    assert "Invalid date format" in r2.text

    # start_date > end_date
    r3 = client.get(
        "/api/v1/analytics/overview?period=CUSTOM&start_date=2026-10-20&end_date=2026-10-10",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r3.status_code == 400
    assert "cannot be after" in r3.text

    # Valid custom range
    r4 = client.get(
        "/api/v1/analytics/overview?period=CUSTOM&start_date=2026-10-01&end_date=2026-10-15",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert r4.status_code == 200
    assert r4.json()["reporting_period"]["start_date_ist"] == "2026-10-01"
    assert r4.json()["reporting_period"]["end_date_ist"] == "2026-10-15"


# ======================================================================
# 13. Agency Isolation & Multi-Tenancy Protection
# ======================================================================

def test_agency_isolation_and_cross_tenant_analytics(client: TestClient):
    token_a, _, agency_a = create_agency_and_user(client, "Tenant Alpha", "owner@alpha.com")
    token_b, _, agency_b = create_agency_and_user(client, "Tenant Beta", "owner@beta.com")

    # Alpha creates a job, candidate, and expense
    job_a = create_job(client, token_a, "Alpha Secret Project")
    cand_a = create_candidate(client, token_a, "Alpha Candidate", "alpha@cand.com")
    app_a = create_application(client, token_a, job_a["id"], cand_a["id"])
    exp_a = client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token_a}"},
        json={
            "title": "Alpha Advertising",
            "amount": 50000.0,
            "currency": "INR",
            "category": "JOB_ADVERTISING",
            "expense_date": datetime.now(timezone.utc).isoformat(),
        },
    ).json()

    # Beta checks overview: must see 0 jobs, 0 candidates, 0 applications
    res_b = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {token_b}"})
    assert res_b.status_code == 200
    assert res_b.json()["total_active_jobs"] == 0
    assert res_b.json()["total_candidates"] == 0
    assert res_b.json()["total_applications"] == 0

    # Beta checks expenses: must see 0 expenses
    exp_list_b = client.get("/api/v1/analytics/expenses", headers={"Authorization": f"Bearer {token_b}"})
    assert exp_list_b.status_code == 200
    assert exp_list_b.json()["total"] == 0

    # Beta attempts IDOR read of Alpha's expense: 404
    idor_read = client.get(f"/api/v1/analytics/expenses/{exp_a['id']}", headers={"Authorization": f"Bearer {token_b}"})
    assert idor_read.status_code == 404

    # Beta filters analytics by Alpha's job: 404
    cross_filter = client.get(
        f"/api/v1/analytics/overview?job_id={job_a['id']}",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert cross_filter.status_code == 404


# ======================================================================
# 14. RBAC Enforcement for Expenses
# ======================================================================

def test_rbac_expense_permissions(client: TestClient):
    token_owner, _, agency_id = create_agency_and_user(client, "RBAC Agency", "owner@rbacagency.com")

    # Invite a RECRUITER
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {token_owner}"},
        json={"email": "recruiter@rbacagency.com", "role": "RECRUITER"},
    )
    assert invite_res.status_code == 201
    inv_token = invite_res.json()["token"]

    # Register recruiter
    reg_rec = client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": inv_token,
            "full_name": "Agency Recruiter",
            "password": "SecurePassword123!",
        },
    )
    assert reg_rec.status_code == 201

    # Login as recruiter
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "recruiter@rbacagency.com", "password": "SecurePassword123!"},
    )
    assert login_res.status_code == 200
    token_rec = login_res.json()["tokens"]["access_token"]

    # 1. Recruiter CAN view analytics
    rec_ov = client.get("/api/v1/analytics/overview", headers={"Authorization": f"Bearer {token_rec}"})
    assert rec_ov.status_code == 200

    # 2. Recruiter CAN list expenses (read-only)
    rec_exp_list = client.get("/api/v1/analytics/expenses", headers={"Authorization": f"Bearer {token_rec}"})
    assert rec_exp_list.status_code == 200

    # 3. Recruiter CANNOT create expenses (403 Forbidden)
    rec_create = client.post(
        "/api/v1/analytics/expenses",
        headers={"Authorization": f"Bearer {token_rec}"},
        json={
            "title": "Unauthorized Expense",
            "amount": 1000.0,
            "currency": "INR",
            "category": "OTHER",
            "expense_date": datetime.now(timezone.utc).isoformat(),
        },
    )
    assert rec_create.status_code == 403


# ======================================================================
# 15. AI-Assisted Insights & Fallback Behavior
# ======================================================================

def test_ai_insights_generation_and_fallback(client: TestClient):
    token, _, _ = create_agency_and_user(client, "AI Insights Agency", "owner@aiagency.com")
    job = create_job(client, token, "Machine Learning Lead")
    cand = create_candidate(client, token, "AI Engineer", "ai@example.com")
    create_application(client, token, job["id"], cand["id"])

    res = client.post(
        "/api/v1/analytics/insights",
        headers={"Authorization": f"Bearer {token}"},
        json={"focus_area": "funnel_dropoff"},
    )
    assert res.status_code == 200, res.text
    data = res.json()

    assert len(data["summary"]) > 0
    assert len(data["key_findings"]) >= 1
    assert len(data["bottlenecks"]) >= 1
    assert len(data["operational_recommendations"]) >= 1
    assert "provider_used" in data
    assert "grounding_disclaimer" in data


# ======================================================================
# 16. Trends Time-Series
# ======================================================================

def test_trends_time_series(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Trends Agency", "owner@trendsagency.com")
    job = create_job(client, token, "Site Reliability Engineer")
    cand = create_candidate(client, token, "SRE Cand", "sre@example.com")
    app = create_application(client, token, job["id"], cand["id"])
    create_interview(client, token, app["id"], "System Design", status_val="COMPLETED")

    res = client.get("/api/v1/analytics/trends?period=LAST_7_DAYS", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200, res.text
    points = res.json()["data_points"]

    assert len(points) == 7
    total_apps = sum(p["applications"] for p in points)
    assert total_apps == 1
