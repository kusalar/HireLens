# HireLens AI — Phase 11: Pre-Implementation Architecture Audit
# Intelligent Recruitment Workflow Automation & Orchestration

**Document:** `PHASE_11_ARCHITECTURE_AUDIT.md`  
**Date:** 2026-10-17  
**Auditor:** Principal Software Architect, Senior Backend Engineer, AI Systems Engineer & Application Security Auditor  
**Project Workspace:** `D:\HireLens`  
**Current Baseline Status:** 138 backend tests passed, 4 skipped; Alembic head `5e6f7a8b9c0d`; Frontend production build 20/20 static pages generated cleanly.

---

## 1. Executive Summary & Objective

Phase 11 transforms HireLens AI from an AI-assisted recruitment SaaS into an **intelligent recruitment operations platform** capable of executing configurable, human-approved recruitment workflows.

### Core Guiding Principle
> **Automate repetitive operations, preserve human authority over hiring decisions.**

The system must automate notifications, recruiter follow-up task generation, calendar synchronization triggers, interview preparation briefs, and operational analytics events. Under **no circumstances** may automated workflows independently hire candidates, reject candidates, or transition application stages without authorized human approval.

---

## 2. Review of Phases 1–10 Architectural Foundations

| Phase | Capability Domain | Key Reusable Services / Models | Phase 11 Integration Role |
|---|---|---|---|
| **Phase 1** | Auth, RBAC & Multi-Tenancy | `User`, `Agency`, `app.core.rbac` (`RoleChecker`) | Enforce OWNER/ADMIN configuration rights; agency-level data shielding. |
| **Phase 2** | Jobs & Candidates | `Job`, `Candidate`, `JobRequirement` | Target entities for triggers and condition evaluations. |
| **Phase 3** | Resume Parsing & Extraction | `Resume`, `ResumeParseRun`, `ResumeProcessingStatus` | Trigger `RESUME_PROCESSED` on parsing completion. |
| **Phase 4** | Deterministic Candidate Matching | `JobMatchResult`, `MatchingService` | Immutable match scores evaluated in conditions (`match_score >= threshold`). |
| **Phase 5** | Application Pipeline | `Application`, `ApplicationStageHistory`, `ApplicationService` | Triggers for `APPLICATION_SUBMITTED`, `APPLICATION_STAGE_CHANGED`. |
| **Phase 6 & 6.1** | Interviews & Scheduling | `Interview`, `InterviewService`, `InterviewFeedback` | Triggers for `INTERVIEW_SCHEDULED`, `RESCHEDULED`, `COMPLETED`, `FEEDBACK_SUBMITTED`. |
| **Phase 7** | Communication & Outbox | `NotificationOutbox`, `NotificationService`, Celery outbox worker | Action: Dispatch candidate notifications via established transactional outbox. |
| **Phase 8** | Recruitment Intelligence | `AnalyticsService` | Action: Trigger analytics tracking events and compute deterministic workflow metrics. |
| **Phase 9** | Calendar & Integrations | `CalendarSyncJob`, `CalendarSyncService` | Action: Trigger calendar sync jobs via durable queue without duplicating providers. |
| **Phase 10** | AI Recruitment Copilot | `CopilotService`, `InterviewPrepResponse` | Action: Automatically generate interview preparation briefs upon scheduling. |

---

## 3. Inspection of Asynchronous & Integration Infrastructure

### 3.1 Celery & Redis Configuration (`app/core/celery_app.py`)
- **Broker / Backend:** Configured via `settings.CELERY_BROKER_URL` and `settings.CELERY_RESULT_BACKEND` (Redis).
- **Timezone:** Normalized to `UTC` with `enable_utc=True`.
- **Task Serialization:** Pure JSON (`task_serializer="json"`), prohibiting arbitrary pickle objects.
- **Time Limits:** Hard limit 300s (5m), soft limit 240s (4m).
- **Prefetch:** `worker_prefetch_multiplier=1` (optimal for concurrency safety).
- **Existing Autodiscovered Tasks:**
  - `app.tasks.resume_tasks`
  - `app.tasks.notification_tasks`
  - `app.tasks.calendar_tasks`
