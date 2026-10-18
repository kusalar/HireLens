# HireLens AI — Phase 15: Final Production Launch Checklist

**System:** HireLens AI Platform  
**Target Workspace:** `D:\HireLens`  
**Current Date:** October 17, 2026  
**Final Status:** PRODUCTION LAUNCH READY  

---

## 1. Launch Readiness Scorecard

| Area | Criterion | Verification Method | Status |
|---|---|---|---|
| **Architecture** | Single Alembic migration head | `alembic heads` -> `9c0d1e2f3a4b (head)` | **PASSED** |
| **Backend Quality** | Comprehensive regression suite | 188 passed, 5 skipped (external PG), 0 failed | **PASSED** |
| **Frontend Quality** | Next.js 14 production build | 29/29 static pages, 0 errors, 0 warnings | **PASSED** |
| **Multi-Tenancy** | Cross-tenant data isolation | Tested via automated cross-agency tests | **PASSED** |
| **Super Admin** | Platform vs. Agency Admin privilege separation | Guarded by `User.is_platform_admin == True` | **PASSED** |
| **SaaS Billing** | Dual payment gateways (Razorpay + Stripe + Mock) | Cryptographic signature verification enforced | **PASSED** |
| **Tax Compliance** | Indian GST 18% & immutable invoices | Sequential `HL-YYYYMM-XXXX` invoice numbering | **PASSED** |
| **Core AI Logic** | Deterministic candidate matching engine | Phase 4 algorithms preserved without regression | **PASSED** |
| **Human in Loop** | Recruiter workflow approvals | Phase 11 approval gates preserved | **PASSED** |
| **Probes & Health** | Container liveness and readiness | `/health/live`, `/health/ready`, `/platform/health` | **PASSED** |
| **Schedulers** | Periodic background jobs | Celery Beat configured for renewal, trial, retention | **PASSED** |

---

## 2. Pre-Launch Configuration Checklist

Before pointing production DNS to the live deployment:

### 2.1 Cryptographic & Security Secrets
- [ ] Generate production `SECRET_KEY` (64-character random hex).
- [ ] Generate production `TOKEN_ENCRYPTION_KEY` (32-byte URL-safe base64 for AES-256 Fernet).
- [ ] Configure `BACKEND_CORS_ORIGINS` with the exact production domain (e.g. `https://hirelens.ai`).
- [ ] Verify `ENABLE_OCR` is enabled if Tesseract OCR is installed in the worker container.

### 2.2 Payment Gateway Live Credentials
- [ ] **Razorpay (India / INR):**
  - Set live `RAZORPAY_KEY_ID` (`rzp_live_...`).
  - Set live `RAZORPAY_KEY_SECRET`.
  - Set live `RAZORPAY_WEBHOOK_SECRET` matching the registered endpoint:  
    `https://api.hirelens.ai/api/v1/billing/webhooks/razorpay`.
- [ ] **Stripe (International / USD):**
  - Set live `STRIPE_PUBLISHABLE_KEY` (`pk_live_...`).
  - Set live `STRIPE_SECRET_KEY` (`sk_live_...`).
  - Set live `STRIPE_WEBHOOK_SECRET` (`whsec_...`) matching:  
    `https://api.hirelens.ai/api/v1/billing/webhooks/stripe`.

### 2.3 Calendar Integrations (Phase 9)
- [ ] Submit Google OAuth app verification for Google Calendar API scopes.
- [ ] Register Microsoft Azure App Registration for Microsoft Graph Calendar scopes.

### 2.4 Transactional Email Delivery (Phase 7)
- [ ] Switch `EMAIL_PROVIDER="smtp"` from `console`/`mock`.
- [ ] Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, and `EMAILS_FROM_EMAIL`.

---

## 3. Go-Live Runbook

1. **Step 1: Start Production Database & Broker**
   ```bash
   docker compose up -d postgres redis
   ```
2. **Step 2: Run Alembic Database Migrations**
   ```bash
   docker compose run --rm backend alembic upgrade head
   ```
3. **Step 3: Seed Default SaaS Subscription Plans**
   Default plans (`FREE`, `STARTER`, `PROFESSIONAL`, `BUSINESS`, `ENTERPRISE`) seed automatically on first plan catalog request.
4. **Step 4: Launch Web & Background Worker Services**
   ```bash
   docker compose up -d backend celery_worker celery_beat frontend
   ```
5. **Step 5: Verify Operational Probes**
   - Check Liveness: `curl -f http://localhost:8000/health/live`
   - Check Readiness: `curl -f http://localhost:8000/health/ready`
6. **Step 6: Provision Initial Platform Super Administrator**
   Connect to the production database and set `is_platform_admin = True` on the initial platform operator user:
   ```sql
   UPDATE users SET is_platform_admin = TRUE WHERE email = 'superadmin@hirelens.ai';
   ```
7. **Step 7: Verify Super Admin Console**
   Log into `https://hirelens.ai/admin` and verify global KPI telemetry and infrastructure probe indicators.

---

## 4. Post-Launch Monitoring Guidelines

1. **Database Query Latency:** Monitor `/api/v1/platform/health` for database latency spikes (>100ms).
2. **Celery Task Queues:** Verify `celery_worker` concurrency and dead-letter count in `EmailDeliveryLog`.
3. **Webhook Replay Protection:** Monitor `PaymentWebhookEvent` to confirm duplicate webhook rejections remain 0 errors.
4. **Security Audit Log Explorer:** Review `/admin` cross-tenant audit events daily for unexpected administrative privilege changes.

---

## 5. Final Signoff

HireLens AI Phase 15 development and system integration are complete. The platform is ready for commercial SaaS deployment.
