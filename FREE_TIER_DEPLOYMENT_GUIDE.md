# HireLens AI — ₹0 Free-Tier Deployment Guide (Dev Week 2 Demo)

**Target Architecture:** Vercel Hobby (Frontend) + Render Free Web Service (Backend) + Neon Serverless PostgreSQL (Database)  
**Hosting Cost:** **₹0 / $0.00 (Zero paid resources, zero credit card required)**  
**Target Duration:** Temporary Public Demonstration  
**Safety Status:** Isolated cloud resources. Zero modification to local environment or local databases.  

---

## 1. Architecture Overview (100% Free Stack)

This deployment architecture provides an enterprise-grade demonstration of HireLens AI at strictly **₹0 hosting cost**:

```
 ┌───────────────────────────┐         HTTPS (API Requests)          ┌───────────────────────────┐
 │       Vercel Hobby        │ ────────────────────────────────────► │      Render Free API      │
 │    Next.js 14 App Router  │                                       │     FastAPI + Uvicorn     │
 │  (Static & Edge Hosting)  │ ◄──────────────────────────────────── │    (512 MB RAM Container) │
 └───────────────────────────┘          JSON Web Tokens              └─────────────┬─────────────┘
                                                                                   │
                                                                   TLS / SSL       │ (PgBouncer Pooler)
                                                                (Auto-Reconnect)   │
                                                                                   ▼
                                                                     ┌───────────────────────────┐
                                                                     │   Neon Free PostgreSQL    │
                                                                     │   Serverless Postgres 16  │
                                                                     │    (0.5 GB / Auto-Sleep)  │
                                                                     └───────────────────────────┘
```

### Free-Tier Guarantees:
- **No Credit Card Required:** Vercel Hobby, Render Free Web Service, and Neon Free tier all allow deployment without requiring credit card registration.
- **Persistent Schemas & Synthetic Data:** Neon free tier does **not** auto-delete your database after 30 days.
- **Zero Cost Background Fallback:** Real-time scoring utilizes the sub-50ms deterministic math/rule engine, eliminating the need for paid Celery workers and Redis clusters.

---

## 2. Step 1: Provision Neon Serverless PostgreSQL (Free)

