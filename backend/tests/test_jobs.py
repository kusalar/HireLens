import pytest
from fastapi.testclient import TestClient

def get_auth_token(client: TestClient, email: str = "recruiter@jobsagency.com") -> str:
    res = client.post("/api/v1/auth/register", json={
        "agency_name": "Job Agency Global",
        "full_name": "Job Recruiter",
        "email": email,
        "password": "Password123!",
    })
    return res.json()["tokens"]["access_token"]

def test_create_and_retrieve_job(client: TestClient):
    token = get_auth_token(client, "owner@techjobs.in")
    headers = {"Authorization": f"Bearer {token}"}

    job_payload = {
        "title": "Senior Backend Architect",
        "department": "Engineering",
        "description": "Lead the design of high-throughput distributed microservices.",
        "responsibilities": "Architect APIs, optimize database queries, mentor team.",
        "location": "Bengaluru",
        "work_mode": "HYBRID",
        "employment_type": "FULL_TIME",
        "minimum_experience": 5,
        "maximum_experience": 10,
        "requirements": [
            {
                "requirement_text": "Strong mastery of Python and FastAPI",
                "normalized_skill": "Python",
                "requirement_type": "SKILL",
                "importance_weight": 2.0,
                "is_mandatory": True,
            },
            {
                "requirement_text": "PostgreSQL database optimization experience",
                "normalized_skill": "PostgreSQL",
                "requirement_type": "EXPERIENCE",
                "importance_weight": 1.5,
                "is_mandatory": True,
            }
        ]
    }

    create_res = client.post("/api/v1/jobs", json=job_payload, headers=headers)
    assert create_res.status_code == 201
    job = create_res.json()
    assert job["title"] == "Senior Backend Architect"
    assert job["work_mode"] == "HYBRID"
    assert len(job["requirements"]) == 2
    job_id = job["id"]

    # Retrieve job details
    get_res = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["title"] == "Senior Backend Architect"
    assert len(get_res.json()["requirements"]) == 2

def test_list_and_filter_jobs(client: TestClient):
    token = get_auth_token(client, "admin@filters.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Create two jobs
    client.post("/api/v1/jobs", json={
        "title": "React Frontend Lead",
        "department": "Product",
        "work_mode": "REMOTE",
        "minimum_experience": 4,
    }, headers=headers)

    client.post("/api/v1/jobs", json={
        "title": "DevOps Engineer",
        "department": "Infrastructure",
        "work_mode": "ONSITE",
        "minimum_experience": 3,
    }, headers=headers)

    # List all
    all_res = client.get("/api/v1/jobs", headers=headers)
    assert all_res.status_code == 200
    assert len(all_res.json()) >= 2

    # Filter by work_mode
    remote_res = client.get("/api/v1/jobs?work_mode=REMOTE", headers=headers)
    assert remote_res.status_code == 200
    assert all(j["work_mode"] == "REMOTE" for j in remote_res.json())

    # Filter by search
    search_res = client.get("/api/v1/jobs?search=DevOps", headers=headers)
    assert search_res.status_code == 200
    assert any("DevOps" in j["title"] for j in search_res.json())

def test_update_and_archive_job(client: TestClient):
    token = get_auth_token(client, "lead@updates.in")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/jobs", json={
        "title": "Junior QA Specialist",
        "minimum_experience": 1,
        "maximum_experience": 3,
    }, headers=headers)
    job_id = create_res.json()["id"]

    # Update job
    upd_res = client.patch(f"/api/v1/jobs/{job_id}", json={
        "title": "Senior QA Automation Engineer",
        "minimum_experience": 3,
        "maximum_experience": 6,
    }, headers=headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["title"] == "Senior QA Automation Engineer"

    # Archive job
    arch_res = client.post(f"/api/v1/jobs/{job_id}/archive", headers=headers)
    assert arch_res.status_code == 200
    assert arch_res.json()["status"] == "ARCHIVED"

def test_job_requirements_crud(client: TestClient):
    token = get_auth_token(client, "rec@reqs.in")
    headers = {"Authorization": f"Bearer {token}"}

    job_res = client.post("/api/v1/jobs", json={
        "title": "Machine Learning Engineer",
        "minimum_experience": 2,
    }, headers=headers)
    job_id = job_res.json()["id"]

    # Add requirement
    req_res = client.post(f"/api/v1/jobs/{job_id}/requirements", json={
        "requirement_text": "Experience with PyTorch or JAX",
        "normalized_skill": "PyTorch",
        "importance_weight": 2.5,
        "is_mandatory": True,
    }, headers=headers)
    assert req_res.status_code == 201
    req_id = req_res.json()["id"]
    assert req_res.json()["importance_weight"] == 2.5

    # Edit requirement
    edit_res = client.patch(f"/api/v1/jobs/{job_id}/requirements/{req_id}", json={
        "importance_weight": 3.0,
        "is_mandatory": False,
    }, headers=headers)
    assert edit_res.status_code == 200
    assert edit_res.json()["importance_weight"] == 3.0
    assert edit_res.json()["is_mandatory"] is False

    # Delete requirement
    del_res = client.delete(f"/api/v1/jobs/{job_id}/requirements/{req_id}", headers=headers)
    assert del_res.status_code == 200

    # Verify requirement is deleted from job
    get_job = client.get(f"/api/v1/jobs/{job_id}", headers=headers)
    assert len(get_job.json()["requirements"]) == 0

def test_job_validation_errors(client: TestClient):
    token = get_auth_token(client, "qa@validation.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Minimum experience > maximum experience
    bad_exp_res = client.post("/api/v1/jobs", json={
        "title": "Invalid Experience Job",
        "minimum_experience": 5,
        "maximum_experience": 2,
    }, headers=headers)
    assert bad_exp_res.status_code == 422

    # Negative experience
    neg_exp_res = client.post("/api/v1/jobs", json={
        "title": "Negative Experience Job",
        "minimum_experience": -1,
    }, headers=headers)
    assert neg_exp_res.status_code == 422

    # Create job for requirement weight test
    job_res = client.post("/api/v1/jobs", json={"title": "Valid Job Title"}, headers=headers)
    job_id = job_res.json()["id"]

    # Invalid requirement weight (<= 0)
    bad_weight_res = client.post(f"/api/v1/jobs/{job_id}/requirements", json={
        "requirement_text": "Weight Test",
        "importance_weight": 0.0,
    }, headers=headers)
    assert bad_weight_res.status_code == 422
