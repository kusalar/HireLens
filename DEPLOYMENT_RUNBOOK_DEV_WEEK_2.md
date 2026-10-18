# HireLens AI — Dev Week 2 Deployment Runbook

**Project:** `D:\HireLens`  
**Target Architecture:** Vercel (Next.js 14) + Render (FastAPI + Hosted PostgreSQL 16)  
**Mode:** Temporary Public Demonstration  
**Safety Status:** Non-destructive. Operates exclusively on isolated cloud instances.  

---

## 1. Prerequisites & Preparation

Before beginning deployment, ensure you have:
1. A **GitHub repository** containing the current HireLens codebase.
2. A **Render account** (free tier or starter subscription).
3. A **Vercel account** (Hobby plan is sufficient).
4. Local shell access to run verification tests or run migrations remotely if desired.

> [!CAUTION]
> **Zero Local Database Impact:** Under no circumstances should your local development database (`hirelens.db` or local PostgreSQL) be connected to the cloud services. All remote steps use the new hosted PostgreSQL connection strings.

---

## 2. Phase 1: Provision the Render Hosted PostgreSQL Database

1. Log into the [Render Dashboard](https://dashboard.render.com).
2. Click **New +** in the top navigation bar and select **PostgreSQL**.
3. Fill in the database specifications:
   - **Name:** `hirelens-demo-db`
   - **Database:** `hirelens_demo`
   - **User:** `hirelens_admin`
   - **Region:** Choose the region closest to your target evaluators (e.g., `Frankfurt (EU Central)` or `Oregon (US West)`).
   - **PostgreSQL Version:** `16`
   - **Instance Type:**
     - *Free Plan:* $0/month. 256 MB RAM, 1 GB storage, expires after 30 days. Perfect for a 1-week challenge.
     - *Basic Plan:* $6/month (pro-rated to ~$1.50 for 7 days). 512 MB RAM, 10 GB persistent storage, no expiration.
4. Click **Create Database**.
5. Once provisioned (approx. 60–90 seconds), navigate to the database **Info** tab and locate:
   - **Internal Database URL:** (Used by Render Web Service):  
     `postgres://hirelens_admin:[PASSWORD]@dpg-[ID]-a/hirelens_demo`
   - **External Database URL:** (Used for local migration runner or pg_dump):  
     `postgres://hirelens_admin:[PASSWORD]@dpg-[ID]-a.[REGION]-postgres.render.com/hirelens_demo`

---

## 3. Phase 2: Deploy the FastAPI Backend on Render

1. From the Render Dashboard, click **New +** and select **Web Service**.
2. Connect your GitHub repository (`HireLens`).
3. Configure the Web Service settings:
   - **Name:** `hirelens-api`
   - **Region:** Must match the region selected for your PostgreSQL database (e.g., `Frankfurt` or `Oregon`).
   - **Branch:** `main` (or your active release branch)
   - **Root Directory:** `backend`
   - **Runtime:** `Python 3`
   - **Build Command:**
     ```bash
     pip install --upgrade pip && pip install -r requirements.txt
     ```
   - **Start Command:**
     ```bash
     uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 2
     ```
   - **Instance Type:**
     - *Free:* $0/month. 512 MB RAM. Spins down after 15 min of inactivity (30-50s cold start).
     - *Starter:* $7/month (pro-rated ~$1.75 for 7 days). Always-on, 512 MB RAM, 0.5 CPU, zero cold starts. Recommended for evaluator review.
4. Expand the **Advanced** section:
   - **Health Check Path:** `/health/live`
   - **Auto-Deploy:** `Yes`
5. Click **Add Environment Variable** and add the following keys (see [DEPLOYMENT_ENVIRONMENT_VARIABLES.md](file:///D:/HireLens/DEPLOYMENT_ENVIRONMENT_VARIABLES.md) for full context):
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `False`
   - `PROJECT_NAME`: `HireLens AI`
   - `SECRET_KEY`: Generate a random 64-character hex key:
     ```bash
     python -c "import secrets; print(secrets.token_hex(32))"
     ```
   - `DATABASE_URL`: Paste the **Internal Database URL** from Phase 1.  
     *(Note: The HireLens backend automatically normalizes `postgres://` to `postgresql+psycopg2://`)*
   - `BACKEND_CORS_ORIGINS`: Temporary placeholder: `https://hirelens-demo.vercel.app`
   - `STORAGE_BACKEND`: `local`
   - `UPLOAD_DIR`: `./uploads`
   - `FALLBACK_RULE_ENGINE_ACTIVE`: `True`
   - `RAZORPAY_KEY_ID`: `rzp_test_placeholder`
   - `RAZORPAY_KEY_SECRET`: `dummy_secret`
6. Click **Create Web Service**.
7. Wait for the initial deployment to complete. Render will assign a public HTTPS URL (e.g., `https://hirelens-api.onrender.com`). Note this URL down.

---

## 4. Phase 3: Execute Database Migrations & Safe Demo Seeding

Before the application can handle requests, the database schema must be initialized and seeded with synthetic demonstration data.

### Option A: Via Render Web Service Shell Tab (Recommended)
1. In the Render Dashboard, navigate to your `hirelens-api` Web Service.
2. Click the **Shell** tab on the left sidebar.
3. Once the terminal connects, run the Alembic migration command:
   ```bash
   alembic upgrade head
   ```
   *Expected output:* Confirms applying migrations up to head `9c0d1e2f3a4b (create platform admin and audit logs tables)`.
4. Run the idempotent synthetic demo seeder:
   ```bash
   python -m app.db.seed_demo
   ```
   *Expected output:*
   ```text
   ======================================================================
     HIRELENS AI - SAFE SYNTHETIC DEMO SEED COMPLETED
   ======================================================================
     Demo Agency:   Apex Talent Partners (DEMO-AGENCY-001)
     Admin User:    admin@apex-demo.hirelens.ai  [Password: DemoPass2026!]
     Recruiter:     recruiter@apex-demo.hirelens.ai  [Password: DemoPass2026!]
     Jobs Created:  2 (Senior Full-Stack Engineer, Lead Data Scientist)
     Candidates:    4 Synthetic Profiles
     Pipeline Runs: 4 Pre-computed Matches (Top Score: 92.4%)
   ======================================================================
   ```

### Option B: From Your Local Machine (Direct to External DB URL)
If the Render Web Service Shell is not accessible, you can apply migrations remotely from your local workstation without touching your local database:
```powershell
# In D:\HireLens\backend
$env:DATABASE_URL="postgres://hirelens_admin:[PASSWORD]@dpg-[ID]-a.[REGION]-postgres.render.com/hirelens_demo"
alembic upgrade head
python -m app.db.seed_demo
Remove-Item Env:\DATABASE_URL
```

---

## 5. Phase 4: Deploy the Next.js Frontend on Vercel

1. Log into your [Vercel Dashboard](https://vercel.com).
2. Click **Add New...** > **Project**.
3. Import your `HireLens` repository.
4. In the **Configure Project** screen:
   - **Project Name:** `hirelens-demo` (or desired name)
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click **Edit** and select `frontend`
   - **Build Command:** `npm run build` (Default)
   - **Output Directory:** `.next` (Default)
   - **Install Command:** `npm install` (Default)
5. Expand the **Environment Variables** section and configure:
   - **Name:** `NEXT_PUBLIC_API_URL`
   - **Value:** Your deployed Render backend URL with protocol and no trailing slash:  
     `https://hirelens-api.onrender.com`
   - Select Environments: **Production**, **Preview**, and **Development**.
6. Click **Deploy**.
7. Vercel will build and deploy the Next.js frontend (approx. 90–120 seconds).
8. Once finished, Vercel will provide your public domain:  
   `https://hirelens-demo.vercel.app`

---

## 6. Phase 5: Align CORS & Final Backend Configuration

1. In the Render Dashboard, return to `hirelens-api` > **Environment**.
2. If your assigned Vercel URL differs from the initial placeholder, update `BACKEND_CORS_ORIGINS`:
   ```text
   BACKEND_CORS_ORIGINS=https://hirelens-demo.vercel.app
   ```
   *(Note: The backend CORS middleware already permits all `*.vercel.app` domains automatically via regex, so preview deployments will also work immediately).*
3. If updated, click **Save Changes** (Render will automatically perform a fast zero-downtime redeploy).

---

## 7. Phase 6: End-to-End Verification & Health Probes

Perform these checks before sharing the URL with evaluators:

### 1. Backend Health Check
Open in browser or terminal:
```bash
curl -i https://hirelens-api.onrender.com/health/ready
```
**Expected response:**
```json
{"status":"ready","database":"healthy"}
```

### 2. Frontend Page Loading
Visit `https://hirelens-demo.vercel.app` in an incognito window:
- Verify that the landing page renders with full CSS styling.
- Click **Sign In** and verify seamless navigation to `/login`.

### 3. Recruiter Authentication & Pipeline Walkthrough
1. Enter the seeded demo credentials:
   - **Email:** `recruiter@apex-demo.hirelens.ai`
   - **Password:** `DemoPass2026!`
2. Verify redirect to the **Dashboard**:
   - Check key recruitment metrics (Total Candidates: 4, Active Jobs: 2).
3. Navigate to **Jobs**:
   - View *Senior Full-Stack Engineer (React/Python)* and *Lead Data Scientist (NLP/MLOps)*.
4. Navigate to **Candidates / Pipeline**:
   - Inspect synthetic candidate profiles: *Elena Rostova*, *Marcus Vance*, *Priya Sharma*, *David Kim*.
   - View pre-computed AI match scores (Elena Rostova: **92.4% Match**).
   - Drill into match explanation to verify evidence breakdowns (Skill overlap, Experience depth, Seniority fit).
5. Test direct route refreshes:
   - Press browser Refresh (F5) on `/candidates` or `/pipeline`. Verify that Next.js App Router does not throw a 404.
6. Click **Sign Out** and verify clean session termination.

---

## 8. Evaluator Demo Guide (Copy & Share)

You can share the following brief with Dev Week 2 evaluators:

```markdown
### HireLens AI — Dev Week 2 Interactive Demo
**Demo URL:** https://hirelens-demo.vercel.app  
**Backend API Docs:** https://hirelens-api.onrender.com/docs  

#### Demo Recruiter Credentials:
- **Email:** `recruiter@apex-demo.hirelens.ai`
- **Password:** `DemoPass2026!`

#### Demo Platform Admin Credentials (Tenant-scoped):
- **Email:** `admin@apex-demo.hirelens.ai`
- **Password:** `DemoPass2026!`

#### Key Features to Evaluate:
1. **Interactive Recruitment Pipeline:** View candidate progression from Sourced to Offer.
2. **AI & Mathematical Match Scoring:** Inspect multi-factor scoring (Elena Rostova - 92.4% score with evidence breakdown).
3. **Multi-Tenant Agency Isolation:** Pre-configured under synthetic agency "Apex Talent Partners".
4. **Subscription & Feature Entitlements:** Enterprise tier tier features active.
5. **Deterministic Fallback Engine:** Real-time scoring functions with zero external LLM dependencies.
```
