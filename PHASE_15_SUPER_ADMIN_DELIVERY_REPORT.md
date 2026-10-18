# HireLens AI — Phase 15: Global Super Admin & Agency Admin Delivery Report

**System:** HireLens AI Platform  
**Target Workspace:** `D:\HireLens`  
**Execution Date:** October 17, 2026  
**Status:** IMPLEMENTED, TESTED, AND VERIFIED  
**Alembic Head:** `9c0d1e2f3a4b (head)`  

---

## 1. Executive Summary

Phase 15 delivers the final governance, operational control plane, and administrative experience for HireLens AI. Prior to Phase 15, platform operators lacked a unified cross-tenant administration console to monitor system-wide telemetry, manage tenant subscriptions, suspend delinquent accounts, and query cross-agency audit events. Furthermore, the agency-level settings console required completion to enable self-service team member management, recruiter invitation lifecycles, and hiring KPI overviews.

With Phase 15, HireLens AI completes its enterprise architecture with:
1. **Global Super Admin Dashboard (`/admin`):** Guarded strictly by the `PLATFORM_SUPER_ADMIN` privilege (`User.is_platform_admin == True`), providing platform operators with global telemetry (agencies, users, jobs, candidates, MRR/ARR), tenant suspension/reactivation workflows with immutable audit logging, cross-tenant security audit event explorer, and deep system infrastructure health probes.
2. **Completed Agency Administration Workspace (`/settings`):** Enhanced multi-tab organization management console for agency OWNERs and ADMINs featuring hiring performance KPIs, member management (invitations, role assignments, activation toggles), organization preferences, and outbound email delivery audits.
3. **Automated Celery Beat Schedulers:** Periodic background task orchestration for daily subscription renewals, hourly trial expirations, and daily data retention compliance sweeps.
4. **Structured Production Logging:** Sanitized JSON log format (`StructuredJSONFormatter`) redacting sensitive credentials and keys.
5. **Operational Probes:** Liveness (`/health/live`) and Readiness (`/health/ready`) probes for container orchestration.

---

## 2. Capabilities Delivered

### 2.1 Global Super Admin Control Plane (`backend/app/api/v1/endpoints/platform.py` & `frontend/app/(dashboard)/admin/page.tsx`)
- **Strict Server-Side Authorization:** Every platform endpoint enforces `require_platform_admin`. Regular agency `OWNER` or `ADMIN` users receive HTTP 403 Forbidden.
- **Global KPI Telemetry (`GET /api/v1/platform/overview`):**
  - Total registered agencies (active vs. suspended counts).
  - Total users and active recruiters.
  - Active jobs, total candidates, applications, interviews, and parsed resumes.
  - Subscription breakdown by tier (`FREE`, `STARTER`, `PROFESSIONAL`, `BUSINESS`, `ENTERPRISE`) and status (`ACTIVE`, `TRIALING`, `PAST_DUE`, `CANCELED`, `EXPIRED`).
  - Financial intelligence: MRR (INR and USD), ARR (INR and USD), Gross Revenue, and total paid invoices count.
  - System health indicator.
- **Tenant Directory & Inspection (`GET /api/v1/platform/agencies` & `GET /api/v1/platform/agencies/{id}`):**
  - Paginated agency roster with keyword search (name, slug, domain) and status filtering (`ACTIVE`, `SUSPENDED`).
  - In-depth tenant inspector displaying agency metadata, user roster, active subscription entitlements, billing profile, GSTIN, and recent invoices.
- **Tenant Lifecycle Governance (`PATCH /api/v1/platform/agencies/{id}/status`):**
  - Capability to suspend or reinstate an agency tenant.
  - Enforces mandatory justification reason logged directly into `SecurityAuditEvent` under `ADMIN_ACTION` (severity `HIGH`).
  - Once suspended, all non-platform users belonging to that agency are immediately rejected at the dependency layer (`get_current_user` raises HTTP 403: "Agency is inactive or not found").
- **Cross-Tenant Audit Explorer (`GET /api/v1/platform/audit-logs`):**
  - Searchable event log aggregating `SecurityAuditEvent` records across all agencies.
  - Filter by event category, severity, action, and keyword search.
  - Sanitized details view with PII and credential redaction.
- **Deep Infrastructure Probes (`GET /api/v1/platform/health`):**
  - Relational database: executes `SELECT 1` and reports query execution latency in milliseconds.
  - Redis / Celery: tests broker reachability and ping response.
  - Storage volume: verifies directory write-ability and reports free disk space in megabytes.

### 2.2 Completed Agency Administration Workspace (`frontend/app/(dashboard)/settings/page.tsx` & `backend/app/api/v1/endpoints/agency.py`)
- **Agency Overview Tab:**
  - Executive hiring metrics: Active Jobs, Talent Repository size, Pipeline Ingests, and Scheduled Interviews for current month.
  - Subscription summary displaying plan tier, billing interval, and renewal period.
  - Soft quota warning banners alerting owners when any resource usage crosses 80%.
- **Team & Recruiter Management Tab:**
  - Recruiter roster showing name, email, role badge, and active status.
  - "Invite Member" modal creating secure, time-limited invitation tokens with configurable roles (`ADMIN`, `RECRUITER`, `VIEWER`).
  - Member role management (OWNERs can reassign roles; demoting the primary owner is strictly prohibited).
  - Active/Inactive toggle enabling owners to deactivate departing recruiters without deleting historical attribution.
  - Safety guards: Owners cannot deactivate themselves or the primary agency owner.
  - Pending invitations list with one-click revocation.
- **Preferences & Timezone Tab:**
  - Global dispatch toggle for transactional emails.
  - Granular toggles for interview confirmations, pipeline status alerts, and candidate updates.
  - Timezone selector defaulting to `Asia/Kolkata` (IST, UTC+05:30).
- **Email Delivery Logs Tab:**
  - Filterable audit table of all outbound notification attempts with attempt counts and error details.
  - Manual retry capability for failed or dead-letter dispatches.

---

## 3. Security Architecture & Boundary Verification

1. **Privilege Boundary Separation:** Platform Super Admin status is controlled exclusively by `User.is_platform_admin == True`. It is completely decoupled from tenant-level `UserRole` (`OWNER`, `ADMIN`, `RECRUITER`, `VIEWER`).
2. **Tenant Suspension Enforcement:** Verified in `test_platform_agency_suspension_and_reactivation_with_audit`. Suspending an agency immediately prevents all recruiters of that agency from making authenticated requests, while platform administrators retain access.
3. **Idempotency & Audit Trails:** Every administrative suspension, reactivation, and entitlement override produces an immutable `SecurityAuditEvent` entry with timestamp, actor email, and justification reason.

---

## 4. Acceptance Signoff

All Phase 15 deliverables have been implemented, verified through automated integration tests, and certified ready for production deployment.
