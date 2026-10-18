# HireLens AI — Phase 11: Intelligent Recruitment Workflow Automation & Orchestration Delivery Report

**Project:** HireLens AI  
**Workspace:** `D:\HireLens`  
**Phase:** 11 — Intelligent Recruitment Workflow Automation & Orchestration  
**Status:** Successfully Completed & Verified  
**Canonical Timezone:** `Asia/Kolkata` (IST) with UTC database persistence  
**Current Alembic Head:** `6f7a8b9c0d1e` (single head)  
**Verification Baseline:**
- **Backend Tests:** 148 passed, 4 skipped across Phases 1–11 (10/10 dedicated Phase 11 workflow tests passed in 3.12s).
- **Frontend Production Build:** Successful (`next build` compiled 25/25 static routes with 0 lint and 0 type errors).

---

## 1. Executive Summary

Phase 11 transforms HireLens from an AI-assisted recruitment platform into an **intelligent recruitment operations and orchestration platform**. It introduces a configurable, deterministic recruitment workflow automation system with human-in-the-loop oversight.

### Core Architectural Principle
> **"Automate repetitive operations, preserve human authority over hiring decisions."**

The system strictly enforces boundaries preventing autonomous hiring decisions:
- Workflows **cannot** unilaterally hire, reject, or advance application stages.
- Sensitive operational actions (such as interview prep generation with recruiter dispatch, high-priority notifications, or candidate status escalations) can be configured to require explicit **human approval**.
- All condition evaluations are performed in a sandboxed, AST-based deterministic engine without `eval` or dynamic code execution.

---

## 2. Architecture Decisions & Design

### A. Sandboxed Deterministic Condition Engine (`backend/app/services/condition_engine.py`)
- **Zero dynamic code execution:** No Python `eval`, `exec`, or unsafe string interpolation.
- **Recursive AST Evaluation:** Evaluates conditions with strictly validated operators:
  - Equality / inequality: `EQUALS`, `NOT_EQUALS`
  - Numeric comparisons: `GREATER_THAN`, `GREATER_THAN_OR_EQUAL`, `LESS_THAN`, `LESS_THAN_OR_EQUAL`
  - String / collection memberships: `CONTAINS`, `NOT_CONTAINS`, `IN`, `NOT_IN`
  - Existence checks: `EXISTS`, `NOT_EXISTS`
- **Nested Logic:** Supports arbitrary combinations of `AND` and `OR` boolean groups.
- **Bounded Complexity Protection:** Hard safety ceilings enforce maximum evaluation depth (`5`) and maximum condition count (`25`) to prevent runaway resource exhaustion or recursive denial-of-service.
- **Null Safety:** Missing dictionary paths return `None` gracefully and evaluate against operators deterministically without throwing uncaught exceptions.

### B. Action Engine & Integration Synergy (`backend/app/services/workflow_service.py`)
Reuses and orchestrates existing platform capabilities from Phases 1–10 without duplicating services:
1. `SEND_CANDIDATE_COMMUNICATION`: Queues candidate emails through Phase 7's transactional `NotificationOutbox` infrastructure.
2. `NOTIFY_RECRUITERS`: Enqueues notifications in the recruiter's outbox.
3. `CREATE_RECRUITER_TASK`: Creates operational action items in the `recruiter_tasks` table with due dates in IST.
4. `GENERATE_INTERVIEW_PREP`: Invokes Phase 10's `CopilotService.prepare_interview` to produce structured interview briefs.
5. `TRIGGER_CALENDAR_SYNC`: Enqueues Phase 9's `sync_interview_to_calendar_task` to ensure external Google/Microsoft calendar synchronization.
6. `GENERATE_ANALYTICS_EVENT`: Logs deterministic operational analytics events.
7. `REQUEST_HUMAN_APPROVAL`: Pauses the workflow step, enters an approval request into `workflow_approvals`, and awaits manual review.

### C. Human Approval & Review Lifecycle (`/approvals`)
- Workflows encountering a step requiring approval transition that step to `WAITING_FOR_APPROVAL` and record a `WorkflowApproval` row.
- **Agency-level isolation and RBAC:** Only authorized roles (`OWNER`, `ADMIN`, or designated `RECRUITER`) can resolve approval tickets.
- **Decisions:**
  - `APPROVE`: The approval status is updated to `APPROVED`, attribution is recorded with user ID and timestamp, and the remaining execution steps resume.
  - `REJECT`: Rejection requires a **mandatory non-empty reason**, recorded in audit history. The workflow execution status transitions to `CANCELLED`.
  - `EXPIRED`: An automated periodic sweep task (`sweep_expired_approvals_task`) marks approvals past their `expires_at` threshold as `EXPIRED` and marks dependent executions as `CANCELLED`.

