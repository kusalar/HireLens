import pytest
from fastapi.testclient import TestClient

def test_tenant_isolation_agency_profile_and_members(client: TestClient):
    # 1. Register Agency A
    reg_a = client.post("/api/v1/auth/register", json={
        "agency_name": "Agency Alpha",
        "full_name": "Alpha Owner",
        "email": "owner@agencyalpha.com",
        "password": "Password123!",
    })
    token_a = reg_a.json()["tokens"]["access_token"]
    agency_a_id = reg_a.json()["user"]["agency_id"]

    # 2. Register Agency B
    reg_b = client.post("/api/v1/auth/register", json={
        "agency_name": "Agency Beta",
        "full_name": "Beta Owner",
        "email": "owner@agencybeta.com",
        "password": "Password123!",
    })
    token_b = reg_b.json()["tokens"]["access_token"]
    agency_b_id = reg_b.json()["user"]["agency_id"]

    assert agency_a_id != agency_b_id

    # 3. Agency A queries /agency/profile
    prof_a = client.get("/api/v1/agency/profile", headers={"Authorization": f"Bearer {token_a}"})
    assert prof_a.status_code == 200
    assert prof_a.json()["id"] == agency_a_id
    assert prof_a.json()["name"] == "Agency Alpha"

    # 4. Agency B queries /agency/profile
    prof_b = client.get("/api/v1/agency/profile", headers={"Authorization": f"Bearer {token_b}"})
    assert prof_b.status_code == 200
    assert prof_b.json()["id"] == agency_b_id
    assert prof_b.json()["name"] == "Agency Beta"

    # 5. Check members list for Agency A
    members_a = client.get("/api/v1/agency/members", headers={"Authorization": f"Bearer {token_a}"})
    assert members_a.status_code == 200
    member_emails_a = [m["email"] for m in members_a.json()]
    assert "owner@agencyalpha.com" in member_emails_a
    assert "owner@agencybeta.com" not in member_emails_a

    # 6. Check members list for Agency B
    members_b = client.get("/api/v1/agency/members", headers={"Authorization": f"Bearer {token_b}"})
    assert members_b.status_code == 200
    member_emails_b = [m["email"] for m in members_b.json()]
    assert "owner@agencybeta.com" in member_emails_b
    assert "owner@agencyalpha.com" not in member_emails_b

def test_tenant_isolation_jobs_candidates_and_notes(client: TestClient):
    # Register Agency Alpha
    reg_a = client.post("/api/v1/auth/register", json={
        "agency_name": "Alpha Staffing Hub",
        "full_name": "Alpha Admin",
        "email": "admin@alphahub.in",
        "password": "Password123!",
    })
    token_a = reg_a.json()["tokens"]["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Register Agency Beta
    reg_b = client.post("/api/v1/auth/register", json={
        "agency_name": "Beta Talent Group",
        "full_name": "Beta Admin",
        "email": "admin@betagroup.in",
        "password": "Password123!",
    })
    token_b = reg_b.json()["tokens"]["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # Agency Alpha creates a Job
    job_res = client.post("/api/v1/jobs", json={
        "title": "Alpha Confidential Architect",
        "minimum_experience": 8,
    }, headers=headers_a)
    assert job_res.status_code == 201
    job_a_id = job_res.json()["id"]

    # Agency Alpha creates a Candidate with Note
    cand_res = client.post("/api/v1/candidates", json={
        "full_name": "Alpha Candidate X",
        "current_location": "Delhi",
    }, headers=headers_a)
    assert cand_res.status_code == 201
    cand_a_id = cand_res.json()["id"]

    note_res = client.post(f"/api/v1/candidates/{cand_a_id}/notes", json={
        "note": "Alpha private salary expectation: 40 LPA"
    }, headers=headers_a)
    assert note_res.status_code == 201
    note_a_id = note_res.json()["id"]

    # --- Cross-Tenant Enforcements ---

    # 1. Agency Beta attempts to GET Agency Alpha's job -> 404
    get_job_b = client.get(f"/api/v1/jobs/{job_a_id}", headers=headers_b)
    assert get_job_b.status_code == 404

    # 2. Agency Beta attempts to PATCH Agency Alpha's job -> 404
    patch_job_b = client.patch(f"/api/v1/jobs/{job_a_id}", json={"title": "Hacked Title"}, headers=headers_b)
    assert patch_job_b.status_code == 404

    # 3. Agency Beta attempts to GET Agency Alpha's candidate -> 404
    get_cand_b = client.get(f"/api/v1/candidates/{cand_a_id}", headers=headers_b)
    assert get_cand_b.status_code == 404

    # 4. Agency Beta attempts to PATCH Agency Alpha's candidate -> 404
    patch_cand_b = client.patch(f"/api/v1/candidates/{cand_a_id}", json={"full_name": "Hacked Name"}, headers=headers_b)
    assert patch_cand_b.status_code == 404

    # 5. Agency Beta attempts to DELETE Agency Alpha's recruiter note -> 404
    del_note_b = client.delete(f"/api/v1/candidates/{cand_a_id}/notes/{note_a_id}", headers=headers_b)
    assert del_note_b.status_code == 404
