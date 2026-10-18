# HireLens AI — Phase 12: Architecture & Integration Audit
**Predictive Recruitment Intelligence & Workforce Planning**

**Project:** HireLens AI  
**Workspace:** `D:\HireLens`  
**Date:** October 2026  
**Author:** Principal AI Architect, Senior Backend Engineer, Data Scientist, Application Security Auditor  
**Status:** Audit Completed & Approved for Implementation  
**Current Migration Head:** `6f7a8b9c0d1e` (Phase 11)

---

## 1. Executive Summary & Objective

Phase 12 elevates HireLens from an automated operational workflow platform into an **enterprise-grade predictive recruitment intelligence and workforce planning system**. The objective is to equip agency owners, talent acquisition leaders, and recruiters with forward-looking intelligence:

1. **Time-to-Hire Forecasting:** Quantify expected completion timelines for open job requisitions based on seniority, department, historical agency performance, and current stage distribution, accompanied by statistical confidence intervals.
2. **Hiring Demand Forecasting:** Forecast requisition demand, application inflow, and talent acquisition needs over 30, 60, and 90-day forward horizons.
3. **Recruitment Bottleneck Prediction:** Detect emerging stagnation in specific pipeline stages (e.g., technical round scheduling delays, recruiter response lags) before they cause candidate drop-off.
4. **Recruitment Risk Intelligence:** Automatically uncover and catalog actionable risks: pipeline insufficiency, candidate drop-off vulnerability, stage stagnation, and cost overruns.
5. **Recruiter Capacity Planning:** Provide operational capacity analytics (active candidates, upcoming interviews, open requisitions per recruiter) and non-autonomous workload redistribution recommendations.
6. **Model Governance & Explainability:** Track model versions, training timestamps, dataset sample sizes, and validation metrics (MAE, RMSE, R2) with grounded natural-language explanations powered by the Phase 10 AI provider.

### Core Architectural Principle
> **"Provide evidence-driven, explainable predictive intelligence with honest handling of uncertainty, while preserving human authority over all hiring and workload decisions."**

Predictions must never autonomously hire, reject, rank candidates, or reassign recruiters.

---

## 2. Audit of Existing Infrastructure & Reusable Assets

To maintain architectural cohesion and avoid duplication, Phase 12 reuses existing foundational services from Phases 1–11:

| Phase | Capability | Integration & Reuse in Phase 12 |
|---|---|---|
| **Phase 1** | RBAC & Agency Multi-Tenancy | Agency-scoped tenant isolation (`agency_id`) across all forecast tables, risks, models, and capacity snapshots. Enforces `OWNER` / `ADMIN` permissions for model re-training and refresh, while `RECRUITER` and `VIEWER` have read-only access. |
| **Phase 4** | Deterministic Matching Engine | Uses candidate match scores and requirement weights to detect low-quality pipeline risks (e.g., requisitions lacking demonstrated candidates). |
| **Phase 5** | Pipeline & Stage History | Uses `ApplicationStageHistory` timestamps to calculate exact historical cycle times, stage transition probabilities, and survival/stagnation distributions. |
| **Phase 6 & 9** | Interview & Calendar Services | Uses scheduled interviews, confirmed rounds, and calendar sync status to evaluate upcoming recruiter workloads and detect scheduling delays. |
| **Phase 7** | Notification Outbox | Triggers critical risk notifications via transactional `NotificationOutbox` when high-severity bottlenecks or pipeline deficits are discovered. |
| **Phase 8** | Analytics & Cost Repositories | Reuses `AnalyticsRepository` SQL aggregations and `RecruitmentExpense` data to forecast cost-per-hire and detect recruitment expense overruns. |
| **Phase 10** | AI Copilot & Provider Abstraction | Integrates `get_ai_provider` (`OllamaProvider`, `HostedOpenWeightProvider`) to generate structured explanations of forecasts, risks, and capacity recommendations without metric hallucination. |
| **Phase 11** | Workflow Automation & Tasks | Emits workflow events or creates `RecruiterTask` action items when critical recruitment risks require recruiter attention. |
| **Core** | Timezone Standard (`Asia/Kolkata`) | Reuses `app.core.timezone` (`DEFAULT_ZONEINFO`, `format_ist`, `convert_utc_to_timezone`) for all 30/60/90-day forecasting bounds, dashboard presentations, and UTC persistence. |
| **Core** | Celery & Redis Infrastructure | Reuses Celery app worker and beat scheduler to execute asynchronous forecast model re-training and periodic risk evaluation sweeps. |