### D. Celery Scheduling & Resilience (`backend/app/tasks/workflow_tasks.py`)
- Celery task `execute_workflow_task(execution_id)` handles async and delayed executions.
- **Idempotency Guard:** `WorkflowExecution` records have unique idempotency keys (`agency_id:workflow_id:trigger_entity_type:entity_id:timestamp_or_nonce`) with a database unique index, preventing duplicate processing.
- **Exponential Backoff & Retries:** Automatic retries up to 3 times on transient failures.
- **Timeout & Failure Handling:** Fatal errors catch exceptions, log the reason in `error_message`, and update the execution status to `FAILED` with an immutable `WorkflowAuditLog` entry.

---

## 3. Database Schema & Migration

### Migration Details
- **Revision ID:** `6f7a8b9c0d1e`
- **Down Revision:** `5e6f7a8b9c0d` (Phase 10 Copilot)
- **Status:** Applied, verified reversible, single migration head confirmed.

### New Models Created (`backend/app/models/workflow.py`)
1. **`RecruitmentWorkflow`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `title` (String(255))
   - `description` (Text)
   - `trigger_type` (Enum `WorkflowTriggerType`)
   - `is_active` (Boolean, indexed)
   - `current_version_id` (UUID, nullable)
   - `created_by_user_id` (UUID, FK -> `users.id`)
   - `created_at`, `updated_at` (DateTime with timezone)

2. **`WorkflowVersion`**:
   - `id` (UUID, PK)
   - `workflow_id` (UUID, FK -> `recruitment_workflows.id`, ondelete CASCADE)
   - `version_number` (Integer)
   - `trigger_config` (JSONB)
   - `condition_definition` (JSONB)
   - `action_definitions` (JSONB)
   - `created_by_user_id` (UUID, FK -> `users.id`)
   - `created_at` (DateTime with timezone)

3. **`WorkflowExecution`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `workflow_id` (UUID, FK -> `recruitment_workflows.id`)
   - `workflow_version_id` (UUID, FK -> `workflow_versions.id`)
   - `trigger_event` (Enum `WorkflowTriggerType`)
   - `trigger_entity_type` (String(50))
   - `trigger_entity_id` (UUID)
   - `status` (Enum `WorkflowExecutionStatus`: `PENDING`, `RUNNING`, `WAITING_FOR_APPROVAL`, `COMPLETED`, `FAILED`, `CANCELLED`)
   - `idempotency_key` (String(128), unique constraint per agency)
   - `retry_count` (Integer, default 0)
   - `error_message` (Text)
   - `started_at`, `completed_at` (DateTime with timezone)

4. **`WorkflowExecutionStep`**:
   - `id` (UUID, PK)
   - `execution_id` (UUID, FK -> `workflow_executions.id`, ondelete CASCADE)
   - `step_index` (Integer)
   - `action_type` (Enum `WorkflowActionType`)
   - `status` (Enum `WorkflowStepStatus`: `PENDING`, `IN_PROGRESS`, `WAITING_FOR_APPROVAL`, `COMPLETED`, `FAILED`, `SKIPPED`)
   - `action_config` (JSONB)
   - `output_payload` (JSONB)
   - `error_message` (Text)
   - `started_at`, `completed_at` (DateTime with timezone)

5. **`WorkflowApproval`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `execution_id` (UUID, FK -> `workflow_executions.id`)
   - `step_id` (UUID, FK -> `workflow_execution_steps.id`)
   - `title` (String(255))
   - `description` (Text)
   - `status` (Enum `WorkflowApprovalStatus`: `PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`)
   - `requested_action` (Enum `WorkflowActionType`)
   - `action_payload` (JSONB)
   - `assigned_role` (String(50), default `ADMIN`)
   - `assigned_user_id` (UUID, nullable)
   - `approved_by_user_id` (UUID, nullable)
   - `rejection_reason` (Text, nullable)
   - `expires_at` (DateTime with timezone)
   - `decided_at` (DateTime with timezone)

6. **`RecruiterTask`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `title` (String(255))
   - `description` (Text)
   - `priority` (Enum `RecruiterTaskPriority`: `LOW`, `MEDIUM`, `HIGH`, `URGENT`)
   - `status` (Enum `RecruiterTaskStatus`: `PENDING`, `IN_PROGRESS`, `COMPLETED`, `CANCELLED`)
   - `assigned_to_user_id` (UUID, FK -> `users.id`)
   - `created_by_user_id` (UUID, FK -> `users.id`)
   - `candidate_id`, `job_id`, `application_id`, `interview_id` (UUID references)
   - `due_date`, `completed_at` (DateTime with timezone)

