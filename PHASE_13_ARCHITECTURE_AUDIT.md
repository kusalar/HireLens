# HireLens AI — Phase 13: Architecture & Security Governance Audit
**Enterprise Security, Compliance & Governance Workspace**

**Project:** HireLens AI  
**Workspace:** `D:\HireLens`  
**Date:** October 2026  
**Author:** Principal Security Architect, Senior Backend Engineer, Data Protection Officer, Application Security Auditor  
**Status:** Audit Completed & Approved for Implementation  
**Current Migration Head:** `7a8b9c0d1e2f` (Phase 12)

---

## 1. Executive Summary & Objective

Phase 13 establishes the enterprise security, compliance, data protection, and governance tier for HireLens AI. While Phases 1–12 introduced multi-tenancy, candidate management, deterministic matching, interview scheduling, notifications, analytics, calendar integration, Copilot assistance, workflow automation, and predictive forecasting, Phase 13 delivers the unified **Enterprise Security, Compliance & Governance Workspace** at `/settings/security`.

### Primary Objectives:
1. **Security Event & Unified Audit Center:** Aggregate, correlate, and inspect all security-relevant platform actions (auth events, credential changes, role modifications, sensitive candidate data views/exports, administrative operations) with strict immutability, pagination, and filtering.
2. **Session & Access Management:** Implement a real server-side session registry tracking device, IP, user-agent, last activity, and active status, enabling granular self-revocation, agency-wide administrative revocation, and global logout while maintaining 100% backward compatibility with existing JWT authentication.
3. **Candidate Privacy & Consent Management:** Record explicit consent versioning, purposes, and withdrawal histories; manage data subject requests (access, rectification, deletion/anonymization) with legal-hold exemptions that preserve statistical pipeline and audit integrity.
4. **AI Governance & Usage Controls:** Enforce agency-wide AI provider policies (permitted providers, token ceilings, cost limits, safety filters) and maintain auditable usage accounting (tokens, latency, cost, fallback events) across all Copilot and predictive features.
5. **Data Retention & Lifecycle Governance:** Provide configurable data retention policies per agency across candidates, resumes, interviews, notifications, audit logs, and AI chats, featuring safe dry-run previews, legal-hold safeguards, and idempotent Celery background execution.

---

## 2. Comprehensive Audit of Existing Phases 1–12 Assets

To maintain architectural cohesion and avoid redundant infrastructure, Phase 13 audits and reuses existing platform components:

| Component / Service | Existing Capabilities | Phase 13 Reuse & Synergy |
|---|---|---|
| **`AuditLog`** (`models/entities.py`) | Basic agency-scoped activity log (action, resource_type, resource_id, ip_address). | Reused as a foundational entity. Supplemented by unified `SecurityAuditEvent` for enterprise-grade security classification (severity, category, actor metadata). |
| **`CopilotAuditLog`** (`models/copilot.py`) | Logs AI chat/prompt token usage, duration, and action type per user turn. | Serves as raw telemetry source for the new aggregated `AIUsageLog` and AI governance dashboard. |
| **`WorkflowAuditLog`** (`models/workflow.py`) | Logs automated workflow step transitions and rule triggers. | Correlated into the unified security audit explorer for compliance reviews. |
| **`EmailDeliveryLog`** (`models/notification.py`) | Tracks notification recipient, delivery status, and timestamps. | Referenced during communication retention sweeps and consent withdrawal investigations. |
| **`CalendarSyncLog`** (`models/calendar.py`) | Audits inbound/outbound external calendar sync events. | Integrated into external integration audit trails. |
| **JWT & OAuth2** (`core/security.py`, `api/deps.py`) | Issues and validates access/refresh tokens. | Enhanced with server-side session validation (`UserSession.id` / `sid` claim) and revocation checks without breaking existing stateless token verification. |
| **Celery & Redis** (`core/celery_app.py`) | Asynchronous and scheduled task execution. | Schedules automated data retention evaluations (`evaluate_retention_policies_task`) and session garbage collection. |
| **Timezone Architecture** (`core/timezone.py`) | Canonical `Asia/Kolkata` (IST) with UTC database persistence. | Enforced across all audit timestamps, session expirations, consent histories, and retention schedules. |

---

## 3. Gap Analysis & Architectural Enhancements