- **Phase 11 Addition:** Introduce `app.tasks.workflow_tasks` for delayed workflow execution, retry scheduling, step processing, and approval expiration sweeping.

### 3.2 Notification Outbox Pattern (`app/models/notification.py`)
- Employs `NotificationOutbox` with unique `idempotency_key`, `attempt_count`, `max_retries`, `next_retry_at`, and status tracking (`PENDING`, `PROCESSING`, `SENT`, `FAILED`, `DEAD_LETTER`).
- **Architectural Decision:** Workflow notification actions will **not** attempt immediate direct SMTP delivery. Instead, they will enqueue records into `NotificationOutbox` within the same database transaction, ensuring zero loss of communications during worker restarts.

### 3.3 Calendar Sync Infrastructure (`app/models/calendar.py` & `CalendarSyncService`)
- Durable asynchronous processing via `CalendarSyncJob` with retry policies and exponential backoff.
- **Architectural Decision:** Workflow calendar actions will call `CalendarSyncService.enqueue_sync_job()` rather than directly invoking external Google/Microsoft APIs, maintaining complete resilience against external downtime.

### 3.4 AI Copilot Integration (`app/services/copilot_service.py`)
- Provides `generate_interview_prep_brief()` with strict entity grounding and fallback to deterministic templates if AI models are unreachable.
- **Architectural Decision:** Workflow action `GENERATE_INTERVIEW_PREP` will invoke `CopilotService` asynchronously, attach the resulting brief to the interview record, and notify the assigned interviewers.

---

## 4. Current Database Schema & Migration Status

- **Alembic Migration Head:** `5e6f7a8b9c0d` (Single head, validated via `alembic heads`).
- **Preceding Phase 10 Migration:** `5e6f7a8b9c0d_add_phase_10_copilot_and_hiring_assistant_models.py`.
- **Existing Workflow Models:** **None** exist currently in the repository.
- **Phase 11 Target Migration:** Create new revision `6f7a8b9c0d1e` descending from `5e6f7a8b9c0d`.

---

## 5. Architectural Risks & Mitigation Strategies

### Risk 1: Violation of Human Hiring Authority (Unintended Autonomous Decisions)
- **Risk:** Automating application stage transitions (e.g., auto-advancing to "Selected" or auto-"Rejecting" candidates based on match score) could introduce algorithmic bias, legal liability, and lack of human oversight.
- **Mitigation:**
  - The workflow action engine strictly prohibits `STAGE_CHANGE`, `HIRE_CANDIDATE`, or `REJECT_CANDIDATE` actions.
  - Actions are restricted to: notification dispatch, recruiter follow-up task creation, interview preparation generation, calendar sync trigger, analytics logging, and human approval requests.
  - Any workflow step requesting sensitive operations must generate a `WorkflowApproval` item in the `/approvals` queue for human review.

### Risk 2: Arbitrary Code Execution via Dynamic Conditions
- **Risk:** Implementing user-configured rules using Python `eval()`, `exec()`, or custom expression parsers could lead to Remote Code Execution (RCE) or resource exhaustion.
- **Mitigation:**
  - Build a deterministic, sandboxed Abstract Syntax Tree (AST) condition evaluator.
  - Condition definitions are strictly validated JSON schemas.
  - Supported operators are limited to a whitelisted set: `EQUALS`, `NOT_EQUALS`, `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`, `CONTAINS`, `NOT_CONTAINS`, `IN`, `NOT_IN`, `EXISTS`, `NOT_EXISTS`.
  - Nested logic is restricted to structured `AND` / `OR` condition groups with a hard-coded recursion depth limit (max depth 5, max total conditions 25).

### Risk 3: Duplicate Workflow Execution & Event Storms
- **Risk:** High-frequency event triggers (e.g. bulk candidate ingestion or stage updates) could trigger duplicate concurrent executions, race conditions, or endless loops.
- **Mitigation:**
  - Deterministic idempotency key derivation: `idempotency_key = sha256(agency_id + workflow_id + trigger_event + entity_id + trigger_timestamp_bucket)`.
  - Database-level unique constraint on `(agency_id, idempotency_key)` in `workflow_executions`.
  - Per-agency active execution concurrency limits (max 10 concurrent active workflow runs per agency).

