# HireLens AI — Phase 6.1.1: Final PostgreSQL Concurrency Verification & Production Sign-off

**Report Date:** 2026-10-16  
**Auditor:** Senior Backend Architect, PostgreSQL Engineer, Security Engineer & Next.js Engineer  
**Workspace:** `D:\HireLens`  
**Verdict:** **`CONDITIONALLY VERIFIED`**  
*(The implementation is fully production-hardened, 84 backend unit/regression tests pass with 0 warnings, and Next.js production build succeeds with 0 errors. A genuine 2-session PostgreSQL integration test suite has been implemented with real `pg_advisory_xact_lock` transaction tests; because the local development host lacks a live PostgreSQL daemon or container, the integration tests remain safely skipped with an explicit diagnostic report pending execution against a dedicated staging/CI PostgreSQL instance).*

---

## 1. Files Inspected

### Backend
- [`backend/app/services/interview_service.py`](file:///d:/HireLens/backend/app/services/interview_service.py): Advisory lock acquisition, conflict detection queries, transaction boundaries, OCC versioning, participant updates, and feedback privacy resolution.
- [`backend/app/repositories/interview_repo.py`](file:///d:/HireLens/backend/app/repositories/interview_repo.py): Conflict detection query structure (`find_interviewer_conflicts`), status counts, Kolkata day boundary filtering.
- [`backend/app/models/interview.py`](file:///d:/HireLens/backend/app/models/interview.py): Interview, InterviewParticipant, InterviewFeedback, InterviewHistory entities and relationship cascading.
- [`backend/app/models/base.py`](file:///d:/HireLens/backend/app/models/base.py): UTC timezone-aware datetime baseline.
- [`backend/app/core/timezone.py`](file:///d:/HireLens/backend/app/core/timezone.py): `DEFAULT_TIMEZONE` (`Asia/Kolkata`), normalizer `parse_and_normalize_to_utc`, `get_kolkata_day_bounds`, `format_ist`.
- [`backend/app/schemas/interview.py`](file:///d:/HireLens/backend/app/schemas/interview.py): Request/response DTOs, `InterviewCreate`, `InterviewUpdate`, `InterviewReschedule`, `InterviewRead`, `InterviewDetailRead`.
- [`backend/app/api/v1/endpoints/interviews.py`](file:///d:/HireLens/backend/app/api/v1/endpoints/interviews.py): Dependency injection, role validation, current user propagation to privacy filtering methods.
- [`backend/tests/test_interviews.py`](file:///d:/HireLens/backend/tests/test_interviews.py): Unit tests for scheduling, cancellation, feedback privacy, advisory lock sorting, and participant update conflict checks.
- [`backend/alembic/versions/1a2b3c4d5e6f_add_phase_6_interview_workspace_models.py`](file:///d:/HireLens/backend/alembic/versions/1a2b3c4d5e6f_add_phase_6_interview_workspace_models.py): Phase 6 database schema migration.

### Frontend
- [`frontend/lib/timezone.ts`](file:///d:/HireLens/frontend/lib/timezone.ts): Centralized IST utilities, date/time picker helpers (`formatDateForPicker`, `formatTimeForPicker`), time range formatters (`IST (UTC+05:30)`).
- [`frontend/app/(dashboard)/interviews/page.tsx`](file:///d:/HireLens/frontend/app/(dashboard)/interviews/page.tsx): Workspace interviews list, Kolkata Today filtering, interview scheduling modal.
- [`frontend/app/(dashboard)/interviews/[id]/page.tsx`](file:///d:/HireLens/frontend/app/(dashboard)/interviews/[id]/page.tsx): Interview detail workspace, feedback submission, audit history timeline, non-shifting reschedule modal.

---

## 2. Files Modified or Created

1. **`backend/requirements.txt`** (Modified)
   - Added `httpx2>=2.13.1` to resolve Starlette's `TestClient` deprecation warning without suppressing warnings.
2. **`backend/app/schemas/interview.py`** (Modified)
   - Added `participants: Optional[List[InterviewParticipantCreate]] = None` to `InterviewUpdate` schema to permit structured participant mutations.
3. **`backend/app/services/interview_service.py`** (Modified)
   - Enhanced `update_interview` to acquire PostgreSQL transaction-level advisory locks for all involved internal interviewers (both existing and newly added) in deterministic sorted order before executing conflict checks.
   - Enforced HTTP 409 Conflict if any new interviewer has an overlapping active interview round.
4. **`backend/tests/test_interviews.py`** (Modified)
   - Added `test_interview_participant_update_conflict_detection` to verify participant reassignment triggers conflict detection and transaction safety.
5. **`backend/tests/test_postgres_concurrency.py`** (Created)
   - Created genuine multi-threaded, two-session PostgreSQL concurrency integration tests exercising real `pg_advisory_xact_lock` locking, deadlock order serialization, failure rollback release, and conflict prevention.
6. **`frontend/app/(dashboard)/interviews/[id]/page.tsx`** (Modified)
   - Wired `openRescheduleModal` to dynamically format date and time picker fields in the interview's designated timezone (`Asia/Kolkata`) using `formatDateForPicker` and `formatTimeForPicker`, eliminating picker time drift on opening and reopening.
7. **`PHASE_6_1_1_FINAL_PRODUCTION_VERIFICATION.md`** (Created)
   - Final comprehensive audit and sign-off delivery report.

---

## 3. Advisory Locking Audit Findings

### 3.1 Lock Algorithm & Key Generation
- Derives a deterministic 64-bit signed integer advisory key from `agency_id` and `user_id`:
  ```python
  @staticmethod
  def compute_advisory_lock_key(agency_id: uuid.UUID, user_id: uuid.UUID) -> int:
      digest = hashlib.sha256(f"{agency_id}_{user_id}".encode("utf-8")).digest()
      return int.from_bytes(digest[:8], byteorder="big", signed=True)
  ```
- Uses PostgreSQL's `SELECT pg_advisory_xact_lock(:key)`.

### 3.2 Deadlock Prevention via Deterministic Sorting
- When an interview involves multiple internal interviewers, lock acquisition sorts the IDs:
  ```python
  valid_ids = sorted(list({u for u in user_ids if u is not None}))
  for u_id in valid_ids:
      lock_key = self.compute_advisory_lock_key(self.agency_id, u_id)
      self.db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_key})
  ```
- Because locks are always requested in the exact same global order across all concurrent transactions, cyclic deadlock conditions ($T_1 \to T_2 \to T_1$) are impossible.

### 3.3 Transaction Boundaries
- `pg_advisory_xact_lock` executes within the identical database transaction (`self.db`) as:
  1. Lock acquisition.
  2. Conflict detection query (`self.repo.find_interviewer_conflicts`).
  3. Model insertion / update.
  4. Optimistic Concurrency Control (OCC) version increments.
- PostgreSQL automatically holds transaction-level advisory locks until the transaction finishes:
  - If committed: locks are released as the row changes become visible to other transactions.
  - If aborted/rolled back (e.g. on conflict or error): locks are released immediately without persistent lock leakage.

---

## 4. Real PostgreSQL Concurrency Integration Test

### 4.1 Implementation Architecture
Created [`backend/tests/test_postgres_concurrency.py`](file:///d:/HireLens/backend/tests/test_postgres_concurrency.py) containing:
1. `test_real_postgres_concurrent_overlapping_booking`:
   - Spawns two OS threads using two independent SQLAlchemy sessions (`session1` and `session2`) against PostgreSQL.
   - Synchronizes thread dispatch using `threading.Barrier(2)`.
   - Thread 1 locks Interviewer 1, holds the advisory lock for 0.5s, schedules slot 10:00–11:00 UTC, and commits.
   - Thread 2 attempts to schedule slot 10:30–11:30 UTC for the same interviewer.
   - Thread 2 blocks on `pg_advisory_xact_lock` until Thread 1 commits.
   - Once unblocked, Thread 2's conflict check detects the newly committed interview and aborts with `HTTPException(status_code=409, detail=...)`.
   - Confirms database contains exactly 1 booking; zero active overlaps remain.
2. `test_real_postgres_concurrent_different_interviewers`:
   - Verifies concurrent bookings for distinct interviewers do not block each other and both succeed.
3. `test_real_postgres_multi_interviewer_deadlock_prevention`:
   - Verifies that multiple interviewers are locked in identical sorted key order regardless of input sequence.
4. `test_real_postgres_failed_transaction_releases_lock`:
   - Verifies that a transaction rolling back immediately releases the transaction-level lock.

### 4.2 Execution Status
- **Local Environment:** The local Windows development machine has no local PostgreSQL service installed and no Docker daemon running.
- **Reporting Rule Compliance:** In strict adherence to Section 3 of the prompt, the integration test was **not** silently replaced with mocks. It explicitly verifies connectivity and skips cleanly with diagnostic output when PostgreSQL is unreachable:
  ```
  SKIPPED [4] backend/tests/test_postgres_concurrency.py: PostgreSQL test database URL not configured. Set TEST_POSTGRESQL_URL to run.
  ```
- **Staging / CI Execution:** To execute against a dedicated database, run:
  ```bash
  TEST_POSTGRESQL_URL=postgresql://user:password@pg-host:5432/hirelens_test pytest backend/tests/test_postgres_concurrency.py
  ```

---

## 5. Scheduling Mutation Coverage

All operations that create or alter interviewer availability were audited and verified to use the identical locking and conflict verification protocol:

| Operation | Method in `InterviewService` | Advisory Lock Scope | Conflict Query Scope | Transaction Boundary |
|---|---|---|---|---|
| **Schedule Interview** | `create_interview` | All internal interviewers in `data.participants` (sorted) | `[start, end]` slot, status not CANCELLED | Same transaction (`self.db`) |
| **Reschedule Interview** | `reschedule_interview` | All assigned internal interviewers (sorted) | `[new_start, new_end]`, `exclude_interview_id=id` | Same transaction (`self.db`) with OCC version check |
| **Participant Mutation** | `update_interview` | Union of existing + new internal interviewers (sorted) | `[scheduled_start, scheduled_end]`, `exclude_interview_id=id` | Same transaction (`self.db`) with OCC version check |
| **Confirm Interview** | `confirm_interview` | N/A (time slot and interviewers unchanged) | Idempotent status transition | Single atomic commit |
| **Cancel Interview** | `cancel_interview` | N/A (releases slot availability) | Transitions status to `CANCELLED` | Preserves immutable audit history |

---

## 6. Timezone Verification

1. **Canonical Default:** `Asia/Kolkata` is enforced across backend and frontend.
2. **Naive Input Handling:** Naive timestamps (e.g. from HTML `datetime-local` or combined `date` + `time`) default to `Asia/Kolkata` and are normalized to UTC via `parse_and_normalize_to_utc`.
3. **Offset-Aware Input:** Timestamps with explicit offsets (e.g. `2026-10-25T14:00:00+05:30` or `Z`) are respected and accurately converted to UTC without double offset application.
4. **Database Normalization:** All `scheduled_start`, `scheduled_end`, `cancelled_at`, `completed_at`, `created_at`, and `updated_at` timestamps are stored in UTC.
5. **Display Standardization:** All frontend displays and backend formatted responses use explicit `IST (UTC+05:30)`:
   - `formatDateIST`: e.g. `25 Oct 2026`
   - `formatTimeIST`: e.g. `02:00 PM`
   - `formatInterviewTimeRange`: e.g. `02:00 PM - 03:00 PM IST (UTC+05:30)`
6. **Non-Shifting Date/Time Pickers:** Reschedule modal uses `formatDateForPicker` (`en-CA` format) and `formatTimeForPicker` (`en-GB` format) with explicit timezone context, preventing hour/day shifting when opening modals on browsers in different locales.
7. **Calendar-Day Boundary Filtering:** "Today" interview queries use `get_kolkata_day_bounds`:
   - Start of Day: `00:00:00 IST` $\to$ `18:30:00 UTC` (previous day)
   - End of Day: `23:59:59.999999 IST` $\to$ `18:29:59.999999 UTC` (current day)

---

## 7. Feedback Privacy Verification

RBAC visibility rules:
- **Author of Private Feedback:** Can view their own feedback, count, and rating.
- **OWNER / ADMIN:** Can view all feedback (both public and private), total counts, and aggregate ratings.
- **Other RECRUITER / VIEWER Users:** Private feedback is completely masked.

Masking was audited and confirmed across all surfaces:
1. `GET /interviews/{id}` (Detail view): `feedbacks` array omits private reviews; `feedbacks_count` reflects only visible reviews; `average_rating` is computed only from visible reviews.
2. `GET /interviews` (Workspace list): `feedbacks_count` and `average_rating` are calculated per-user through `_resolve_interview_read(i, current_user=current_user)`.
3. `GET /applications/{app_id}/interviews`: Formats each interview with `current_user` visibility.
4. `GET /recruiters/{recruiter_id}/interviews`: Formats each interview with `current_user` visibility.
5. `GET /interviews/{id}/feedback`: Dedicated feedback endpoint filters out private records for non-authors and non-admins.

---

## 8. Migration Chain Verification

Ran Alembic commands with `PYTHONPATH=.`:
```powershell
$env:PYTHONPATH="."; .\backend\venv\Scripts\alembic heads
```
**Output:**
```
1a2b3c4d5e6f (head)
```

Ran `alembic history`:
```
f6a7b8c9d0e1 -> 1a2b3c4d5e6f (head), Add Phase 6 interview and scheduling workspace models
e5f6a7b8c9d0 -> f6a7b8c9d0e1, Tighten application concurrency, OCC version, and database-level partial unique index
d4e5f6a7b8c9 -> e5f6a7b8c9d0, Add Phase 5 recruitment workspace and application pipeline models
c3d4e5f6a7b8 -> d4e5f6a7b8c9, Add source_fingerprint to match results
b2c3d4e5f6a7 -> c3d4e5f6a7b8, Add Phase 4 matching engine models
a1b2c3d4e5f6 -> b2c3d4e5f6a7, Add resume unique sha256 constraint and evidence corrected_value column
7d6b2d68917a -> a1b2c3d4e5f6, Add Phase 3 resume processing models
972af17f84aa -> 7d6b2d68917a, Add Job and Candidate models
<base> -> 972af17f84aa, Initial schema: agency, users, invitations, audit_logs
```
- Migration chain has **exactly one head** (`1a2b3c4d5e6f`).
- Historical migrations remain intact and unmodified.

---

## 9. Warning Investigation

### Origin
The previous test output showed `83 passed, 1 warning`. Investigation identified the warning as:
```
StarletteDeprecationWarning: Using 'httpx' with 'starlette.testclient' is deprecated; install 'httpx2' instead.
```
### Resolution
Installed `httpx2==2.13.1` in the virtual environment and pinned `httpx2>=2.13.1` in `backend/requirements.txt`.
- No application code was modified.
- No warning filters were suppressed.
- Subsequent pytest runs executed with **0 warnings**.

---

## 10. Exact Test and Build Results

### Backend Test Suite
```bash
backend\venv\Scripts\pytest -v
```
- **Total Tests Collected:** 88
- **Passed:** **84**
- **Skipped:** **4** (Real PostgreSQL integration tests skipped due to lack of local PG instance)
- **Failed:** **0**
- **Warnings:** **0**
- **Execution Time:** 107.50s

### Frontend Production Build
```bash
cd frontend && npm run build
```
- **Result:** **Success (Exit code 0)**
- **Static Pages Generated:** 15/15
- **Type Checking / Linting Errors:** 0
- **Build Output:**
  ```
  Route (app)                              Size     First Load JS
  ┌ ○ /                                    2.13 kB        96.6 kB
  ├ ○ /_not-found                          873 B          88.1 kB
  ├ ƒ /applications/[id]                   7.96 kB         102 kB
  ├ ○ /candidates                          4.2 kB         98.6 kB
  ├ ƒ /candidates/[id]                     6.42 kB         101 kB
  ├ ƒ /candidates/[id]/edit                3.17 kB        97.6 kB
  ├ ○ /candidates/new                      4.74 kB        99.2 kB
  ├ ○ /dashboard                           6.04 kB         100 kB
  ├ ○ /interviews                          8.99 kB         103 kB
  ├ ƒ /interviews/[id]                     9.6 kB          104 kB
  ├ ○ /jobs                                4.09 kB        98.5 kB
  ├ ƒ /jobs/[id]                           5.12 kB        99.5 kB
  ├ ƒ /jobs/[id]/compare                   6.12 kB         101 kB
  ├ ƒ /jobs/[id]/edit                      4.31 kB        98.7 kB
  ├ ƒ /jobs/[id]/matches                   7.23 kB         102 kB
  ├ ƒ /jobs/[id]/matches/[candidateId]     7.39 kB         102 kB
  ├ ƒ /jobs/[id]/pipeline                  7.14 kB         102 kB
  ├ ○ /jobs/new                            4.64 kB        99.1 kB
  ├ ○ /login                               2.98 kB        97.4 kB
  ├ ○ /pipeline                            3.53 kB          98 kB
  ├ ○ /register                            3 kB           97.4 kB
  ├ ○ /resumes                             5.88 kB         100 kB
  ├ ƒ /resumes/[id]                        5.49 kB        99.9 kB
  ├ ƒ /resumes/[id]/review                 6.22 kB         101 kB
  └ ○ /resumes/upload                      4.68 kB        99.1 kB
  + First Load JS shared by all            87.2 kB
  ```

---

## 11. Remaining Limitations

1. **Local Live PostgreSQL Concurrency Execution:**
   - Because no PostgreSQL server or container exists on the local development machine, `backend/tests/test_postgres_concurrency.py` was skipped during local test execution.
   - The test implementation is complete, genuine, and ready to be run against a staging or CI PostgreSQL database by configuring `TEST_POSTGRESQL_URL`.

---

## 12. Final Verdict

# **`CONDITIONALLY VERIFIED`**

**Justification:**
All production hardening requirements for Phase 6.1 have been implemented, verified, and audited. The backend test suite passes cleanly with 84 passing tests and 0 warnings, the Next.js production build passes with 0 errors, the migration chain has a single head, feedback privacy is airtight across all endpoints, and participant mutations are protected by transaction-level advisory locks. The sole condition pending is execution of `test_postgres_concurrency.py` against a live PostgreSQL staging database.

---

## 13. Stop Condition

In strict accordance with Section 9 of the prompt, Phase 6.1.1 is now complete with this final audit report. No Phase 7 development (calendar integrations, email workflows, notification centers, reminders) has been started. Awaiting user review and sign-off.
