# Phase 14: Mandatory Pre-Implementation Architecture Audit
## Enterprise SaaS Monetization, Subscription, Billing & Usage Management

**Document Status:** Complete & Verified Pre-Implementation  
**System:** HireLens AI Platform  
**Target Workspace:** `D:\HireLens`  
**Current Date:** October 17, 2026  
**Timezone Standard:** Asia/Kolkata (IST, UTC+05:30) with UTC database persistence  
**Current Alembic Head:** `8b9c0d1e2f3a` (Phase 13 Enterprise Security & Governance)

---

## 1. Executive Summary & Audit Objectives

Phase 14 transitions HireLens AI from an internal recruitment SaaS platform into a commercially deployable, multi-tenant enterprise product with:
1. Automated subscription lifecycle management (FREE, STARTER, PROFESSIONAL, BUSINESS, ENTERPRISE).
2. Dual-provider payment infrastructure: Razorpay for India (INR / ₹) with GST compliance and Stripe for international markets (USD / $), supported by a robust Mock payment adapter for local and automated testing.
3. Centralized feature entitlements and atomic usage metering that strictly protects operational integrity while preventing revenue leakage.
4. Immutable billing invoices with GSTIN calculations, credit notes, refunds, and downloadable PDF/receipt representations.
5. Organization-level billing ownership (agency level) coupled with an isolated platform-administration governance layer.
6. A unified responsive billing workspace at `/settings/billing`.

---

## 2. Audit of Existing Infrastructure & Reusable Assets

A comprehensive audit was performed across all 13 existing phases to identify existing data models, business services, background tasks, and API boundaries.

### 2.1 Multi-Tenancy & Agency Ownership
- **Model:** `Agency` in `app/models/entities.py`.
- **Existing Fields:** `id` (GUID), `name`, `slug`, `domain`, `country` (defaults to 'IN'), `is_active`, `created_at`, `updated_at`.
- **Multi-Tenant Boundary:** Every business query scopes by `agency_id`.
- **Phase 14 Strategy:** Subscriptions, billing profiles, payment methods, quotas, and invoices belong strictly to `Agency`, NOT individual recruiters. When an agency's subscription changes, all recruiters in that agency inherit the plan's entitlements.

### 2.2 Roles & RBAC (`app/models/enums.py` & `app/api/deps.py`)
- **Existing User Roles:** `OWNER`, `ADMIN`, `RECRUITER`, `VIEWER`.
- **Agency-Level Billing Rights:** Only `OWNER` and `ADMIN` can view billing information, initiate checkouts, switch plans, or manage payment profiles. `RECRUITER` and `VIEWER` have read-only or no access.
- **Platform-Level Administration:** Distinct from agency OWNER/ADMIN. To prevent privilege confusion, platform administration requires `is_platform_admin: bool = Column(Boolean, default=False)` on `User` and a dedicated FastAPI dependency `require_platform_admin`. Public self-registration for platform admins is strictly prohibited.

### 2.3 Metering & Consumption Foundations
Existing models already track granular operational activity, which will feed into the usage metering engine:
- **AI Telemetry (`app/models/governance.py` - `AIUsageLog`):** Captures `prompt_tokens`, `completion_tokens`, `total_tokens`, `feature_name`, `provider`, and `estimated_cost_usd` per agency.
- **Transactional Communication (`app/models/notification.py` - `EmailDeliveryLog`):** Tracks email dispatch counts and attempts per agency.
- **Resume Processing (`app/models/resume.py` - `Resume`):** Records file sizes (`file_size_bytes`) and processing runs per agency.
- **Application Pipeline (`app/models/application.py` - `Application`):** Tracks candidate application transitions per agency.
- **Workflow Automation (`app/models/workflow.py` - `WorkflowRun`):** Records workflow rule executions per agency.
- **Calendar Integrations (`app/models/calendar_integration.py` - `CalendarSyncLog`):** Records sync events and calendar booking volume.
- **Interviews (`app/models/interview.py` - `Interview`):** Records interview scheduling volume.
- **Phase 14 Strategy:** Instead of fragmenting quota checks across disparate services, Phase 14 introduces a **Centralized Entitlement & Metering Service** (`EntitlementService`). Operations request quota reservations or report atomic increments.