### Risk 4: Worker Crashes & Transactional Inconsistency
- **Risk:** A Celery worker terminating midway through a multi-step workflow could leave the execution in an indeterminate state.
- **Mitigation:**
  - Model `WorkflowExecution` and `WorkflowExecutionStep` with discrete states (`PENDING`, `RUNNING`, `WAITING_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`).
  - Transactional step execution: Each step commits its own database status.
  - Periodic heartbeat / sweep task to identify stalled executions (`RUNNING` with `updated_at > 15 minutes`) and mark them retryable or failed.

### Risk 5: Timezone Inconsistencies
- **Risk:** Approval expiration, delayed action triggers, and cron evaluations could mismatch if calculated in local server time.
- **Mitigation:**
  - Canonical timezone is strictly `Asia/Kolkata` (IST, UTC+05:30).
  - All database columns persist timestamps as UTC `DateTime(timezone=True)`.
  - Delay calculations and business hours are computed using explicit IST calendar conversions.

---

## 6. Proposed Phase 11 Architecture

### 6.1 Database Models (`backend/app/models/workflow.py`)

1. **`RecruitmentWorkflow`**:
   - Agency-isolated workflow definition (`id`, `agency_id`, `name`, `description`, `is_active`, `trigger_type`, `created_by`, `current_version_id`).
2. **`WorkflowVersion`**:
   - Immutable version record (`id`, `workflow_id`, `version_number`, `definition_json`, `created_by`, `created_at`).
   - `definition_json` contains the serialized trigger config, condition tree, and sequence of action steps.
3. **`WorkflowExecution`**:
   - Single run instance (`id`, `agency_id`, `workflow_id`, `workflow_version_id`, `trigger_event`, `trigger_entity_type`, `trigger_entity_id`, `status`, `idempotency_key`, `context_snapshot`, `error_message`, `started_at`, `completed_at`).
4. **`WorkflowExecutionStep`**:
   - Granular step execution state (`id`, `execution_id`, `step_index`, `action_type`, `action_config`, `status`, `input_payload`, `output_payload`, `error_message`, `started_at`, `completed_at`).
5. **`WorkflowApproval`**:
   - Human approval queue item (`id`, `agency_id`, `execution_id`, `step_id`, `title`, `description`, `status`, `requested_action`, `payload`, `assigned_role`, `assigned_user_id`, `approved_by_user_id`, `rejection_reason`, `expires_at`, `decided_at`).
6. **`RecruiterTask`**:
   - Recruiter follow-up task (`id`, `agency_id`, `title`, `description`, `priority`, `status`, `assigned_to_user_id`, `candidate_id`, `job_id`, `application_id`, `interview_id`, `due_date`, `completed_at`).
7. **`WorkflowAuditLog`**:
   - Immutable audit trail (`id`, `agency_id`, `workflow_id`, `execution_id`, `user_id`, `action`, `details`, `created_at`).

### 6.2 Service Architecture

```
                    [ Recruitment Event Occurs ]
        (Candidate Ingest / Stage Change / Interview Event)
                               |
                               v
                     WorkflowTriggerDispatcher
                               |
                   Find Active Matching Workflows
                               |
                               v
                  Evaluate Sandboxed Conditions
                 (Deterministic AST Evaluator)
                               |
                +--------------+--------------+
                |                             |
             [ False ]                     [ True ]
                |                             |
             No-Op                     Create Execution
                                      (Idempotency Check)
                                              |
                                              v
                                    Enqueue Celery Task
                               (execute_workflow_task)
                                              |
                                              v
                                  Sequential Action Runner
                                              |
            +----------------+----------------+----------------+
            |                |                |                |
            v                v                v                v
      Notification     Recruiter Task    Calendar Sync   Human Approval
     (Outbox Pattern) (RecruiterTask)   (CalendarJob)   (Wait for Review)
```

---

## 7. Audit Sign-Off

The existing architecture provides solid, robust foundations. Phase 11 can be implemented cleanly through additive models, the sandboxed condition engine, Celery task orchestration, and human-in-the-loop approval queues without modifying or breaking any verified Phase 1–10 capabilities.

**Stage 1 Audit Completed:** Proceed to Stage 2 (Database Models & Migrations).
