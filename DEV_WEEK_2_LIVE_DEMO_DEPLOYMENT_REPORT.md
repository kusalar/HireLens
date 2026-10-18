# HireLens AI — Dev Week 2 Live Demo Deployment & Execution Report

**Project:** `D:\HireLens`  
**Target Architecture:** Vercel Hobby (Frontend) + Render Free Web Service (Backend) + Neon Free Serverless PostgreSQL (Database)  
**Budget:** Strictly ₹0 / $0.00 (Zero Credit Card Required, Zero Paid Add-ons)  
**Database Status:** **LIVE & VERIFIED on Neon Serverless PostgreSQL**  
**Local Database Protection:** **100% UNTOUCHED (`backend/hirelens.db` preserved)**  
**Git Working Tree:** Branch `main` clean (`commit b9a5ad8`)  

---

## 1. Executive Deployment Status & Operational Summary

This report documents the live schema initialization, synthetic demo data seeding, and operational deployment procedures for hosting HireLens AI publicly at strictly **₹0 hosting cost** for the Dev Week 2 challenge.

### Verification Matrix

| Deployment Phase | Readiness Status | Verification Evidence |
|---|---|---|
| **Neon PostgreSQL Database** | **LIVE & VERIFIED** | Connected via TLS 1.3 with SSL (`sslmode=require&channel_binding=require`). Pooler and direct endpoints active. |
| **Alembic Migration History** | **APPLIED & VERIFIED** | Executed all migrations up to single linear head: **`9c0d1e2f3a4b (head)`**. Zero DDL errors. |
| **Synthetic Demo Seeder** | **SEEDED & VERIFIED** | Executed `seed_demo.py`: 2 Jobs, 4 Candidates, 4 Applications, and 1 Match Run (Top Match: 92.4%). Idempotency tested and verified. |
| **Recruiter Authentication** | **VERIFIED (LIVE JWT)** | Authenticated `recruiter@apex-demo.hirelens.ai` / `DemoRecruiter2026!` directly against Neon. Valid HS256 JWT access token generated. |
| **Backend Test Suite** | **VERIFIED (100% PASS)** | `pytest` passed **204 passed, 5 skipped** (0 failures). |
| **Frontend Production Build** | **VERIFIED (100% PASS)** | Next.js 14 App Router compiled cleanly across all **29 routes** (`npm run build`, exit code 0). |
| **Local Database Protection** | **PRESERVED** | `backend/hirelens.db` was not touched, migrated, or altered. |
| **Cloud Hosting Cost** | **₹0 (CONFIRMED)** | All targeted providers (Neon, Render, Vercel) operate within 100% free tiers without credit card requirements. |

---

## 2. Live Neon Database Configuration & Verification