### 2.4 Celery & Async Infrastructure (`app/core/celery_app.py`)
- **Existing Workers:** Autodiscovers `app.tasks.resume_tasks`, `notification_tasks`, `calendar_tasks`, `workflow_tasks`, `predictive_tasks`, `governance_tasks`.
- **Scheduled Sweeps:** Celery Beat already executes retention evaluations.
- **Phase 14 Reusability:** Phase 14 adds `app.tasks.billing_tasks` for:
  - Daily subscription renewal checks.
  - Trial expiration sweeps.
  - Grace-period and past-due deactivation.
  - Monthly quota reset at billing-period boundaries.
  - Invoice generation on successful subscription renewal.

### 2.5 Security, Governance & Audit Integration (Phase 13)
- **Security Audit Events:** Phase 13 created `SecurityAuditEvent`. All billing events (plan upgrades, cancellations, refunds, manual quota overrides, and webhook receptions) will log to `SecurityAuditEvent` under `ADMIN_ACTION` or `SECURITY_EVENT`.
- **Strict Compliance Boundary:** As mandated, **no quota exhaustion may ever block critical security, privacy (GDPR/DPDP erasure requests), legal-hold, or compliance data exports**.

---

## 3. Subscription Tier Architecture & Entitlement Matrix

To balance flexibility and deterministic enforcement, standard subscription tiers are configured with default limits while permitting agency-specific entitlement overrides:

| Plan Dimension | FREE | STARTER | PROFESSIONAL | BUSINESS | ENTERPRISE |
|---|---|---|---|---|---|
| **Monthly Price (INR / ₹)** | ₹0 | ₹4,999 | ₹14,999 | ₹39,999 | ₹99,999 |
| **Annual Price (INR / ₹)** | ₹0 | ₹47,990 | ₹143,990 | ₹383,990 | ₹959,990 |
| **Monthly Price (USD / $)** | $0 | $69 | $199 | $499 | $1,299 |
| **Annual Price (USD / $)** | $0 | $660 | $1,910 | $4,790 | $12,470 |
| **Max Active Jobs** | 2 | 10 | 30 | 100 | Unlimited (-1) |
| **Max Recruiter Seats** | 1 | 3 | 10 | 30 | Unlimited (-1) |
| **Candidates / Month** | 50 | 500 | 2,500 | 10,000 | Unlimited (-1) |
| **Resume Storage (MB)** | 250 MB | 2,500 MB | 15,000 MB | 60,000 MB | Unlimited (-1) |
| **AI Tokens / Month** | 50,000 | 500,000 | 2,500,000 | 10,000,000 | Custom / 50M |
| **AI Copilot Access** | Basic | Standard | Advanced | Full Access | Priority Dedicated |
| **Interviews / Month** | 10 | 100 | 500 | 2,000 | Unlimited (-1) |
| **Workflows / Month** | 0 | 50 | 500 | 3,000 | Unlimited (-1) |
| **Analytics Access** | Basic | Standard | Advanced (P8) | Full (P8+P12) | Full (Custom) |
| **Predictive AI (P12)** | ❌ No | ❌ No | ❌ No | ✅ Yes | ✅ Yes |
| **Calendar Sync (P9)** | ❌ No | ✅ Google | ✅ Google+Outlook | ✅ All + Zoom | ✅ Dedicated SSO |
| **Gov & Retention (P13)** | Basic (30d) | 90d Logs | 365d Logs | Full Retention | Custom Compliance |

---

## 4. Payment Gateway Abstraction & Transaction Security

