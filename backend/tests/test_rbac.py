import pytest
from fastapi.testclient import TestClient

def test_rbac_owner_and_recruiter_permissions(client: TestClient):
    # 1. Register Agency with OWNER
    reg = client.post("/api/v1/auth/register", json={
        "agency_name": "Nexus Staffing",
        "full_name": "Nexus Owner",
        "email": "owner@nexusstaffing.com",
        "password": "Password123!",
    })
    owner_token = reg.json()["tokens"]["access_token"]

    # 2. OWNER can update agency profile
    upd = client.patch(
        "/api/v1/agency/profile",
        json={"name": "Nexus Staffing Solutions"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert upd.status_code == 200
    assert upd.json()["name"] == "Nexus Staffing Solutions"

    # 3. OWNER can invite RECRUITER
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        json={"email": "recruiter@nexusstaffing.com", "role": "RECRUITER"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert invite_res.status_code == 201
    invite_token = invite_res.json()["token"]

    # 4. Accept invitation
    accept_res = client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": invite_token,
            "full_name": "Rita Recruiter",
            "password": "RecruiterPass123!",
        },
    )
    assert accept_res.status_code == 201
    assert accept_res.json()["role"] == "RECRUITER"

    # 5. Log in as RECRUITER
    login_rec = client.post(
        "/api/v1/auth/login",
        json={"email": "recruiter@nexusstaffing.com", "password": "RecruiterPass123!"},
    )
    assert login_rec.status_code == 200
    recruiter_token = login_rec.json()["tokens"]["access_token"]

    # 6. RECRUITER tries to update agency profile -> 403 Forbidden
    rec_upd = client.patch(
        "/api/v1/agency/profile",
        json={"name": "Hacked Agency Name"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert rec_upd.status_code == 403
    assert "Operation not permitted" in rec_upd.json()["detail"]

    # 7. RECRUITER tries to invite another member -> 403 Forbidden
    rec_invite = client.post(
        "/api/v1/agency/members/invite",
        json={"email": "another@nexusstaffing.com", "role": "VIEWER"},
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert rec_invite.status_code == 403

    # 8. RECRUITER CAN view team members -> 200 OK
    rec_members = client.get(
        "/api/v1/agency/members",
        headers={"Authorization": f"Bearer {recruiter_token}"},
    )
    assert rec_members.status_code == 200
    assert len(rec_members.json()) == 2

def test_rbac_viewer_read_only_restriction(client: TestClient):
    # Register agency
    reg = client.post("/api/v1/auth/register", json={
        "agency_name": "Pinnacle HR",
        "full_name": "Pinnacle Boss",
        "email": "boss@pinnaclehr.in",
        "password": "Password123!",
    })
    owner_token = reg.json()["tokens"]["access_token"]

    # Invite user with VIEWER role
    inv_res = client.post(
        "/api/v1/agency/members/invite",
        json={"email": "viewer@pinnaclehr.in", "role": "VIEWER"},
        headers={"Authorization": f"Bearer {owner_token}"},
    )
    assert inv_res.status_code == 201
    inv_token = inv_res.json()["token"]

    # Accept invite
    client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": inv_token,
            "full_name": "Vinay Viewer",
            "password": "ViewerPassword1!",
        },
    )

    # Log in as VIEWER
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "viewer@pinnaclehr.in", "password": "ViewerPassword1!"},
    )
    viewer_token = login_res.json()["tokens"]["access_token"]
    viewer_headers = {"Authorization": f"Bearer {viewer_token}"}

    # 1. VIEWER cannot create a Job -> 403
    bad_job = client.post("/api/v1/jobs", json={"title": "Unauthorized Job"}, headers=viewer_headers)
    assert bad_job.status_code == 403

    # 2. VIEWER cannot create a Candidate -> 403
    bad_cand = client.post("/api/v1/candidates", json={"full_name": "Unauthorized Cand"}, headers=viewer_headers)
    assert bad_cand.status_code == 403

    # 3. VIEWER can read Jobs list -> 200
    read_jobs = client.get("/api/v1/jobs", headers=viewer_headers)
    assert read_jobs.status_code == 200

    # 4. VIEWER can read Candidates list -> 200
    read_cands = client.get("/api/v1/candidates", headers=viewer_headers)
    assert read_cands.status_code == 200
