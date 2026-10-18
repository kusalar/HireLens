import uuid
import json
import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.enums import (
    UserRole,
    JobStatus,
    PipelineStageType,
    ConfidenceLevel,
    PredictionAlgorithm,
    RecruitmentRiskType,
    RiskSeverity,
    RiskStatus,
    RecruiterUtilizationStatus,
)
from app.models.predictive import (
    PredictionModelVersion,
    RecruitmentForecast,
    RecruitmentRisk,
    CapacitySnapshot,
)
from app.models.job import Job
from app.models.candidate import Candidate
from app.models.application import Application
from app.services.predictive_engine import PredictiveEngine
from app.services.predictive_service import PredictiveService


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
# 1. Predictive Engine Mathematical & Statistical Tests
# =============================================================================
def test_predictive_engine_cold_start_fallback():
    """
    Validates that N < 10 sample size triggers baseline empirical Bayesian priors,
    sets is_baseline_fallback=True, and outputs confidence intervals honestly.
    """
    sparse_data = [{"duration_days": 28.0, "department": "Engineering"}]
    res = PredictiveEngine.calculate_time_to_hire_forecast(sparse_data, department="Engineering")

    assert res["is_baseline_fallback"] is True
    assert res["confidence_level"] in [ConfidenceLevel.PRELIMINARY, ConfidenceLevel.LOW]
    assert res["sample_size"] == 1
    assert res["algorithm"] == PredictionAlgorithm.BASELINE_EMPIRICAL
    assert res["confidence_lower"] < res["predicted_days"] < res["confidence_upper"]
    assert "preliminary estimate" in res["explanation"].lower()


def test_predictive_engine_intermediate_and_mature_data():
    """
    Validates that 10 <= N < 50 uses exponential smoothing / empirical averages,
    and N >= 50 evaluates with scikit-learn models.
    """
    # 25 samples
    intermediate_data = [
        {"duration_days": 25.0 + (i % 8), "department": "Sales"}
        for i in range(25)
    ]
    res_inter = PredictiveEngine.calculate_time_to_hire_forecast(intermediate_data, department="Sales")
    assert res_inter["is_baseline_fallback"] is False
    assert res_inter["confidence_level"] in [ConfidenceLevel.MEDIUM, ConfidenceLevel.HIGH]
    assert res_inter["sample_size"] == 25
    assert res_inter["algorithm"] == PredictionAlgorithm.EXPONENTIAL_SMOOTHING

    # 55 samples
    mature_data = [
        {
            "duration_days": 30.0 + (i % 12),
            "department": "Engineering",
            "requirements_count": 4,
            "experience_months": 48,
            "candidate_volume": 15,
        }
        for i in range(55)
    ]
    res_mature = PredictiveEngine.calculate_time_to_hire_forecast(mature_data, department="Engineering")
    assert res_mature["sample_size"] == 55
    assert res_mature["confidence_lower"] <= res_mature["predicted_days"] <= res_mature["confidence_upper"]


def test_hiring_demand_linear_forecasting():
    """
    Tests trend estimation and 30, 60, and 90-day demand aggregation.
    """
    monthly_apps = [10, 15, 20, 25, 30]
    monthly_jobs = [2, 3, 3, 4, 5]

    demand = PredictiveEngine.forecast_hiring_demand(monthly_apps, monthly_jobs)
    assert demand["demand_30d"] >= 4
    assert demand["demand_60d"] >= demand["demand_30d"]
    assert demand["demand_90d"] >= demand["demand_60d"]
    assert demand["expected_application_volume_30d"] >= 25
    assert demand["trend_direction"] == "INCREASING"


def test_recruiter_workload_calculation():
    """
    Tests deterministic calculation of operational workload index.
    """
    w_idx = PredictiveEngine.calculate_recruiter_workload(
        active_apps=12, upcoming_interviews=4, open_jobs=2
    )
    # 12*1.0 + 4*2.5 + 2*5.0 = 12 + 10 + 10 = 32.0
    assert w_idx == 32.0