### 4.1 Payment Provider Abstraction
To support global SaaS deployment while ensuring seamless local automated testing, Phase 14 creates `PaymentGatewayProvider` with three concrete implementations:
1. **`RazorpayAdapter`:**
   - Currency: `INR`.
   - Capabilities: Razorpay Order Creation (`order_id`), Checkout verification using HMAC-SHA256 (`razorpay_order_id|razorpay_payment_id`), and Webhook signature verification (`X-Razorpay-Signature`).
   - India B2B Support: Captures Customer GSTIN, calculates CGST (9%) + SGST (9%) for intra-state or IGST (18%) for inter-state transactions.
2. **`StripeAdapter`:**
   - Currency: `USD` (and multi-currency support).
   - Capabilities: Stripe Checkout Session creation, Webhook signature verification (`Stripe-Signature` using tolerance-checked timestamp and secret), and customer payment method binding.
3. **`MockPaymentAdapter`:**
   - Purpose: Automated CI/CD and offline local development without external API keys.
   - Deterministic test transactions, signature simulation, refund handling, and simulated failure testing.

### 4.2 Security & Idempotency Safeguards
- **Zero Frontend Trust:** The frontend never confirms payments. A subscription is activated or renewed ONLY upon server-side signature verification or receipt of a cryptographically validated webhook.
- **Idempotency Keys (`idempotency_key`):** Every checkout session, webhook dispatch, and invoice generation uses an idempotency key to prevent double billing.
- **No PCI Data Storage:** Raw card numbers, expiry dates, CVVs, or gateway API secret keys are NEVER stored in the application database.
- **Credential Guards:** Live payment integration remains disabled (`PAYMENT_ENABLED = False`) unless valid Razorpay/Stripe secrets are detected in the environment.

---

## 5. Invoicing, GST & Financial Integrity

### 5.1 Sequential Invoice Numbering
- Format: `HL-INV-{YEAR}-{MONTH}-{SEQUENCE:05d}` (e.g. `HL-INV-2026-10-00042`).
- Guaranteed unique constraint on `(agency_id, invoice_number)`.