### Gap 1: Stateless JWT Revocation vs. Enterprise Session Control
- **Issue:** Standard stateless JWTs cannot be revoked mid-flight before their expiration timestamp without a server-side state mechanism.
- **Solution:** Introduce `UserSession` model. When tokens are minted or refreshed, a session identifier (`sid`) is embedded in the payload. `get_current_user` validates that the session record exists and `is_active == True`. If revoked, requests fail immediately with `401 Unauthorized`. For tokens without a `sid` (such as legacy test tokens), a global user-level timestamp `tokens_revoked_before` provides seamless backward compatibility.

### Gap 2: Ad-Hoc Consent vs. Auditable Data Protection
- **Issue:** Candidate consent was previously implicit during application submission without versioned purpose tracking or withdrawal history.
- **Solution:** Introduce `CandidateConsentRecord` capturing consent type, policy version, purpose, timestamp, and withdrawal events. Introduce `CandidatePrivacyRequest` to handle formal GDPR/DPDP-style access, correction, and deletion requests with administrative approval and legal-hold protection.

### Gap 3: Unmonitored AI Token Consumption & Unrestricted Providers
- **Issue:** Recruiters could invoke Copilot and predictive endpoints without agency-level budget limits or provider restrictions.
- **Solution:** Introduce `AIGovernancePolicy` (agency-scoped rules defining allowed providers, max tokens per request, monthly budget, and mandatory safety filters) and `AIUsageLog` for multi-provider telemetry tracking.

### Gap 4: Indefinite Data Accumulation vs. Configurable Retention
- **Issue:** Resumes, candidate records, and interview notes accumulated indefinitely without lifecycle management.
- **Solution:** Introduce `DataRetentionPolicy` (supporting `ANONYMIZE`, `ARCHIVE`, and `DELETE` actions per data category) with mandatory **Dry-Run Preview** functionality and legal-hold exemptions before permanent execution.

---

## 4. Database Schema Design (Phase 13 Migration)

The schema additions are isolated in `backend/app/models/governance.py` and linked via foreign keys with `agency_id` tenant isolation:

1. **`UserSession`**:
   - `id` (UUID PK, referenced as `sid`)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `user_id` (UUID FK -> `users.id`, index=True)
   - `session_token_hash` (String(64), index=True)
   - `ip_address` (String(50))
   - `user_agent` (String(500))
   - `device_info` (String(100))
   - `is_active` (Boolean, default True, index=True)
   - `created_at`, `last_activity_at`, `revoked_at` (DateTime TZ)
   - `revocation_reason` (String(255))

2. **`SecurityAuditEvent`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `actor_user_id` (UUID FK -> `users.id`, nullable, index=True)
   - `actor_email` (String(255))
   - `event_category` (Enum `AuditEventCategory`: `AUTHENTICATION`, `AUTHORIZATION`, `DATA_ACCESS`, `DATA_EXPORT`, `ADMIN_ACTION`, `SECURITY_EVENT`, `PRIVACY_OP`)
   - `severity` (Enum `AuditSeverity`: `LOW`, `MEDIUM`, `HIGH`, `CRITICAL`, index=True)
   - `action` (String(100), index=True)
   - `resource_type` (String(100), index=True)
   - `resource_id` (String(100), nullable)
   - `details_json` (Text)
   - `ip_address`, `user_agent` (String)
   - `created_at` (DateTime TZ, default utc_now)

3. **`CandidateConsentRecord`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `candidate_id` (UUID FK -> `candidates.id`, index=True)
   - `consent_type` (Enum `ConsentType`: `DATA_PROCESSING`, `COMMUNICATION`, `BACKGROUND_CHECK`, `THIRD_PARTY_SHARING`)
   - `is_granted` (Boolean, default True)
   - `policy_version` (String(50))
   - `purpose` (String(255))
   - `channel` (String(50))
   - `granted_at`, `withdrawn_at` (DateTime TZ)
   - `metadata_json` (Text)

