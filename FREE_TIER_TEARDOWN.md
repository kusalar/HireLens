# HireLens AI — ₹0 Free-Tier Backup & Teardown Runbook

**Target Architecture:** Vercel Hobby + Render Free + Neon Free  
**Hosting Cost:** **₹0 / $0.00**  
**Decommission Goal:** Clean removal of all cloud resources after Dev Week 2 evaluation concludes.  

---

## 1. Overview

Because this deployment targets strictly **₹0 hosting cost** without credit cards or auto-renewing subscriptions, there is zero danger of unexpected recurring charges.

However, to maintain clean cloud hygiene and safeguard any demonstration data, follow this structured decommission process once the Dev Week 2 judging period concludes.

---

## 2. Phase 1: Database Snapshot Export (Optional Backup)

If you wish to retain a copy of the candidate data, jobs, and pre-computed match evidence created during the demo, export a database dump using the **Neon Direct Connection URL**.

### Backup Command (from Local Terminal)

```powershell
# Windows PowerShell
$NEON_URL = "postgresql://neondb_owner:YOUR_NEON_PASSWORD@ep-plain-forest-a57q8f94.us-east-2.aws.neon.tech/neondb?sslmode=require"

# Export schema and data using pg_dump
pg_dump --clean --if-exists --no-owner --no-privileges "$NEON_URL" > "d:\HireLens\neon_demo_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
```

*Or via Docker (if pg_dump is not installed locally):*
```bash
docker run --rm -v "D:\HireLens:/backup" postgres:16 pg_dump \
  --clean --if-exists --no-owner --no-privileges \
  "postgresql://neondb_owner:YOUR_NEON_PASSWORD@ep-plain-forest-a57q8f94.us-east-2.aws.neon.tech/neondb?sslmode=require" \
  -f "/backup/neon_demo_backup.sql"
```

---

## 3. Phase 2: Decommission Cloud Services (5-Minute Teardown)

### Step 1: Delete Neon PostgreSQL Project
1. Log into your [Neon Dashboard](https://console.neon.tech).
2. Select your `hirelens-demo` project.
3. In the left navigation, click **Project settings**.
4. Scroll to the **Danger zone** at the bottom.
5. Click **Delete project**.
6. Type the confirmation string and click **Delete**.
7. *Result:* All database storage and compute endpoints are instantly destroyed.

### Step 2: Delete Render Web Service
1. Log into your [Render Dashboard](https://dashboard.render.com).
2. Click on the `hirelens-api` Web Service.
3. In the left menu, select **Settings**.
4. Scroll down to the **Danger Zone**.
5. Click **Delete Web Service**.
6. Type `hirelens-api` to confirm and click **Delete**.
7. *Result:* Container is terminated and public API endpoint is removed.

### Step 3: Delete Vercel Project
1. Log into your [Vercel Dashboard](https://vercel.com).
2. Select the `hirelens-demo` project.
3. Navigate to **Settings** > Scroll to **Delete Project**.
4. Click **Delete Project**, type the project name, and confirm.
5. *Result:* Frontend is removed from Vercel's global edge network.

---

## 4. Phase 3: Final Account Verification

1. **Neon Console:** Confirm project count is `0`.
2. **Render Dashboard:** Confirm active services count is `0`.
3. **Vercel Dashboard:** Confirm project list does not contain `hirelens-demo`.
4. **Billing Status:** Affirm ₹0 / $0.00 total spend across all three provider dashboards.
