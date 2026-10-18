# HireLens AI — ₹0 Free-Tier Deployment Checklist

**Architecture:** Vercel Hobby + Render Free + Neon Free  
**Target Cost:** **₹0 / $0.00 (Zero Credit Card Required)**  
**Verification Standard:** Pre-Flight, In-Flight, and Post-Flight Verification  

---

## Pre-Flight Verification (Local Workstation)

- [x] **Local Database Protection:** Confirmed local `hirelens.db` is completely untouched. Zero local migrations executed.
- [x] **Next.js Frontend Build:** Tested `npm run build` in `frontend/`. All 29 routes statically compiled without errors (exit code 0).
- [x] **FastAPI Test Suite:** Ran backend test suite with Neon-compatible session pooling (`pool_pre_ping=True`, `pool_recycle=300`).
- [x] **Zero Hardcoded Localhost URLs:** Verified `frontend/lib/api.ts` strictly defaults to `process.env.NEXT_PUBLIC_API_URL`.
- [x] **Zero Hardcoded Secrets in Codebase:** Verified all passwords, database URLs, and cryptographic tokens are loaded dynamically from environment variables.

---

## Phase 1: Neon Serverless PostgreSQL Setup

- [ ] **Account Creation:** Sign in at [https://neon.tech](https://neon.tech) (Free tier, zero credit card requirement).
- [ ] **Project Provisioning:**
  - [ ] Name: `hirelens-demo`
  - [ ] PostgreSQL Version: `16`
  - [ ] Region: Selected nearest region (e.g. `AWS US East (Ohio)` or `AWS Europe (Frankfurt)`).
- [ ] **Connection Strings Captured:**
  - [ ] **Pooled Connection URL** (PgBouncer with `-pooler` prefix and `?sslmode=require`):
    `postgresql://neondb_owner:[PASSWORD]@[ENDPOINT]-pooler.[REGION].neon.tech/neondb?sslmode=require`
  - [ ] **Direct Connection URL** (for running DDL migrations):
    `postgresql://neondb_owner:[PASSWORD]@[ENDPOINT].[REGION].neon.tech/neondb?sslmode=require`

---

## Phase 2: Render Free Web Service Deployment

- [ ] **Account Setup:** Sign in at [https://dashboard.render.com](https://dashboard.render.com) (Zero credit card requirement).
- [ ] **Web Service Configuration:**
  - [ ] Repository: Connected GitHub repository
  - [ ] Name: `hirelens-api`
  - [ ] Root Directory: `backend`
  - [ ] Runtime: `Python 3`
  - [ ] Instance Type: **Free ($0/month)**
  - [ ] Build Command: `pip install --upgrade pip && pip install -r requirements.txt`
  - [ ] Start Command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
  - [ ] Health Check Path: `/health/live`
- [ ] **Environment Variables Injected:**
  - [ ] `ENVIRONMENT` = `production`
  - [ ] `DEBUG` = `False`
  - [ ] `PROJECT_NAME` = `HireLens AI`
  - [ ] `SECRET_KEY` = `[Random 64-char hex]`
  - [ ] `DATABASE_URL` = `[Neon Pooled Connection String]`
  - [ ] `BACKEND_CORS_ORIGINS` = `https://hirelens-demo.vercel.app`
  - [ ] `FALLBACK_RULE_ENGINE_ACTIVE` = `True`
  - [ ] `STORAGE_BACKEND` = `local`
  - [ ] `UPLOAD_DIR` = `./uploads`
  - [ ] `RAZORPAY_KEY_ID` = `rzp_test_placeholder`
  - [ ] `RAZORPAY_KEY_SECRET` = `dummy_secret_for_demo`
  - [ ] `EMAIL_PROVIDER` = `console`
- [ ] **Deployment Execution:** Click **Create Web Service**. Wait for build to complete.
- [ ] **Public Backend URL Captured:** Note the assigned URL: `https://hirelens-api.onrender.com`.

---

## Phase 3: Database Migrations & Safe Demo Seeder

- [ ] **Run Alembic Migrations:**
  - Via Render Web Service **Shell** tab:
    ```bash
    alembic upgrade head
    ```
  - *Verify:* Outputs clean execution through migration head `9c0d1e2f3a4b`.
- [ ] **Run Safe Synthetic Demo Seeder:**
  - In Render Shell:
    ```bash
    python -m app.db.seed_demo
    ```
  - *Verify:* Displays summary confirmation:
    - Agency: `Apex Talent Partners [DEMO]`
    - Recruiter: `recruiter@apex-demo.hirelens.ai` / `DemoRecruiter2026!`
    - Jobs: 2 Active Job Postings
    - Candidates: 4 Synthetic Profiles
    - Pipeline: 4 Pre-computed AI Matches (Top: Elena Rostova - 92.4%)

---

## Phase 4: Vercel Frontend Deployment

- [ ] **Account Setup:** Sign in at [https://vercel.com](https://vercel.com) (Hobby Free tier, zero credit card requirement).
- [ ] **Project Import:**
  - [ ] Import `HireLens` repository.
  - [ ] Framework: `Next.js`
  - [ ] Root Directory: `frontend`
- [ ] **Frontend Environment Variable:**
  - [ ] `NEXT_PUBLIC_API_URL` = `https://hirelens-api.onrender.com` (no trailing slash).
  - [ ] Set for **Production**, **Preview**, and **Development**.
- [ ] **Deploy:** Click **Deploy**. Wait ~90 seconds for Next.js build.
- [ ] **Public Frontend URL Captured:** Note URL: `https://hirelens-demo.vercel.app`.

---

## Phase 5: Live Smoke Test & Verification

- [ ] **API Health Probe:**
  ```bash
  curl -i https://hirelens-api.onrender.com/health/ready
  ```
  *Expected:* HTTP 200 with `{"status":"ready","database":"healthy"}`.
- [ ] **Frontend Route Check:** Visit `https://hirelens-demo.vercel.app`. Confirm CSS and styling render.
- [ ] **Direct Navigation Check:** Refresh browser on `/candidates` and `/dashboard` (confirms no 404 routing errors).
- [ ] **Recruiter Authentication:**
  - Log in with `recruiter@apex-demo.hirelens.ai` / `DemoRecruiter2026!`.
  - Confirm dashboard metrics load (4 Candidates, 2 Jobs).
- [ ] **Candidate Match Inspection:**
  - Open candidate *Elena Rostova*.
  - Verify **92.4% Match Score** and multi-factor breakdown (skills, seniority, experience).
- [ ] **Session Teardown:** Click **Sign Out** and verify clean return to login screen.