---

## 3. Predictive Model Architecture & Methodology

Phase 12 employs a **hybrid architecture** combining deterministic statistical priors with machine learning estimators (`scikit-learn`), strictly ensuring graceful degradation when historical data is scarce.

### A. Honest Data Handling & Sample Size Tiers
Recruitment agencies exhibit varying historical data volumes. Fabricating data or running deep models on five data points is strictly prohibited:

1. **Cold Start / Sparse Tier ($N < 10$ historical hires):**
   - Pure deterministic statistical model using empirical Bayesian priors (industry/agency baseline medians, standard deviations, and stage-duration benchmarks).
   - Model explicitly sets `is_baseline_fallback = True`, confidence level = `LOW` or `PRELIMINARY`, with clear user-facing notices indicating insufficient historical sample size.
2. **Intermediate Tier ($10 \le N < 50$ historical hires):**
   - Weighted rolling averages and exponential smoothing (Holt-Winters / trend-adjusted moving averages) for demand.
   - Stage duration survival analysis (Kaplan-Meier-inspired empirical cumulative distribution functions) for bottleneck detection.
   - Linear / Ridge regression for time-to-hire prediction with feature weighting on job department, seniority, and stage count.
3. **Mature Tier ($N \ge 50$ historical hires):**
   - Multi-variate `scikit-learn` estimators (`RandomForestRegressor`, `GradientBoostingRegressor`, `Ridge`) trained on engineered features:
     - Requisition department, seniority level, number of requirements.
     - Sourcing channel distribution and initial candidate volume.
     - Current pipeline depth across active stages.
   - Cross-validated evaluation metrics (MAE, RMSE, $R^2$) logged in `prediction_model_versions`.

### B. Time-to-Hire Forecasting Mechanics
- Expected remaining time for an active job $j$:
  $$\widehat{T}_j = \sum_{s \in \text{Remaining Stages}} \widehat{d}_s \cdot P(\text{Transition} \mid s)$$
  adjusted by job complexity features and historical velocity.
- **Confidence Intervals (80% and 95%):**
  $$\text{CI}_{95\%} = \widehat{T}_j \pm 1.96 \cdot \text{SE}_{\text{model}}$$
  Distinguishes predicted duration from historical agency averages.

### C. Hiring Demand Forecasting (30, 60, 90 Days)
- Forecasts new requisitions and application volume per department using:
  - Seasonality-aware linear trend decomposition: $Y_t = T_t + S_t + \epsilon_t$.
  - Historical requisition opening velocity across prior quarters.
  - Sourcing conversion ratios to forecast needed candidate volume.

### D. Prevention of Data Leakage
- Chronological train/test splitting: Models are trained only on completed historical applications prior to the forecast cutoff date.
- Active (in-flight) applications are strictly reserved for inference, never used as training targets.
- All metrics (time-to-hire, drop-off rates) exclude currently uncompleted records to prevent right-censoring bias.

---

## 4. Recruiter Capacity & Workload Balancing

Calculates operational load index per recruiter:
$$\text{Workload Score} = w_{\text{apps}} \cdot N_{\text{active apps}} + w_{\text{interviews}} \cdot N_{\text{upcoming interviews}} + w_{\text{jobs}} \cdot N_{\text{open jobs}}$$
- **Imbalance Detection:** Identifies recruiters whose workload score deviates by $> 1.5$ standard deviations from the agency mean.
- **Advisory Capacity Recommendations:** Recommends specific load-leveling actions (e.g., assigning new incoming requisitions to under-utilized recruiters), accompanied by a prominent warning that reassignments require human decision-making.