4. **`CandidatePrivacyRequest`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `candidate_id` (UUID FK -> `candidates.id`, nullable, index=True)
   - `request_type` (Enum `PrivacyRequestType`: `DATA_ACCESS`, `DATA_CORRECTION`, `DATA_DELETION`, `RESTRICT_PROCESSING`, `CONSENT_WITHDRAWAL`)
   - `status` (Enum `PrivacyRequestStatus`: `PENDING`, `IN_REVIEW`, `COMPLETED`, `REJECTED`, `LEGAL_HOLD`, index=True)
   - `requested_by_email` (String(255))
   - `request_details` (Text)
   - `resolution_notes` (Text)
   - `has_legal_hold` (Boolean, default False)
   - `legal_hold_reason` (Text)
   - `handled_by_user_id` (UUID FK -> `users.id`, nullable)
   - `created_at`, `resolved_at` (DateTime TZ)

5. **`AIGovernancePolicy`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, unique=True, index=True)
   - `allowed_providers_json` (Text, default `["OLLAMA", "HOSTED_OPEN_WEIGHT"]`)
   - `max_tokens_per_request` (Integer, default 4000)
   - `monthly_token_budget` (Integer, default 500000)
   - `require_pii_masking` (Boolean, default True)
   - `safety_filter_enabled` (Boolean, default True)
   - `updated_by_user_id` (UUID FK -> `users.id`, nullable)
   - `created_at`, `updated_at` (DateTime TZ)

6. **`AIUsageLog`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `user_id` (UUID FK -> `users.id`, nullable, index=True)
   - `feature_name` (String(100), index=True)
   - `provider` (String(50), index=True)
   - `model` (String(100))
   - `prompt_tokens`, `completion_tokens`, `total_tokens` (Integer)
   - `latency_ms` (Float)
   - `estimated_cost_usd` (Float)
   - `is_fallback` (Boolean, default False)
   - `fallback_reason` (String(255))
   - `safety_filter_triggered` (Boolean, default False)
   - `created_at` (DateTime TZ)

7. **`DataRetentionPolicy`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `data_category` (Enum `RetentionCategory`: `CANDIDATE_RECORDS`, `RESUME_DOCUMENTS`, `INTERVIEW_RECORDS`, `NOTIFICATIONS`, `AUDIT_LOGS`, `AI_CONVERSATIONS`, index=True)
   - `retention_days` (Integer, default 365)
   - `action_type` (Enum `RetentionAction`: `ANONYMIZE`, `ARCHIVE`, `DELETE`)
   - `is_enabled` (Boolean, default False)
   - `exempt_legal_holds` (Boolean, default True)
   - `last_executed_at` (DateTime TZ, nullable)
   - `created_at`, `updated_at` (DateTime TZ)

8. **`RetentionExecutionLog`**:
   - `id` (UUID PK)
   - `agency_id` (UUID FK -> `agencies.id`, index=True)
   - `policy_id` (UUID FK -> `data_retention_policies.id`, ondelete="CASCADE")
   - `execution_type` (Enum `RetentionExecutionType`: `DRY_RUN`, `EXECUTE`)
   - `records_scanned`, `records_affected`, `records_exempted` (Integer, default 0)
   - `status` (Enum `RetentionStatus`: `COMPLETED`, `FAILED`, `CANCELLED`)
   - `executed_by_user_id` (UUID FK -> `users.id`, nullable)
   - `execution_summary_json` (Text)
   - `created_at` (DateTime TZ)

---

## 5. Security & Privacy Safeguards

1. **Audit Immutability:** Audit records have no `UPDATE` or `DELETE` API endpoints. Once committed, rows cannot be mutated or purged by standard users or recruiters.
2. **PII Protection in Audit Records:** Passwords, authentication tokens, session secrets, and resume text are strictly filtered before serializing into `details_json`.
3. **Anonymization Integrity:** When executing candidate deletion/anonymization, the candidate's personal data (name, email, phone, location) is replaced with an anonymous pseudonym (`Candidate-[ID]`), while application stage transitions, match metrics, and historical counts remain intact to preserve statistical reporting.
4. **Legal Hold Exemption:** Any candidate or application marked with an active `has_legal_hold == True` is skipped during retention sweeps, with exemptions logged in the immutable execution report.

---

## 6. Audit Conclusion & Implementation Roadmap

The existing architecture provides strong multi-tenant isolation, clean Alembic versioning, and well-structured Celery queues. Phase 13 introduces the comprehensive governance workspace without disrupting any Phase 1–12 capabilities.

**Stage 1 Audit is hereby concluded. Proceed to Stage 2: Database Models & Migrations.**
