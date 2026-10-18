# HireLens AI — Temporary Demo Cost, Backup & Teardown Guide

**Project:** `D:\HireLens`  
**Target Environment:** Vercel (Frontend) + Render (Backend & Database)  
**Challenge:** Dev Week 2 Demonstration  
**Lifecycle:** Ephemeral / Temporary Deployment  

---

## 1. Hosting Tier Comparison & Cost Breakdown

To host the Dev Week 2 public demonstration, two viable deployment tiers are available. Both options use standard cloud providers and require zero long-term commitments.

### Option A: 100% Free Tier ($0.00 Total)
Recommended if you want zero cloud expenditure and do not mind a minor cold-start latency when the service has been idle.

| Component | Provider & Tier | Monthly Rate | 7-Day Challenge Cost | Resource Limits & Behavior |
|---|---|---|---|---|
| **Frontend** | Vercel Hobby | $0.00 | **$0.00** | 100 GB bandwidth, unlimited preview deployments, global edge CDN. Fast and always-on. |
| **Backend API** | Render Free Web Service | $0.00 | **$0.00** | 512 MB RAM, shared CPU. **Spins down after 15 min of inactivity.** Evaluator experiences a 30–50s initial cold start when opening the demo after an idle period. |
| **Database** | Render Free PostgreSQL | $0.00 | **$0.00** | 256 MB RAM, 1 GB storage, 100 max connections. **Expires and is permanently deleted after 30 days.** |
| **Workers & Cache** | *Omitted for Demo* | $0.00 | **$0.00** | Pre-seeded synthetic records and synchronous deterministic rule engines eliminate the need for Celery & Redis. |
| **Total Cost** | | **$0.00** | **$0.00** | **Completely free.** |

---

### Option B: High-Reliability Demo Tier (~$3.25 Pro-Rated for 7 Days)
**Recommended for Evaluator Polish:** Eliminates cold starts completely so judges experience instant sub-second response times on first visit. Render bills by the second, so you only pay for the exact days the services are running.

| Component | Provider & Tier | Monthly Rate | 7-Day Challenge Cost | Resource Limits & Behavior |
|---|---|---|---|---|
| **Frontend** | Vercel Hobby | $0.00 | **$0.00** | Global edge deployment, instant response. |
| **Backend API** | Render Starter Web Service | $7.00 / mo | **~$1.75** (7 days) | **Always-on (Zero cold starts).** 0.5 CPU, 512 MB RAM. Instant response times for evaluators. |
| **Database** | Render Basic PostgreSQL | $6.00 / mo | **~$1.50** (7 days) | 512 MB RAM, 10 GB persistent SSD storage. **No 30-day expiration policy.** Automated daily backups. |
| **Total Cost** | | **$13.00 / mo** | **~$3.25** | **Billed pro-rata by second. Cancel immediately after judging.** |

---

## 2. Resource Limitations & Lifecycle Rules

### 2.1 Render Free Tier Inactivity Spin-Down
- **Behavior:** The free web service automatically hibernates after 15 minutes of zero HTTP traffic.
- **Cold-Start Latency:** 30–50 seconds on the very first incoming request. Subsequent requests take <100ms.
- **Evaluator Impact:** Evaluators who click the demo link while the container is asleep will see a loading spinner for ~40 seconds.
- **Mitigation:**
  - If using Option A, trigger an automated ping (e.g. through UptimeRobot or a simple periodic script) to `https://hirelens-api.onrender.com/health/live` every 10 minutes during the review period.
  - If using Option B, the service never sleeps.

### 2.2 Render Free PostgreSQL 30-Day Auto-Deletion
- **Behavior:** Free PostgreSQL instances created on Render are automatically and irreversibly deleted exactly **30 days** after creation.
- **Evaluator Impact:** None during the 7-day Dev Week 2 evaluation window.
- **Mitigation:** Export the database backup using the `pg_dump` procedure below before the 30-day window closes.

---

## 3. Database Backup Runbook (Before Teardown)