---

## 5. Recruitment Risk Intelligence Engine

Scans active agency pipeline telemetry and raises structured records in `recruitment_risks`:

| Risk Code | Risk Category | Trigger Conditions | Severity | Recommended Operational Action |
|---|---|---|---|---|
| `RISK_PIPELINE_DEFICIT` | Pipeline Insufficiency | Active applications $< 3 \times$ target hires after 14 days active. | HIGH / CRITICAL | Launch sourcing campaigns or expand job board posting. |
| `RISK_STAGE_STAGNATION` | Stage Stagnation | Applications in `UNDER_REVIEW` or `INTERVIEW` exceeding 2x stage median duration. | MEDIUM / HIGH | Review stagnant applications and expedite scheduling. |
| `RISK_DROP_OFF_VULNERABILITY` | Candidate Drop-off | High-match candidate ($>80\%$) inactive for $>7$ days without scheduled next round. | HIGH | Prompt recruiter to schedule next interview immediately. |
| `RISK_SCHEDULING_BOTTLENECK` | Interview Delays | Average time from shortlist to interview scheduled $> 8$ days in department. | MEDIUM | Add interviewer availability or allocate backup interviewers. |
| `RISK_EXPENSE_OVERRUN` | Budget / Cost Overrun | Current expenses for job exceed 120% of department average cost-per-hire. | MEDIUM / HIGH | Audit job board spend and optimize sourcing channels. |

---

## 6. Database Entity Architecture

All entities reside in `backend/app/models/predictive.py` with foreign keys, compound indexes, and `agency_id` tenant isolation:

1. **`PredictionModelVersion`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`)
   - `model_type` (Enum: `TIME_TO_HIRE`, `HIRING_DEMAND`, `STAGE_DURATION`, `CANDIDATE_DROP_OFF`)
   - `algorithm` (String: `RIDGE_REGRESSION`, `RANDOM_FOREST`, `EXPONENTIAL_SMOOTHING`, `BASELINE_EMPIRICAL`)
   - `version_tag` (String: e.g. `v1.2.0-20261017`)
   - `training_sample_size` (Integer)
   - `evaluation_metrics` (JSONB: `{ "mae": 4.2, "rmse": 5.8, "r2": 0.76 }`)
   - `hyperparameters` (JSONB)
   - `feature_names` (JSONB)
   - `is_active` (Boolean)
   - `trained_at`, `created_at` (DateTime TZ)

2. **`RecruitmentForecast`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `job_id` (UUID, FK -> `jobs.id`, nullable)
   - `department` (String, nullable)
   - `forecast_type` (Enum: `TIME_TO_HIRE`, `DEMAND_30D`, `DEMAND_60D`, `DEMAND_90D`, `APPLICATION_VOLUME`)
   - `predicted_value` (Float)
   - `confidence_lower` (Float)
   - `confidence_upper` (Float)
   - `confidence_level` (String: `HIGH`, `MEDIUM`, `LOW`, `PRELIMINARY`)
   - `is_baseline_fallback` (Boolean)
   - `explanation` (Text)
   - `factors` (JSONB)
   - `model_version_id` (UUID, FK -> `prediction_model_versions.id`)
   - `horizon_days` (Integer)
   - `forecast_date` (DateTime TZ)
   - `created_at` (DateTime TZ)

3. **`RecruitmentRisk`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `risk_type` (Enum: `PIPELINE_DEFICIT`, `STAGE_STAGNATION`, `DROP_OFF_VULNERABILITY`, `SCHEDULING_BOTTLENECK`, `EXPENSE_OVERRUN`)
   - `severity` (Enum: `CRITICAL`, `HIGH`, `MEDIUM`, `LOW`)
   - `status` (Enum: `OPEN`, `ACKNOWLEDGED`, `MITIGATED`, `DISMISSED`)
   - `title` (String(255))
   - `description` (Text)
   - `job_id` (UUID, FK -> `jobs.id`, nullable)
   - `candidate_id` (UUID, FK -> `candidates.id`, nullable)
   - `application_id` (UUID, nullable)
   - `recruiter_id` (UUID, nullable)
   - `evidence_payload` (JSONB)
   - `recommended_action` (Text)
   - `confidence_score` (Float)
   - `acknowledged_by_user_id` (UUID, nullable)
   - `detected_at`, `resolved_at`, `created_at` (DateTime TZ)

4. **`CapacitySnapshot`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`, indexed)
   - `recruiter_id` (UUID, FK -> `users.id`)
   - `active_applications_count` (Integer)
   - `upcoming_interviews_count` (Integer)
   - `open_requisitions_count` (Integer)
   - `workload_index` (Float)
   - `utilization_status` (Enum: `OPTIMAL`, `OVERLOADED`, `UNDERUTILIZED`)
   - `recommendations` (JSONB)
   - `snapshot_date` (DateTime TZ)
   - `created_at` (DateTime TZ)