7. **`WorkflowAuditLog`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `execution_id` (UUID, FK -> `workflow_executions.id`, nullable)
   - `workflow_id` (UUID, nullable)
   - `event_name` (String(100))
   - `actor_user_id` (UUID, nullable)
   - `details` (JSONB)
   - `created_at` (DateTime with timezone)

---

## 4. API Endpoints (`/api/v1/workflows`)

| Method | Endpoint | Description | Access Control |
|---|---|---|---|
| `GET` | `/api/v1/workflows` | List agency workflows with active filter and pagination | All Agency Users |
| `POST` | `/api/v1/workflows` | Create a new workflow and initial version | OWNER, ADMIN |
| `GET` | `/api/v1/workflows/monitoring/stats` | Aggregated monitoring KPIs & execution stream | All Agency Users |
| `GET` | `/api/v1/workflows/executions` | List recent executions with status filter | All Agency Users |
| `GET` | `/api/v1/workflows/executions/{id}` | Detailed execution trace and step telemetry | All Agency Users |
| `GET` | `/api/v1/workflows/approvals` | List approval queue tickets | All Agency Users |
| `POST` | `/api/v1/workflows/approvals/{id}/decision` | Approve or reject a pending approval ticket | OWNER, ADMIN, RECRUITER |
| `GET` | `/api/v1/workflows/tasks` | List operational recruiter tasks | All Agency Users |
| `POST` | `/api/v1/workflows/tasks` | Create a manual recruiter task | OWNER, ADMIN, RECRUITER |
| `PATCH` | `/api/v1/workflows/tasks/{id}` | Update task status or priority | OWNER, ADMIN, RECRUITER |
| `DELETE` | `/api/v1/workflows/tasks/{id}` | Delete recruiter task | OWNER, ADMIN |
| `GET` | `/api/v1/workflows/{id}` | Get workflow details with version history | All Agency Users |
| `PUT` | `/api/v1/workflows/{id}` | Update workflow metadata or configuration | OWNER, ADMIN |
| `DELETE` | `/api/v1/workflows/{id}` | Soft-delete/deactivate workflow | OWNER, ADMIN |
| `POST` | `/api/v1/workflows/{id}/trigger` | Manually dispatch a test execution | OWNER, ADMIN |

---

## 5. Frontend User Experience

Built on Next.js 14 App Router, conforming strictly to HireLens SaaS visual guidelines:
- **Navigation (`frontend/app/(dashboard)/layout.tsx`):** Added Workflows (`/workflows`), Approvals (`/approvals`), and Tasks (`/tasks`) into the main navigation hierarchy.
- **Workflow Directory (`/workflows`):** Filter workflows by status and trigger event; toggle active/inactive directly from the card; view action summary badges and quick links.
- **Visual Workflow Builder (`/workflows/new`):**
  - Trigger event selector with friendly descriptions.
  - Interactive Condition Builder supporting field paths, comparisons, and expected values.
  - Action Sequence Builder supporting candidate communication, recruiter notifications, interview prep briefs, and recruiter tasks.
  - "Require Human Approval" toggle for sensitive action steps.
- **Workflow Details & Execution History (`/workflows/[id]`):**
  - Displays configuration breakdown and condition matrix.
  - Real-time execution log history table.
  - "Run Workflow Now" modal for manual testing.
- **Workflow Monitoring Dashboard (`/workflows/monitoring`):**
  - Metric summary cards: Active Workflows, Total Executions, Success Rate (%), Pending Approvals, Average Execution Time (ms).
  - Telemetry drawer/modal for inspecting step-level JSON payloads, conditions evaluated, and error logs.
- **Human Approval Queue (`/approvals`):**
  - Tabbed interface (`PENDING`, `APPROVED`, `REJECTED`, `EXPIRED`).
  - One-click "Approve & Execute" button.
  - "Reject Request" with mandatory rejection reason modal.
- **Recruiter Operational Tasks (`/tasks`):**
  - Task card workspace with fast status toggles (`PENDING` <-> `COMPLETED`).
  - Priority badges (`URGENT`, `HIGH`, `MEDIUM`, `LOW`).
  - IST-formatted due dates with visual overdue alerts.
  - "New Recruiter Task" modal for scheduling ad-hoc operational items.

---

## 6. Timezone Standardization (`Asia/Kolkata`)

In alignment with HireLens core architecture:
- All task due dates, approval expiry deadlines, and execution timestamps are persisted in **UTC** within PostgreSQL.
- All frontend presentations format timestamps into **IST (`Asia/Kolkata` / UTC+05:30)** using localized date formatters.
- Expiration sweeps and delays calculate relative time offsets against UTC to ensure platform portability.