1. Navigate to **[https://neon.tech](https://neon.tech)** and sign in with GitHub or email (No credit card required).
2. Click **Create Project**:
   - **Project Name:** `hirelens-demo`
   - **Database Name:** `neondb` (Default)
   - **Region:** Select the region closest to your target audience (e.g., `AWS US East (Ohio)` or `AWS Europe (Frankfurt)`).
   - **Postgres Version:** `16`
3. Click **Create Project**.
4. In the **Connection Details** modal on the project dashboard:
   - Ensure the dropdown is set to **Pooled connection** (PgBouncer).
   - Copy the connection string. It will look like:
     ```text
     postgresql://neondb_owner:npg_RANDOM_SECRET@ep-plain-forest-a57q8f94-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```
   - Also note the **Direct connection** (uncheck "Pooled connection") for running Alembic migrations:
     ```text
     postgresql://neondb_owner:npg_RANDOM_SECRET@ep-plain-forest-a57q8f94.us-east-2.aws.neon.tech/neondb?sslmode=require
     ```

> [!NOTE]
> **Neon Serverless Pooling:** HireLens AI automatically detects Neon URLs and configures `pool_pre_ping=True`, `pool_recycle=300`, and `sslmode=require`. When Neon suspends after 5 minutes of inactivity, HireLens automatically reconnects without raising 500 errors.

---

## 3. Step 2: Deploy FastAPI Backend on Render (Free Web Service)

1. Navigate to **[https://dashboard.render.com](https://dashboard.render.com)** and sign in (No credit card required).
2. Click **New +** > **Web Service**.
3. Select **Build and deploy from a Git repository** and connect your `HireLens` repository.
4. Configure service parameters:
   - **Name:** `hirelens-api`
   - **Region:** Must match your Neon region (e.g., `Ohio (US East)` or `Frankfurt (EU Central)`).
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
   - **Instance Type:** Select **Free** ($0 / month).
5. Expand **Advanced**:
   - **Health Check Path:** `/health/live`
   - **Auto-Deploy:** `Yes`
6. Add Environment Variables (click **Add Environment Variable**):
   - `ENVIRONMENT`: `production`
   - `DEBUG`: `False`
   - `PROJECT_NAME`: `HireLens AI`
   - `SECRET_KEY`: Generate a random 64-char key locally (`python -c "import secrets; print(secrets.token_hex(32))"`)
   - `DATABASE_URL`: Paste the **Neon Pooled Connection String** from Step 1.
   - `BACKEND_CORS_ORIGINS`: `https://hirelens-demo.vercel.app`
   - `STORAGE_BACKEND`: `local`
   - `UPLOAD_DIR`: `./uploads`
   - `FALLBACK_RULE_ENGINE_ACTIVE`: `True`
   - `RAZORPAY_KEY_ID`: `rzp_test_placeholder`
   - `RAZORPAY_KEY_SECRET`: `dummy_secret`
7. Click **Create Web Service**.
8. Render will build and deploy the container. Once completed, your public URL will be displayed (e.g., `https://hirelens-api.onrender.com`).

---

## 4. Step 3: Run Alembic Migrations & Safe Demo Seeder

Before the frontend connects, the Neon PostgreSQL schema must be created and seeded with synthetic demo records.

### Option A: Via Render Web Service Shell Tab (Recommended)
1. In the Render Dashboard, open `hirelens-api`.
2. Click the **Shell** tab.
3. Run the schema migrations:
   ```bash
   alembic upgrade head
   ```
   *Result:* Applies all migrations up to revision `9c0d1e2f3a4b`.
4. Run the idempotent synthetic demo seeder:
   ```bash
   python -m app.db.seed_demo
   ```
   *Result:* Provisions demo agency "Apex Talent Partners", demo recruiter, jobs, and pre-computed candidate matches.

### Option B: From Your Local Machine (Direct to Neon)
If the Render Shell tab is slow to open, run migrations directly from your local terminal against Neon (without touching your local development database):
```powershell
# In D:\HireLens\backend
$env:DATABASE_URL="postgresql://neondb_owner:npg_SECRET@ep-plain-forest-a57q8f94.us-east-2.aws.neon.tech/neondb?sslmode=require"
.\venv\Scripts\alembic.exe upgrade head
.\venv\Scripts\python.exe -m app.db.seed_demo
Remove-Item Env:\DATABASE_URL
```

---

## 5. Step 4: Deploy Next.js Frontend on Vercel (Hobby Free)

1. Navigate to **[https://vercel.com](https://vercel.com)** and log in.
2. Click **Add New...** > **Project**.
3. Import your `HireLens` repository.
4. Configure project settings:
   - **Project Name:** `hirelens-demo`
   - **Framework Preset:** `Next.js`
   - **Root Directory:** Click **Edit** and choose `frontend`
   - **Build Command:** `npm run build`
   - **Output Directory:** `.next`
5. Expand **Environment Variables**:
   - **Key:** `NEXT_PUBLIC_API_URL`
   - **Value:** `https://hirelens-api.onrender.com` (Your Render Web Service URL with no trailing slash)
   - **Target:** Check Production, Preview, and Development.
6. Click **Deploy**.
7. Vercel will build and deploy the Next.js App Router static and dynamic pages. Once done, it will provide your public domain: `https://hirelens-demo.vercel.app`.

---

## 6. Step 5: End-to-End Verification

Perform these 4 rapid verification checks:

1. **Backend Health Probe:** Open `https://hirelens-api.onrender.com/health/ready`.  
   Expected JSON response: `{"status":"ready","database":"healthy"}`
2. **Frontend UI:** Open `https://hirelens-demo.vercel.app`. Verify that CSS, dark mode, and navigation render cleanly.
3. **Recruiter Login:**
   - URL: `https://hirelens-demo.vercel.app/login`
   - Email: `recruiter@apex-demo.hirelens.ai`
   - Password: `DemoRecruiter2026!`
4. **Pipeline & Matching:**
   - Navigate to `/pipeline` or `/candidates`.
   - Inspect synthetic candidate profiles (Elena Rostova, Marcus Vance, Priya Sharma, David Kim).
   - View Elena Rostova's **92.4% Match Score** and multi-factor breakdown.