# =============================================================================
# 2. Service & API Endpoint Integration Tests
# =============================================================================
def test_predictive_refresh_and_overview_api(client: TestClient, db_session: Session):
    """
    Tests POST /api/v1/predictive-analytics/refresh and GET /overview.
    """
    token, _, agency_id = create_agency_and_user(
        client, "Predictive Agency Alpha", "pred_admin@alpha.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Create an active job to test forecast generation
    job_res = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "title": "Principal ML Architect",
            "department": "Engineering",
            "location": "Bengaluru",
            "work_mode": "HYBRID",
            "employment_type": "FULL_TIME",
        },
    )
    assert job_res.status_code == 201

    # Trigger Refresh
    ref_res = client.post("/api/v1/predictive-analytics/refresh", headers=headers)
    assert ref_res.status_code == 200, ref_res.text
    ref_data = ref_res.json()
    assert ref_data["status"] == "SUCCESS"
    assert ref_data["forecasts_generated"] >= 5

    # Fetch Overview
    ov_res = client.get("/api/v1/predictive-analytics/overview", headers=headers)
    assert ov_res.status_code == 200, ov_res.text
    ov_data = ov_res.json()

    assert ov_data["active_jobs_count"] >= 1
    assert ov_data["average_predicted_time_to_hire_days"] > 0
    assert ov_data["demand_next_30d_hires"] >= 1
    assert "model_governance" in ov_data
    assert ov_data["timezone"] == "Asia/Kolkata"