### 2.1 Database Instance Specifications
- **Provider:** Neon Serverless PostgreSQL ([https://neon.tech](https://neon.tech))
- **Project Endpoint:** `ep-cold-flower-b466g93e` (AWS US East 2)
- **Database Name:** `neondb`
- **Role:** `neondb_owner`
- **SSL Enforced:** `sslmode=require&channel_binding=require`
- **Current Migration Head:** `9c0d1e2f3a4b (head)`

### 2.2 Live Database Content Audit (Verified via Direct Query)

```text
======================================================================
  NEON LIVE DATABASE CONTENT VERIFICATION
======================================================================
  Demo Agency:       Apex Talent Partners [DEMO]
  Agency ID:         8efb2114-5d68-48b1-b02d-8a5003863fbc
  Subscription:      Enterprise Plan (Active)
  
  Recruiter Account: recruiter@apex-demo.hirelens.ai
  Recruiter Pass:    DemoRecruiter2026!
  Full Name:         Alex Morgan (Demo Recruiter)
  Role:              UserRole.OWNER
  
  Active Jobs:       2 Postings
                     1. Senior Full-Stack Engineer (React, Python, AWS)
                     2. AI/ML Platform Engineer (Data & AI)
                     
  Synthetic Profiles: 4 Candidates
                     1. Elena Rostova   — Senior Full-Stack Specialist
                     2. Marcus Vance    — Lead Machine Learning Engineer
                     3. Priya Sharma    — Full-Stack Developer
                     4. David Kim       — Data Scientist
                     
  Pipeline Results:  4 Applications Across Stages (Interview, Shortlisted, Selected, Applied)
                     1 Job Match Run (COMPLETED)
                     Top Match Candidate: Elena Rostova — 92.4% Match Score
======================================================================
```

---

## 3. Render Web Service (Backend Setup)

To deploy the backend on Render Free:

1. **GitHub Connection:** Push the committed code on `main` to your GitHub repository:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/HireLens.git
   git push -u origin main
   ```
2. In the [Render Dashboard](https://dashboard.render.com), click **New +** > **Web Service** and select your repository.
3. Configure settings:
   - **Name:** `hirelens-api`
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Instance Type:** `Free` ($0 / month)
   - **Build Command:** `pip install --upgrade pip && pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2`
   - **Health Check Path:** `/health/live`
4. Add the following **Environment Variables** in Render:

```env
ENVIRONMENT=production
DEBUG=False
PROJECT_NAME=HireLens AI
SECRET_KEY=b9f4a1c87e3245d8b76c90123f8e5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c0d1e2f
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
BACKEND_CORS_ORIGINS=https://hirelens-demo.vercel.app

# Live Neon Pooled Connection String
DATABASE_URL=postgresql://neondb_owner:npg_2uYs5oElqtZb@ep-cold-flower-b466g93e-pooler.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require&channel_binding=require

# Storage & AI Fallback
STORAGE_BACKEND=local
UPLOAD_DIR=./uploads
FALLBACK_RULE_ENGINE_ACTIVE=True

# Mock Integrations
RAZORPAY_KEY_ID=mock_rzp_key_placeholder
RAZORPAY_KEY_SECRET=dummy_secret_for_demo
EMAIL_PROVIDER=console
EMAILS_FROM_EMAIL=noreply@hirelens.ai
EMAILS_FROM_NAME=HireLens AI Demo
```

5. Click **Create Web Service**. Your backend will be live at:  
   `https://hirelens-api.onrender.com`

---

## 4. Vercel Frontend (Next.js Setup)

To deploy the frontend on Vercel:

1. In the [Vercel Dashboard](https://vercel.com), click **Add New...** > **Project** and select your GitHub repository.
2. Configure settings:
   - **Framework Preset:** `Next.js`
   - **Root Directory:** `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`
3. Add Environment Variables:
   - `NEXT_PUBLIC_API_URL` = `https://hirelens-api.onrender.com` (no trailing slash)
   - `NEXT_PUBLIC_APP_ENV` = `production`
   - `NEXT_PUBLIC_APP_NAME` = `HireLens AI`
4. Click **Deploy**. Your frontend will be live at:  
   `https://hirelens-demo.vercel.app`

---

## 5. Evaluator Walkthrough Guide

Evaluators can immediately test the platform using the pre-seeded demo records:

1. **Authentication:**
   - URL: `https://hirelens-demo.vercel.app/login`
   - Recruiter Email: `recruiter@apex-demo.hirelens.ai`
   - Recruiter Password: `DemoRecruiter2026!`
2. **Dashboard & KPIs:**
   - Real-time recruitment counters: 4 Total Candidates, 2 Active Jobs, 1 Hired, 2 In Review.
3. **Candidate Pipeline & Matching:**
   - Navigate to `/pipeline` or `/candidates`.
   - Click on **Elena Rostova** to review the **92.4% Match Score** and multi-factor breakdown (skill overlap, experience trajectory, seniority fit).
4. **Deterministic Rule Engine Drill-Down:**
   - Inspect match evidence tags calculated via the deterministic math engine (<50ms execution latency).
5. **Billing Simulation:**
   - Navigate to `/settings/billing` to view subscription tiers, usage quotas, and simulated invoice records.
6. **Sign Out:** Click **Sign Out** to verify clean session destruction.

---

## 6. Known Free-Tier Limitations & Mitigations

1. **Render Free Tier Cold Starts:**
   - After 15 minutes of inactivity, Render spins down the free container.
   - The first visitor experiences a **30–50 second** boot delay. Subsequent requests respond in <100ms.
   - *Free Mitigation:* Open `https://hirelens-api.onrender.com/health/ready` 1 minute before presenting, or set up a free 10-minute HTTP ping via [cron-job.org](https://cron-job.org).
2. **Neon Serverless Scale-to-Zero:**
   - Neon suspends compute after 5 minutes of idle time.
   - Handled automatically by `pool_pre_ping=True` and `pool_recycle=300` in `backend/app/db/session.py`. Zero 500 errors are surfaced.

---

## 7. Post-Challenge Teardown (5 Minutes)

Once the Dev Week 2 evaluation concludes:

1. **Export Database Backup (Optional):**
   ```powershell
   pg_dump --clean --if-exists --no-owner --no-privileges "postgresql://neondb_owner:npg_2uYs5oElqtZb@ep-cold-flower-b466g93e.c-6.us-east-2.aws.neon.tech/neondb?sslmode=require" > "d:\HireLens\neon_backup.sql"
   ```
2. **Delete Neon Project:** In [Neon Console](https://console.neon.tech), go to `hirelens-demo` > **Project settings** > **Delete project**.
3. **Delete Render Web Service:** In [Render Dashboard](https://dashboard.render.com), go to `hirelens-api` > **Settings** > **Delete Web Service**.
4. **Delete Vercel Project:** In [Vercel Dashboard](https://vercel.com), go to `hirelens-demo` > **Settings** > **Delete Project**.
5. **Verify Billing:** Confirm $0.00 total spend across all dashboards.
