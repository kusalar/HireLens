import pytest
from fastapi.testclient import TestClient

def test_register_agency_and_owner(client: TestClient):
    payload = {
        "agency_name": "Apex Talent Partners",
        "full_name": "Rohan Sharma",
        "email": "rohan@apextalent.in",
        "password": "SecurePassword123!",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert "user" in data
    assert "tokens" in data
    assert data["user"]["email"] == "rohan@apextalent.in"
    assert data["user"]["role"] == "OWNER"
    assert data["user"]["is_active"] is True
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]

def test_duplicate_registration_fails(client: TestClient):
    payload = {
        "agency_name": "Alpha Staffing",
        "full_name": "Priya Nair",
        "email": "priya@alphastaffing.com",
        "password": "Password456!",
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    # Second registration with same email must fail
    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 400
    assert "already exists" in r2.json()["detail"]

def test_login_success_and_failure(client: TestClient):
    # Register user
    reg = client.post("/api/v1/auth/register", json={
        "agency_name": "Zeta Recruiters",
        "full_name": "Vikram Seth",
        "email": "vikram@zetarecruit.com",
        "password": "MySecretPassword1!",
    })
    assert reg.status_code == 201

    # Login valid
    login_valid = client.post("/api/v1/auth/login", json={
        "email": "vikram@zetarecruit.com",
        "password": "MySecretPassword1!",
    })
    assert login_valid.status_code == 200
    assert "access_token" in login_valid.json()["tokens"]

    # Login invalid password
    login_bad_pw = client.post("/api/v1/auth/login", json={
        "email": "vikram@zetarecruit.com",
        "password": "WrongPassword!",
    })
    assert login_bad_pw.status_code == 401

    # Login unknown email
    login_bad_email = client.post("/api/v1/auth/login", json={
        "email": "unknown@zetarecruit.com",
        "password": "MySecretPassword1!",
    })
    assert login_bad_email.status_code == 401

def test_refresh_token_workflow(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "agency_name": "Future Workforce",
        "full_name": "Aman Verma",
        "email": "aman@futurework.com",
        "password": "WorkforceSecure9!",
    })
    refresh_token = reg.json()["tokens"]["refresh_token"]

    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    data = refresh_res.json()
    assert "access_token" in data
    assert "refresh_token" in data

    # Bad refresh token
    bad_res = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.jwt.token"})
    assert bad_res.status_code == 401

def test_get_current_user_me(client: TestClient):
    reg = client.post("/api/v1/auth/register", json={
        "agency_name": "Elevate Search",
        "full_name": "Sunita Rao",
        "email": "sunita@elevatesearch.com",
        "password": "StrongPassword789!",
    })
    token = reg.json()["tokens"]["access_token"]

    # Authenticated request
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["email"] == "sunita@elevatesearch.com"

    # Unauthenticated request
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401
