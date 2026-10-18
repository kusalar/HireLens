# HireLens AI — Phase 12: Predictive Recruitment Intelligence & Workforce Planning Delivery Report

**Project:** HireLens AI  
**Workspace:** `D:\HireLens`  
**Phase:** 12 — Predictive Recruitment Intelligence & Workforce Planning  
**Status:** Successfully Completed & Verified  
**Canonical Timezone:** `Asia/Kolkata` (IST, UTC+05:30) with UTC database persistence  
**Current Alembic Head:** `7a8b9c0d1e2f` (single head)  
**Verification Baseline:**
- **Backend Tests:** 158 passed, 4 skipped across Phases 1–12 (10/10 dedicated Phase 12 tests passed in 3.00s).
- **Frontend Production Build:** Successful (`next build` compiled 26/26 static routes with 0 lint and 0 type errors).

---

## 1. Executive Summary

Phase 12 elevates HireLens from an automated operational workflow platform into an **enterprise-grade predictive recruitment intelligence and workforce planning system**. It introduces statistical modeling and machine learning estimators to forecast hiring completion velocity, project requisition demand over 30/60/90-day horizons, uncover pipeline bottlenecks before they cause candidate drop-off, catalog actionable recruitment risks, and provide advisory recruiter capacity planning.

### Core Architectural Principle
> **"Provide evidence-driven, explainable predictive intelligence with honest handling of uncertainty, while preserving human authority over all hiring, candidate-ranking, and workload decisions."**

The system strictly enforces boundaries:
- Predictions **never** autonomously hire, reject, rank candidates, or reassign recruiters.
- When historical data is sparse, the system **never fabricates synthetic data** as real predictions; it explicitly flags baseline empirical fallbacks with honest sample sizes and confidence ratings.
- All AI explanations are strictly grounded in verified database telemetry using the Phase 10 AI provider abstraction.

---

## 2. Architecture & Hybrid Modeling Methodology

### A. Honest Handling of Sample Sizes & Tiered Model Selection (`backend/app/services/predictive_engine.py`)
Recruitment agencies exhibit varying historical data volumes. The predictive engine operates in three rigorous tiers:

1. **Cold Start / Sparse Tier ($N < 10$ historical hires):**
   - Applies empirical Bayesian priors incorporating industry-standard benchmarks (e.g. 34.0 days base cycle time, department multipliers) combined with whatever few observed data points exist via shrinkage estimation:
     $$\widehat{T} = w \cdot \bar{T}_{\text{observed}} + (1 - w) \cdot T_{\text{benchmark}}, \quad w = \frac{N}{10}$$
   - Marks predictions explicitly with `is_baseline_fallback = True`, confidence level = `PRELIMINARY` or `LOW`, and explanatory notices informing leadership of small sample sizes.
2. **Intermediate Tier ($10 \le N < 50$ historical hires):**
   - Empirical moving averages and exponential smoothing for time-to-hire distributions.
   - Stage duration survival distributions (Kaplan-Meier-inspired cycle times) for bottleneck identification.
   - Computes standard error $SE = \frac{s}{\sqrt{N}}$ and empirical 95% confidence intervals: $[\widehat{T} - 1.96 \cdot SE, \widehat{T} + 1.96 \cdot SE]$.
3. **Mature Tier ($N \ge 50$ historical hires):**
   - Multivariate `scikit-learn` Ridge Regression (`Ridge(alpha=1.0)`) trained on engineered features: mandatory requirements count, required seniority/experience months, and initial application volume.
   - Chronological 80/20 train/validation split preventing data leakage.
   - Logs validation metrics (MAE, RMSE, $R^2$) into `prediction_model_versions`.

### B. Hiring Demand Forecasting (30, 60, 90 Days)
- Linear trend decomposition: Fits ordinary least squares on monthly job openings and application volumes over past quarters.
- Forecasts projected new requisition demand for 30D, 60D, and 90D horizons.
- Projects expected candidate inflow volume required to sustain projected hiring velocity.
- Supplies historical vs. projected time series data points for charting.

### C. Pipeline Bottleneck Radar
- Evaluates cycle times across pipeline stages: `APPLIED`, `UNDER_REVIEW`, `SHORTLISTED`, `INTERVIEW`, `SELECTED`.
- Calculates median duration, mean duration, and 90th percentile duration ($P_{90}$) from `ApplicationStageHistory`.
- Flags a stage as `is_bottleneck = True` if the active candidate volume is elevated and the median duration exceeds 1.25x benchmark.
- Analyzes interview scheduling latency per department (shortlist-to-interview delay).