### 5.2 Indian Taxation Engine (GSTIN Compliance)
- If `agency.country == "IN"`:
  - Validates GSTIN format via regex: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`.
  - Determines state code from the first 2 digits of the GSTIN.
  - If state code matches HireLens corporate state code (e.g., `27` for Maharashtra or `29` for Karnataka): applies **CGST 9% + SGST 9%**.
  - If state code differs: applies **IGST 18%**.
- If international (`agency.country != "IN"`): 0% export of services with zero-rated tax classification.

### 5.3 Financial Immutability
- Invoices transition through `DRAFT` -> `ISSUED` -> `PAID` / `VOID` / `REFUNDED`.
- Once `PAID`, line items, taxes, and amounts become strictly immutable. Corrections require audited `CreditNote` and `RefundRecord` issuance.

---

## 6. Centralized Usage Metering & Quota Enforcement

### 6.1 Database-Level Concurrency Safety
- High-concurrency operations (e.g. 50 parallel resume uploads or AI requests) cannot rely on naive `read -> check -> write` application-layer loops.
- `UsageMeter` maintains `current_usage` with optimistic concurrency versioning (`version`) and atomic database-level increment expressions:
  ```python
  stmt = (
      update(UsageMeter)
      .where(and_(UsageMeter.id == meter.id, UsageMeter.current_usage + delta <= meter.hard_limit))
      .values(current_usage=UsageMeter.current_usage + delta, version=UsageMeter.version + 1)
      .returning(UsageMeter.current_usage)
  )
  ```
- If the hard limit would be breached, the transaction rolls back gracefully and raises `HTTP 402 Payment Required` or `HTTP 429 Quota Exceeded` with a structured payload detailing the exhausted resource, current limit, and upgrade URL.

### 6.2 Exempted Critical Operations
The following operations are explicitly exempt from quota blocking:
- Compliance and security log inspection (`/governance/*`).
- Candidate privacy requests (`/governance/privacy-requests`).
- Legal-hold enforcement.
- Data export under legal or compliance mandate.

---

## 7. Database Model Architecture (Phase 14 Proposed Models)

The following models will be created in `app/models/billing.py`:

1. `SubscriptionPlan`: Canonical catalog of plans, pricing, and default resource limits.
2. `AgencySubscription`: Active subscription link per agency, status (`ACTIVE`, `TRIALING`, `PAST_DUE`, `CANCELED`, `EXPIRED`), current billing period start/end, trial end, and payment method details.
3. `SubscriptionHistory`: Immutable audit log of all plan changes, activations, renewals, downgrades, and cancellations.
4. `FeatureEntitlement`: Agency-level entitlement matrix with feature flags and maximum quotas.
5. `EntitlementOverride`: Administrative overrides applied to specific agencies (e.g. promotional extra candidate quotas or beta feature access).
6. `UsageMeter`: Monthly aggregated meters per agency and resource category (`ACTIVE_JOBS`, `RECRUITERS`, `CANDIDATES_PROCESSED`, `RESUME_STORAGE_MB`, `AI_TOKENS`, `INTERVIEWS_SCHEDULED`, `WORKFLOW_RUNS`).
7. `UsageRecord`: Granular audit trail of individual quota consumption events with idempotency keys.
8. `PaymentTransaction`: Record of checkout sessions, gateway charges, amounts, currencies, fees, and gateway references.
9. `PaymentWebhookEvent`: Log of incoming webhooks with signature verification status and processing timestamps (prevents replay attacks).
10. `BillingInvoice`: Formal tax invoice with invoice number, billing details, subtotal, tax amount, total, and status.
11. `InvoiceLineItem`: Itemized details per invoice.
12. `CreditNote`: Financial adjustments and credit records against paid invoices.
13. `RefundRecord`: Gateway refund records with reason and transaction reference.
14. `AgencyBillingProfile`: Legal company name, billing contact email, address, tax ID (GSTIN), and currency preference.
15. `BillingAuditLog`: Specialized audit log for all financial, billing, and subscription operations.

---

## 8. Frontend Workspace Plan (`/settings/billing`)

A comprehensive, responsive billing dashboard will be created at `frontend/app/(dashboard)/settings/billing/page.tsx`:
- **Current Subscription Card:** Active plan badge, renewal date in IST, trial countdown (if active), and cancel/renew controls.
- **Usage & Quotas Dashboard:** Visual progress bars for Jobs, Recruiters, Candidates, Storage, AI Tokens, Interviews, and Workflows with warning thresholds (yellow at 80%, red at 95%).
- **Plan Comparison & Upgrade Modal:** Side-by-side pricing tier selector with annual/monthly toggle, features breakdown, and Checkout CTA.
- **Payment Method & Checkout Flow:** Seamless gateway modal with Razorpay / Stripe integration and mock fallback for testing.
- **Invoices & Receipts Table:** Downloadable invoice receipts, payment dates, GST breakdown, status badges, and transaction IDs.
- **Billing Profile Form:** Company legal name, billing address, and GSTIN management with live validation.

---

## 9. Migration & Pre-Implementation Verification Plan

1. **Schema Migration:** Create Alembic revision `9c0d1e2f3a4b_add_phase_14_enterprise_saas_billing_and_monetization_models.py` descending from `8b9c0d1e2f3a`.
2. **Reversibility Check:** Verify clean `alembic upgrade head` -> `alembic downgrade -1` -> `alembic upgrade head`.
3. **Single Head Verification:** Confirm single migration head.
4. **Pytest Coverage:** Build comprehensive tests in `tests/test_billing.py` covering all lifecycle states, webhook security, quota concurrency, GST math, and tenant isolation.
5. **Full Regression Test:** Verify all 167+ existing tests across Phases 1–13 pass without regression.
6. **Frontend Production Build:** Verify `npm run build` succeeds with 0 errors across 28+ static pages.

---
*Audit Completed. Ready to proceed to Stage 2: Database Models & Migrations.*
