import pytest
from fastapi.testclient import TestClient

def get_auth_token(client: TestClient, email: str = "recruiter@candidatecorp.in") -> str:
    res = client.post("/api/v1/auth/register", json={
        "agency_name": "Candidate Corp",
        "full_name": "Senior Recruiter",
        "email": email,
        "password": "Password123!",
    })
    return res.json()["tokens"]["access_token"]

def test_create_and_retrieve_candidate(client: TestClient):
    token = get_auth_token(client, "lead@candidatemgmt.in")
    headers = {"Authorization": f"Bearer {token}"}

    payload = {
        "full_name": "Ananya Sen",
        "email": "ananya.sen@example.com",
        "current_title": "Full Stack Engineer",
        "total_experience_months": 48,
        "current_location": "Hyderabad",
        "professional_summary": "Experienced full-stack engineer with React and Node.js focus.",
        "skills": [
            {
                "skill_name": "React",
                "normalized_skill": "React",
                "proficiency": "ADVANCED",
            },
            {
                "skill_name": "TypeScript",
                "normalized_skill": "TypeScript",
                "proficiency": "ADVANCED",
            }
        ],
        "experiences": [
            {
                "company": "Tech Innovators Pvt Ltd",
                "job_title": "Senior Frontend Developer",
                "start_date": "2022-01",
                "end_date": "Present",
                "description": "Architected component system used by 500k users.",
            }
        ],
        "educations": [
            {
                "institution": "BITS Pilani",
                "qualification": "B.Tech",
                "field_of_study": "Computer Science",
                "start_year": 2017,
                "end_year": 2021,
            }
        ]
    }

    create_res = client.post("/api/v1/candidates", json=payload, headers=headers)
    assert create_res.status_code == 201
    cand = create_res.json()
    assert cand["full_name"] == "Ananya Sen"
    assert cand["current_location"] == "Hyderabad"
    assert len(cand["skills"]) == 2
    assert len(cand["experiences"]) == 1
    assert len(cand["educations"]) == 1
    cand_id = cand["id"]

    # Retrieve profile
    get_res = client.get(f"/api/v1/candidates/{cand_id}", headers=headers)
    assert get_res.status_code == 200
    assert get_res.json()["email"] == "ananya.sen@example.com"
    assert get_res.json()["experiences"][0]["company"] == "Tech Innovators Pvt Ltd"

def test_list_search_and_filter_candidates(client: TestClient):
    token = get_auth_token(client, "search@candidatemgmt.in")
    headers = {"Authorization": f"Bearer {token}"}

    # Candidate 1: Python developer in Pune
    client.post("/api/v1/candidates", json={
        "full_name": "Rahul Verma",
        "email": "rahul.verma@example.com",
        "current_title": "Python Developer",
        "total_experience_months": 36,
        "current_location": "Pune",
        "skills": [{"skill_name": "Python"}, {"skill_name": "Django"}]
    }, headers=headers)

    # Candidate 2: Cloud Architect in Gurugram
    client.post("/api/v1/candidates", json={
        "full_name": "Neha Gupta",
        "email": "neha.gupta@example.com",
        "current_title": "Cloud Architect",
        "total_experience_months": 72,
        "current_location": "Gurugram",
        "skills": [{"skill_name": "AWS"}, {"skill_name": "Kubernetes"}]
    }, headers=headers)

    # Search by title
    search_res = client.get("/api/v1/candidates?search=Cloud", headers=headers)
    assert search_res.status_code == 200
    assert len(search_res.json()) >= 1
    assert search_res.json()[0]["full_name"] == "Neha Gupta"

    # Filter by skill
    skill_res = client.get("/api/v1/candidates?skill=Python", headers=headers)
    assert skill_res.status_code == 200
    assert any(c["full_name"] == "Rahul Verma" for c in skill_res.json())
    assert all(c["full_name"] != "Neha Gupta" for c in skill_res.json())

    # Filter by location
    loc_res = client.get("/api/v1/candidates?location=Pune", headers=headers)
    assert loc_res.status_code == 200
    assert any(c["full_name"] == "Rahul Verma" for c in loc_res.json())

def test_update_and_archive_candidate(client: TestClient):
    token = get_auth_token(client, "updater@candidatemgmt.in")
    headers = {"Authorization": f"Bearer {token}"}

    create_res = client.post("/api/v1/candidates", json={
        "full_name": "Amit Patel",
        "current_location": "Ahmedabad",
    }, headers=headers)
    cand_id = create_res.json()["id"]

    # Update candidate
    upd_res = client.patch(f"/api/v1/candidates/{cand_id}", json={
        "current_title": "Lead Mobile Architect",
        "current_location": "Mumbai",
        "total_experience_months": 96,
    }, headers=headers)
    assert upd_res.status_code == 200
    assert upd_res.json()["current_title"] == "Lead Mobile Architect"
    assert upd_res.json()["current_location"] == "Mumbai"

    # Archive candidate
    arch_res = client.post(f"/api/v1/candidates/{cand_id}/archive", headers=headers)
    assert arch_res.status_code == 200
    assert arch_res.json()["profile_status"] == "ARCHIVED"

def test_recruiter_notes_crud(client: TestClient):
    token = get_auth_token(client, "notes@candidatemgmt.in")
    headers = {"Authorization": f"Bearer {token}"}

    cand_res = client.post("/api/v1/candidates", json={
        "full_name": "Siddharth Malhotra",
    }, headers=headers)
    cand_id = cand_res.json()["id"]

    # Add recruiter note
    note_res = client.post(f"/api/v1/candidates/{cand_id}/notes", json={
        "note": "Exceptional system design communication during phone screening."
    }, headers=headers)
    assert note_res.status_code == 201
    note_id = note_res.json()["id"]
    assert "Exceptional" in note_res.json()["note"]

    # Update recruiter note
    edit_note_res = client.patch(f"/api/v1/candidates/{cand_id}/notes/{note_id}", json={
        "note": "Exceptional system design communication. Strong candidate for Staff role."
    }, headers=headers)
    assert edit_note_res.status_code == 200
    assert "Staff role" in edit_note_res.json()["note"]

    # Note appears on candidate profile
    profile_res = client.get(f"/api/v1/candidates/{cand_id}", headers=headers)
    assert len(profile_res.json()["notes"]) == 1

    # Delete recruiter note
    del_note_res = client.delete(f"/api/v1/candidates/{cand_id}/notes/{note_id}", headers=headers)
    assert del_note_res.status_code == 200

    # Verify note deleted from candidate profile
    profile_after = client.get(f"/api/v1/candidates/{cand_id}", headers=headers)
    assert len(profile_after.json()["notes"]) == 0