### D. Recruitment Risk Intelligence Engine
Scans agency telemetry and raises structured records in `recruitment_risks`:
- `RISK_PIPELINE_DEFICIT`: Active job open $>7$ days with $<3$ active applicants.
- `RISK_STAGE_STAGNATION`: Applications stagnant in review or interview stages exceeding benchmark durations.
- `RISK_DROP_OFF_VULNERABILITY`: High-match candidate ($\ge 75\%$) with no active interview scheduled.
- `RISK_SCHEDULING_BOTTLENECK`: Completed interviews awaiting feedback for $>48$ hours or pending interview invitations.
- `RISK_EXPENSE_OVERRUN`: Expense on job exceeding target budget or department median.
- Supported risk lifecycle: `OPEN` $\rightarrow$ `ACKNOWLEDGED` $\rightarrow$ `MITIGATED` / `DISMISSED` with reviewer attribution and resolution notes.

### E. Recruiter Capacity & Workload Balancing
- Measures operational load per recruiter:
  $$\text{Workload Index} = 1.0 \times N_{\text{active apps}} + 2.5 \times N_{\text{interviews}} + 5.0 \times N_{\text{open jobs}}$$
- Compares against agency mean $\mu$ and standard deviation $\sigma$:
  - `OVERLOADED`: $\text{Index} > \mu + 1.25\sigma$ and $\text{Index} > 25.0$.
  - `UNDERUTILIZED`: $\text{Index} < \mu - 1.25\sigma$.
  - `OPTIMAL`: Workload within balanced operational bounds.
- Generates advisory load-leveling recommendations with clear disclaimers that reassignments require human decision-making.

---

## 3. Database Schema & Migration

### Migration Details
- **Revision ID:** `7a8b9c0d1e2f`
- **Down Revision:** `6f7a8b9c0d1e` (Phase 11 Workflows)
- **Status:** Verified upgrade, downgrade (`-1`), and re-upgrade. Single migration head confirmed.

### New Models Created (`backend/app/models/predictive.py`)
1. **`PredictionModelVersion`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `model_type` (Enum `ModelType`: `TIME_TO_HIRE`, `HIRING_DEMAND`, `STAGE_DURATION`, `CANDIDATE_DROP_OFF`)
   - `algorithm` (Enum `PredictionAlgorithm`: `RIDGE_REGRESSION`, `RANDOM_FOREST`, `EXPONENTIAL_SMOOTHING`, `BASELINE_EMPIRICAL`)
   - `version_tag` (String(100))
   - `training_sample_size` (Integer)
   - `evaluation_metrics_json` (Text, stores MAE, RMSE, $R^2$)
   - `hyperparameters_json`, `feature_names_json` (Text)
   - `is_active` (Boolean, indexed)
   - `trained_at`, `created_at` (DateTime TZ)

2. **`RecruitmentForecast`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `job_id` (UUID, FK -> `jobs.id`, nullable, indexed)
   - `department` (String(100), nullable, indexed)
   - `forecast_type` (Enum `ForecastType`: `TIME_TO_HIRE`, `DEMAND_30D`, `DEMAND_60D`, `DEMAND_90D`, `APPLICATION_VOLUME`)
   - `predicted_value` (Float)
   - `confidence_lower`, `confidence_upper` (Float)
   - `confidence_level` (Enum `ConfidenceLevel`: `HIGH`, `MEDIUM`, `LOW`, `PRELIMINARY`)
   - `is_baseline_fallback` (Boolean)
   - `explanation` (Text)
   - `factors_json` (Text)
   - `model_version_id` (UUID, FK -> `prediction_model_versions.id`)
   - `horizon_days` (Integer)
   - `forecast_date`, `created_at`, `updated_at` (DateTime TZ)