def test_time_to_hire_and_demand_endpoints(client: TestClient):
    """
    Tests GET /time-to-hire and GET /demand endpoints.
    """
    token, _, _ = create_agency_and_user(
        client, "Predictive Beta", "admin@predbeta.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Refresh first
    client.post("/api/v1/predictive-analytics/refresh", headers=headers)

    # Test Time-to-Hire
    tth_res = client.get("/api/v1/predictive-analytics/time-to-hire", headers=headers)
    assert tth_res.status_code == 200, tth_res.text
    tth_data = tth_res.json()
    assert tth_data["overall_agency_predicted_days"] > 0
    assert "lower_days" in tth_data["confidence_interval"]
    assert "upper_days" in tth_data["confidence_interval"]
    assert len(tth_data["by_department"]) > 0

    # Test Demand
    dem_res = client.get("/api/v1/predictive-analytics/demand", headers=headers)
    assert dem_res.status_code == 200, dem_res.text
    dem_data = dem_res.json()
    assert dem_data["demand_30d"] > 0
    assert dem_data["demand_60d"] >= dem_data["demand_30d"]
    assert len(dem_data["department_breakdown"]) > 0
    assert len(dem_data["historical_vs_predicted_data"]) >= 4


def test_bottlenecks_and_capacity_endpoints(client: TestClient):
    """
    Tests GET /bottlenecks and GET /capacity endpoints.
    """
    token, _, _ = create_agency_and_user(
        client, "Predictive Gamma", "admin@predgamma.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Test Bottlenecks
    btn_res = client.get("/api/v1/predictive-analytics/bottlenecks", headers=headers)
    assert btn_res.status_code == 200, btn_res.text
    btn_data = btn_res.json()
    assert len(btn_data["stagnant_stages"]) >= 4
    assert len(btn_data["recommendations"]) >= 1

    # Test Capacity
    cap_res = client.get("/api/v1/predictive-analytics/capacity", headers=headers)
    assert cap_res.status_code == 200, cap_res.text
    cap_data = cap_res.json()
    assert len(cap_data["recruiters"]) >= 1
    assert cap_data["agency_average_workload"] >= 0.0
    assert len(cap_data["redistribution_recommendations"]) >= 1


def test_recruitment_risk_detection_and_lifecycle(client: TestClient, db_session: Session):
    """
    Tests risk generation, filtering, and acknowledgment/resolution via PATCH /risks/{id}.
    """
    token, _, agency_id = create_agency_and_user(
        client, "Risk Agency Delta", "admin@riskdelta.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    # Create an active job with 0 candidates to trigger pipeline deficit risk
    job_res = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "title": "Lead DevOps Architect",
            "department": "Infrastructure",
            "location": "Mumbai",
            "work_mode": "ONSITE",
            "employment_type": "FULL_TIME",
        },
    )
    assert job_res.status_code == 201

    # Refresh to trigger risk scanner
    client.post("/api/v1/predictive-analytics/refresh", headers=headers)

    # Get risks
    risks_res = client.get("/api/v1/predictive-analytics/risks", headers=headers)
    assert risks_res.status_code == 200, risks_res.text
    risks = risks_res.json()
    assert len(risks) >= 1

    deficit_risk = next((r for r in risks if r["risk_type"] == "PIPELINE_DEFICIT"), None)
    assert deficit_risk is not None
    assert deficit_risk["status"] == "OPEN"
    assert deficit_risk["severity"] in ["HIGH", "CRITICAL"]

    # Acknowledge the risk
    patch_res = client.patch(
        f"/api/v1/predictive-analytics/risks/{deficit_risk['id']}",
        headers=headers,
        json={
            "status": "ACKNOWLEDGED",
            "resolution_notes": "Sourcing specialist assigned to outreach campaign.",
        },
    )
    assert patch_res.status_code == 200, patch_res.text
    patched_data = patch_res.json()
    assert patched_data["status"] == "ACKNOWLEDGED"
    assert patched_data["resolution_notes"] == "Sourcing specialist assigned to outreach campaign."

    # Mitigate the risk
    mit_res = client.patch(
        f"/api/v1/predictive-analytics/risks/{deficit_risk['id']}",
        headers=headers,
        json={"status": "MITIGATED"},
    )
    assert mit_res.status_code == 200
    assert mit_res.json()["status"] == "MITIGATED"
    assert mit_res.json()["resolved_at"] is not None


def test_predictive_rbac_and_tenant_isolation(client: TestClient):
    """
    Verifies that only OWNER/ADMIN can refresh models and that tenant isolation
    strictly partitions risks and forecasts between agencies.
    """
    token_a, _, agency_a = create_agency_and_user(
        client, "Agency RBAC A", "owner_a@rbactest.com"
    )
    token_b, _, agency_b = create_agency_and_user(
        client, "Agency RBAC B", "owner_b@rbactest.com"
    )

    recruiter_token, _ = create_recruiter_user(
        client, token_a, "recruiter_a@rbactest.com", "Recruiter A"
    )

    # 1. Recruiter cannot call /refresh (403 Forbidden)
    ref_denied = client.post(
        "/api/v1/predictive-analytics/refresh",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert ref_denied.status_code == 403

    # 2. Owner A refreshes Agency A
    client.post(
        "/api/v1/predictive-analytics/refresh",
        headers={"Authorization": f"Bearer {token_a}"},
    )

    # 3. Agency B should have 0 forecasts from Agency A
    res_b = client.get(
        "/api/v1/predictive-analytics/models",
        headers={"Authorization": f"Bearer {token_b}"},
    )
    assert res_b.status_code == 200
    assert len(res_b.json()) == 0


def test_model_registry_governance(client: TestClient):
    """
    Validates that /models returns version tags, algorithms, and sample sizes.
    """
    token, _, _ = create_agency_and_user(
        client, "Gov Agency", "gov_admin@test.com"
    )
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/v1/predictive-analytics/refresh", headers=headers)

    models_res = client.get("/api/v1/predictive-analytics/models", headers=headers)
    assert models_res.status_code == 200, models_res.text
    models = models_res.json()
    assert len(models) >= 1
    m = models[0]
    assert "version_tag" in m
    assert "algorithm" in m
    assert "training_sample_size" in m
    assert m["is_active"] is True