5. **`ForecastEvaluation`**:
   - `id` (UUID, PK)
   - `agency_id` (UUID, FK -> `agencies.id`)
   - `forecast_id` (UUID, FK -> `recruitment_forecasts.id`)
   - `actual_value` (Float)
   - `absolute_error` (Float)
   - `percentage_error` (Float)
   - `evaluated_at` (DateTime TZ)

---

## 7. Migration Plan

- **New Migration:** `7a8b9c0d1e2f_add_phase_12_predictive_intelligence_models.py`
- **Down Revision:** `6f7a8b9c0d1e` (Phase 11)
- **Validation:** Test `alembic upgrade head`, `alembic downgrade -1`, and re-upgrade to ensure single migration head and clean reversibility.

---

## 8. API Architecture (`/api/v1/predictive-analytics`)

| Method | Endpoint | Description | RBAC |
|---|---|---|---|
| `GET` | `/overview` | Executive predictive intelligence summary, KPI cards, and critical risk counters | All Agency Users |
| `GET` | `/time-to-hire` | Requisition-specific and department-level time-to-hire forecasts with confidence intervals | All Agency Users |
| `GET` | `/demand` | 30/60/90-day recruitment demand and application volume projections | All Agency Users |
| `GET` | `/bottlenecks` | Pipeline stage stagnation analysis and interview scheduling delay radar | All Agency Users |
| `GET` | `/risks` | Filterable recruitment risk register with severity badges and evidence | All Agency Users |
| `PATCH` | `/risks/{id}` | Acknowledge, mitigate, or dismiss a recruitment risk | OWNER, ADMIN, RECRUITER |
| `GET` | `/capacity` | Recruiter workload distribution, capacity indices, and load-leveling advice | All Agency Users |
| `GET` | `/models` | Model registry: training versions, algorithms, sample sizes, and accuracy metrics | All Agency Users |
| `POST` | `/refresh` | Trigger on-demand recalculation of forecasts and risk detection | OWNER, ADMIN |

---

## 9. Security, Privacy & Bias Safeguards

1. **Strict Multi-Tenancy:** All queries and training datasets are partitioned strictly by `agency_id`. Cross-tenant data aggregation is blocked at the database and repository layers.
2. **Bias Protection:** Models **never** ingest or evaluate protected characteristics (Age, Gender, Race, Caste, Religion, Marital Status).
3. **Privacy Integrity:** Private interviewer comments and candidate PII are never encoded into model features or exposed in risk descriptions.
4. **No Autonomous Hiring Decisions:** Predictions and risk flags are purely informational and advisory. No candidate is rejected, moved, or hired without human agency review.

---

## 10. Audit Conclusion

The existing Phase 1–11 codebase provides solid foundations (`AnalyticsRepository`, `CopilotService`, `NotificationOutbox`, `CeleryApp`, `Asia/Kolkata` timezones). The Phase 12 architecture strictly reuses these assets, adds honest and robust statistical/ML models, enforces tenant isolation and RBAC, and delivers a polished frontend predictive intelligence workspace.

**Stage 1 Audit is hereby concluded. Proceed to Stage 2: Database Models & Migrations.**