Before decommissioning or deleting your cloud database, export a complete snapshot of all schemas, migrations, synthetic candidate records, and matching evidence.

### 3.1 Prerequisites
You need PostgreSQL client tools (`pg_dump`) installed locally. If you do not have PostgreSQL installed locally, you can use a one-off Docker container.

### 3.2 Backup Execution via External Database URL

1. In the Render Dashboard, open your PostgreSQL instance (`hirelens-demo-db`).
2. Copy the **External Database URL**:  
   `postgres://hirelens_admin:[PASSWORD]@dpg-[ID]-a.[REGION]-postgres.render.com/hirelens_demo`

3. Run the export command from your local terminal (Windows PowerShell or Linux):

```powershell
# Windows PowerShell
$DB_URL = "postgres://hirelens_admin:[PASSWORD]@dpg-[ID]-a.[REGION]-postgres.render.com/hirelens_demo"
pg_dump --clean --if-exists --no-owner --no-privileges "$DB_URL" > "d:\HireLens\hirelens_demo_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
```

*Or using Docker if local `pg_dump` is not installed:*
```bash
docker run --rm -v "D:\HireLens:/backup" postgres:16 pg_dump \
  --clean --if-exists --no-owner --no-privileges \
  "postgres://hirelens_admin:[PASSWORD]@dpg-[ID]-a.[REGION]-postgres.render.com/hirelens_demo" \
  -f "/backup/hirelens_demo_backup.sql"
```

### 3.3 Verifying the Backup File
Inspect the generated `.sql` file:
- File size should be between **50 KB and 5 MB** (containing schema DDL and seeded demo records).
- Verify the presence of Alembic version table and candidate records:
  ```powershell
  Get-Content "d:\HireLens\hirelens_demo_backup.sql" | Select-String "alembic_version", "Apex Talent Partners"
  ```

---

## 4. Teardown & Decommission Procedure (Post-Challenge)

Follow these steps immediately after the Dev Week 2 challenge evaluation closes to guarantee that zero recurring charges occur and no cloud assets remain orphaned.

### Step 1: Export Final Database Backup
Perform the `pg_dump` procedure documented in Section 3 above. Save the `.sql` archive in `D:\HireLens\backups\`.

### Step 2: Delete Render PostgreSQL Instance
1. In the [Render Dashboard](https://dashboard.render.com), click on `hirelens-demo-db`.
2. Scroll to the bottom of the page to the **Danger Zone**.
3. Click **Delete Database**.
4. Type the database name to confirm and click **Delete**.
5. *Result:* The database is immediately de-provisioned and billing stops instantly.

### Step 3: Delete Render Web Service
1. In the Render Dashboard, click on `hirelens-api`.
2. Scroll to the bottom of the page to the **Danger Zone**.
3. Click **Delete Web Service**.
4. Type the service name to confirm and click **Delete**.
5. *Result:* Web service container is deleted and compute billing ceases.

### Step 4: Deactivate or Delete Vercel Frontend
1. In the [Vercel Dashboard](https://vercel.com), navigate to `hirelens-demo`.
2. Go to **Settings** > Scroll down to the **Delete Project** section.
3. Click **Delete Project** and enter the project name to confirm.
4. *Result:* The project is removed from Vercel's edge network.

### Step 5: Verify Account Billing Status
1. Check the **Billing** tab in Render:
   - Ensure active services count is `0`.
   - Confirm current invoice reflects only the pro-rated consumption for the demo period (under $3.50 if Starter/Basic was used, or $0.00 if Free tier was used).
2. Check Vercel account:
   - Confirm zero paid add-ons or running team resources.

---

## 5. Summary & Recommendation

For the Dev Week 2 evaluation:
- **Recommended Strategy:** Deploy using **Option B (Starter Web Service + Basic PostgreSQL)** for the ~7 days of evaluator review. The total cost will be approximately **$3.25**, which guarantees zero cold-start frustration for judges and reliable, always-on performance.
- **Teardown Commitment:** Once evaluation scores are finalized, execute the 5-minute teardown checklist above to completely wipe all cloud resources with zero ongoing liability.