---

## 7. Verification & Test Results

### Dedicated Phase 11 Test Suite (`backend/tests/test_workflows.py`)
All 10 tests passed in 3.12s:
1. `test_condition_engine_operators`: Evaluates all 12 condition operators and dot-path resolution.
2. `test_condition_engine_nested_groups_and_complexity`: Validates AND/OR trees and depth limit protections.
3. `test_workflow_crud_and_versioning`: Tests workflow creation, version increments, and retrieval.
4. `test_workflow_rbac_and_tenant_isolation`: Verifies that recruiters cannot modify workflows and cross-tenant execution is blocked.
5. `test_workflow_action_execution_notification_outbox`: Verifies integration with Phase 7 NotificationOutbox.
6. `test_workflow_action_recruiter_task_creation`: Verifies automated task generation from workflow triggers.
7. `test_workflow_idempotency_prevents_duplicate_runs`: Verifies database-level idempotency guards against concurrent duplicate triggers.
8. `test_human_approval_lifecycle_approve_and_reject`: Verifies approval queues, approval resumption, and rejection with mandatory reason.
9. `test_recruiter_task_endpoints_and_monitoring`: Tests task CRUD, status updates, and SQL monitoring KPI aggregations.
10. `test_prohibited_autonomous_actions_boundary`: Validates architectural boundary preventing autonomous hiring, rejection, or stage advancement.

### Full Backend Test Suite
- **148 tests passed**, 4 skipped (PostgreSQL concurrency tests requiring live DB socket), 0 failures across all phases.

### Frontend Production Build
```bash
npm run build
```
- **Compiled successfully**
- **Linting & Type-checking passed** (0 errors)
- **25/25 static pages generated:**
  - `○ /approvals`
  - `○ /tasks`
  - `○ /workflows`
  - `ƒ /workflows/[id]`
  - `○ /workflows/monitoring`
  - `○ /workflows/new`
  - All existing routes from Phases 1–10 preserved intact.

---

## 8. Files Created and Modified

### Created Files
- `backend/app/models/workflow.py`
- `backend/app/schemas/workflow.py`
- `backend/app/services/condition_engine.py`
- `backend/app/services/workflow_service.py`
- `backend/app/tasks/workflow_tasks.py`
- `backend/app/api/v1/endpoints/workflows.py`
- `backend/alembic/versions/6f7a8b9c0d1e_add_phase_11_workflow_automation_and_orchestration_models.py`
- `backend/tests/test_workflows.py`
- `frontend/app/(dashboard)/workflows/page.tsx`
- `frontend/app/(dashboard)/workflows/new/page.tsx`
- `frontend/app/(dashboard)/workflows/[id]/page.tsx`
- `frontend/app/(dashboard)/workflows/monitoring/page.tsx`
- `frontend/app/(dashboard)/approvals/page.tsx`
- `frontend/app/(dashboard)/tasks/page.tsx`
- `PHASE_11_ARCHITECTURE_AUDIT.md`
- `PHASE_11_WORKFLOW_AUTOMATION_DELIVERY_REPORT.md`

### Modified Files
- `backend/app/models/enums.py`: Added workflow triggers, actions, statuses, and task enums.
- `backend/app/models/__init__.py`: Registered Phase 11 models and enums.
- `backend/app/core/celery_app.py`: Registered `app.tasks.workflow_tasks`.
- `backend/app/api/v1/api.py`: Mounted `/workflows` router.
- `backend/app/services/application_service.py`: Added lifecycle triggers on submission and stage changes.
- `backend/app/services/interview_service.py`: Added lifecycle triggers on interview scheduling, rescheduling, completion, and feedback submission.
- `frontend/types/index.ts`: Added Phase 11 TypeScript interfaces and enums.
- `frontend/app/(dashboard)/layout.tsx`: Added Workflows, Approvals, and Tasks navigation links.

---

## 9. Celery Worker & Scheduler Setup

To run workflow automation in production environments:
```bash
# 1. Start Celery Worker
celery -A app.core.celery_app worker -l info -Q default,notifications,calendar_sync,workflows -c 4

# 2. Start Celery Beat Scheduler (Periodic approval sweeps & reminders)
celery -A app.core.celery_app beat -l info
```

---

## 10. Conclusion & Stop Condition Met

Phase 11 is complete, fully tested, documented, and verified.
All operations honor the core principle: **automate repetitive operations, preserve human authority over hiring decisions.**

Work has stopped cleanly. We await your explicit review and approval before proceeding to any future phases.