3. **`RecruitmentRisk`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `risk_type` (Enum `RecruitmentRiskType`: `PIPELINE_DEFICIT`, `STAGE_STAGNATION`, `DROP_OFF_VULNERABILITY`, `SCHEDULING_BOTTLENECK`, `EXPENSE_OVERRUN`)
   - `severity` (Enum `RiskSeverity`: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`, indexed)
   - `status` (Enum `RiskStatus`: `OPEN`, `ACKNOWLEDGED`, `MITIGATED`, `DISMISSED`, indexed)
   - `title` (String(255))
   - `description` (Text)
   - `job_id` (UUID, FK -> `jobs.id`, nullable)
   - `candidate_id` (UUID, FK -> `candidates.id`, nullable)
   - `application_id` (UUID, nullable)
   - `recruiter_id` (UUID, FK -> `users.id`, nullable)
   - `evidence_payload_json` (Text)
   - `recommended_action` (Text)
   - `confidence_score` (Float)
   - `acknowledged_by_user_id` (UUID, FK -> `users.id`, nullable)
   - `resolution_notes` (Text, nullable)
   - `detected_at`, `resolved_at`, `created_at`, `updated_at` (DateTime TZ)

4. **`CapacitySnapshot`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `recruiter_id` (UUID, FK -> `users.id`, indexed)
   - `active_applications_count`, `upcoming_interviews_count`, `open_requisitions_count` (Integer)
   - `workload_index` (Float)
   - `utilization_status` (Enum `RecruiterUtilizationStatus`: `OPTIMAL`, `OVERLOADED`, `UNDERUTILIZED`)
   - `recommendations_json` (Text)
   - `snapshot_date`, `created_at` (DateTime TZ)

5. **`ForecastEvaluation`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `forecast_id` (UUID, FK -> `recruitment_forecasts.id`, ondelete CASCADE)
   - `actual_value`, `absolute_error`, `percentage_error` (Float)
   - `evaluated_at` (DateTime TZ)

---

## 4. API Endpoints (`/api/v1/predictive-analytics`)

| Method | Endpoint | Description | RBAC |
|---|---|---|---|
| `GET` | `/api/v1/predictive-analytics/overview` | Executive predictive intelligence summary, KPI cards, and critical risk counters | All Agency Users |
| `GET` | `/api/v1/predictive-analytics/time-to-hire` | Requisition-specific and department-level time-to-hire forecasts with confidence intervals | All Agency Users |
| `GET` | `/api/v1/predictive-analytics/demand` | 30/60/90-day recruitment demand and application volume projections | All Agency Users |
| `GET` | `/api/v1/predictive-analytics/bottlenecks` | Pipeline stage stagnation analysis and interview scheduling delay radar | All Agency Users |
| `GET` | `/api/v1/predictive-analytics/risks` | Filterable recruitment risk register with severity badges and evidence | All Agency Users |
| `PATCH` | `/api/v1/predictive-analytics/risks/{id}` | Acknowledge, mitigate, or dismiss a recruitment risk | OWNER, ADMIN, RECRUITER |
| `GET` | `/api/v1/predictive-analytics/capacity` | Recruiter workload distribution, capacity indices, and load-leveling advice | All Agency Users |
| `GET` | `/api/v1/predictive-analytics/models` | Model registry: training versions, algorithms, sample sizes, and accuracy metrics | All Agency Users |
| `POST` | `/api/v1/predictive-analytics/refresh` | Trigger on-demand recalculation of forecasts and risk detection | OWNER, ADMIN |

---

## 5. Frontend Predictive Analytics Workspace

Built on Next.js 14 App Router, conforming strictly to HireLens SaaS visual guidelines:
- **Route:** [`/predictive-analytics`](file:///D:/HireLens/frontend/app/(dashboard)/predictive-analytics/page.tsx)
- **Navigation:** Integrated `TrendingUp` icon into main sidebar layout (`frontend/app/(dashboard)/layout.tsx`).
- **Interactive Tabs:**
  1. **Executive Overview:** 5 executive KPI cards (Avg Time-to-Hire, 30D Demand, Active Requisitions, Open Risks with Critical badges, Capacity Balance), Grounded AI Strategic Brief, Top Actionable Risks widget, Department velocity list.
  2. **Time-to-Hire Forecast:** Explanatory notes, 95% confidence bounds, active requisitions forecast list with confidence rating badges.
  3. **Hiring Demand (30, 60, 90 Days):** 3-horizon summary cards, department demand breakdown, historical vs projected time series data table.
  4. **Bottleneck Radar:** 5-stage duration cards (`APPLIED`, `UNDER_REVIEW`, `SHORTLISTED`, `INTERVIEW`, `SELECTED`) with median, benchmark, P90 duration, candidate counts, and Bottleneck alert badges; interview delay radar.
  5. **Risk Register:** Filter by status and severity; risk cards with evidence and recommended actions; modal to Acknowledge, Mitigate, or Dismiss with resolution notes.
  6. **Recruiter Capacity Planning:** Recruiter operational workload cards with active applications, interviews, open requisitions, and workload index; utilization status badges; advisory redistribution guidelines.
  7. **Model Governance:** Auditable model registry table detailing version tags, algorithms, training sample counts, and validation metrics (MAE, RMSE, $R^2$).

---

## 6. Timezone Standardization (`Asia/Kolkata`)

In alignment with HireLens core architecture:
- All task scheduling, 30/60/90-day forecast horizon dates, and risk detection timestamps are stored in **UTC** within PostgreSQL.
- Frontend displays all dates, timestamps, and reporting periods explicitly in **IST (`Asia/Kolkata` / UTC+05:30)**.

---

## 7. Verification & Test Results

### Dedicated Phase 12 Test Suite (`backend/tests/test_predictive.py`)
All 10 tests passed in 3.00s:
1. `test_predictive_engine_cold_start_fallback`: Verifies $N < 10$ fallback to empirical Bayesian baseline with honest preliminary confidence.
2. `test_predictive_engine_intermediate_and_mature_data`: Validates exponential smoothing for $10 \le N < 50$ and scikit-learn models for $N \ge 50$.
3. `test_hiring_demand_linear_forecasting`: Validates trend decomposition and 30/60/90-day demand aggregation.
4. `test_recruiter_workload_calculation`: Validates composite workload index calculation ($1.0 \times \text{apps} + 2.5 \times \text{interviews} + 5.0 \times \text{jobs}$).
5. `test_predictive_refresh_and_overview_api`: Tests `POST /refresh` and `GET /overview` API contract.
6. `test_time_to_hire_and_demand_endpoints`: Tests `GET /time-to-hire` and `GET /demand` responses.
7. `test_bottlenecks_and_capacity_endpoints`: Tests `GET /bottlenecks` and `GET /capacity` outputs.
8. `test_recruitment_risk_detection_and_lifecycle`: Tests automated risk scanner, filtering, and acknowledgment/mitigation transitions.
9. `test_predictive_rbac_and_tenant_isolation`: Verifies that recruiters cannot trigger model re-training and tenant isolation holds strictly across agencies.
10. `test_model_registry_governance`: Tests that `GET /models` returns versions, algorithms, and training sample sizes.

### Full Backend Test Suite
- **158 passed, 4 skipped in 149.79s** (0 regressions across Phases 1–12).
- The 4 skipped tests are previously verified PostgreSQL concurrency tests requiring a live PostgreSQL instance.

### Frontend Production Build
```bash
npm run build
```
- **Compiled successfully**
- **Linting & Type-checking passed** (0 errors)
- **26/26 static pages generated:**
  - `○ /predictive-analytics` (9.99 kB, First Load JS: 97.2 kB)
  - All existing routes from Phases 1–11 preserved intact.

---

## 8. Files Created and Modified

### Created Files
- `backend/app/models/predictive.py`
- `backend/app/schemas/predictive.py`
- `backend/app/services/predictive_engine.py`
- `backend/app/services/predictive_service.py`
- `backend/app/tasks/predictive_tasks.py`
- `backend/app/api/v1/endpoints/predictive.py`
- `backend/alembic/versions/7a8b9c0d1e2f_add_phase_12_predictive_intelligence_and_workforce_planning_models.py`
- `backend/tests/test_predictive.py`
- `frontend/app/(dashboard)/predictive-analytics/page.tsx`
- `PHASE_12_ARCHITECTURE_AUDIT.md`
- `PHASE_12_PREDICTIVE_INTELLIGENCE_DELIVERY_REPORT.md`

### Modified Files
- `backend/app/models/enums.py`: Added predictive intelligence enums (`ModelType`, `PredictionAlgorithm`, `ForecastType`, `ConfidenceLevel`, `RecruitmentRiskType`, `RiskSeverity`, `RiskStatus`, `RecruiterUtilizationStatus`).
- `backend/app/models/__init__.py`: Registered Phase 12 predictive models and enums.
- `backend/app/core/celery_app.py`: Registered `app.tasks.predictive_tasks` for autodiscovery.
- `backend/app/api/v1/api.py`: Mounted `/predictive-analytics` router.
- `backend/requirements.txt`: Added `scikit-learn>=1.4.0` and `numpy>=1.26.0`.
- `frontend/types/index.ts`: Added Phase 12 TypeScript interfaces and enums.
- `frontend/app/(dashboard)/layout.tsx`: Added `Predictive AI` navigation link.

---

## 9. Known Limitations & Production Deployment Requirements

1. **Celery Worker & Beat Configuration:**
   - To execute background periodic model refreshes and risk evaluation sweeps:
     ```bash
     celery -A app.core.celery_app worker -l info -Q default,notifications,calendar_sync,workflows -c 4
     celery -A app.core.celery_app beat -l info
     ```
2. **Cold-Start Sample Sizes:**
   - Agencies with fewer than 10 completed hires will operate in Tier 1 empirical Bayesian mode. The system transparently highlights preliminary confidence levels until additional hiring volume is established.
3. **AI Explanations Availability:**
   - AI strategic briefing falls back cleanly to deterministic template narratives if an LLM provider is not configured or temporarily unreachable.

---

## 10. Conclusion & Strict Stop Condition

Phase 12 is complete, fully tested, documented, and verified.
All operations honor the core principles: **evidence-driven forecasting, honest handling of uncertainty, and human-in-the-loop authority.**

Work has stopped cleanly. We await your explicit review and approval before proceeding to any future phases.
