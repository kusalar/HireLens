# HireLens AI — Deployment Audit: Vercel + Render Architecture

**System:** HireLens AI Platform  
**Target Repository:** `D:\HireLens`  
**Deployment Target:** Vercel (Frontend) + Render (Backend & Database)  
**Purpose:** Temporary Public Demo for Dev Week 2 Evaluators  
**Current Status:** Phases 1–15 Complete (100% Green Test Suite)  
**Audit Mode:** AUDIT & PREPARATION ONLY — NOT DEPLOYED  

---

## 1. Executive Summary

This audit evaluates the architectural readiness of HireLens AI for a temporary, public, multi-tenant demonstration hosted on **Vercel** (Next.js 14 frontend) and **Render** (FastAPI backend + hosted PostgreSQL).

### Key Architectural Findings:
1. **Frontend Architecture:** The Next.js 14 application in `frontend/` compiles cleanly across all 29 routes (`npm run build`). It communicates via a central API client in `frontend/lib/api.ts` that reads `NEXT_PUBLIC_API_URL`.
2. **Backend Architecture:** The FastAPI application in `backend/` serves an ASGI application at `app.main:app` with operational liveness (`/health/live`), readiness (`/health/ready`), and system health (`/health`) probes.
3. **Database Architecture:** Alembic maintains a single linear head (`9c0d1e2f3a4b`) covering all 15 phases. The schema has been verified on both SQLite and PostgreSQL 16/18.
4. **Authentication & Session Mechanics:** The application uses JWT Bearer tokens stored in client `localStorage` and sent via `Authorization: Bearer <token>` headers. Because it does not rely on cross-domain cookies for API authentication, cross-domain hosting (Vercel `*.vercel.app` -> Render `*.onrender.com`) functions without third-party cookie restrictions.
5. **AI Inference & Matching:** The core recruitment intelligence engine (deterministic scoring, skill normalization, TF-IDF semantic relevance, and match explanations) executes mathematical algorithms directly in Python without requiring external GPU hardware. In the absence of a local Ollama daemon, Copilot and match explanations fall back gracefully to the built-in deterministic rule-engine.
6. **Background Worker & Redis Requirement:** Redis and Celery are used for asynchronous resume parsing, calendar sync, and email outbox delivery. However, for a temporary evaluator demo, the platform operates safely with pre-seeded synthetic demonstration data; evaluator walkthroughs do not require a multi-node Celery cluster if demo records are pre-populated.

---

## 2. Repository & Component Inspection Matrix

| Inspection Area | Repository File / Directory | Inspected Property | Finding & Evaluation |
| :--- | :--- | :--- | :--- |
| **Frontend Root** | `D:\HireLens\frontend` | Root directory | Valid Next.js 14 project directory with `package.json`, `tailwind.config.ts`, and `app/` router. |
| **Frontend Framework** | `frontend/package.json` | Next.js version | Next.js `14.2.24`, React `18.3.1`, TypeScript `5.6.3`. Built with App Router architecture. |
| **Frontend Package Manager** | `frontend/package-lock.json` | Package manager | `npm` (v10+). Vercel auto-detects `package-lock.json` and uses `npm ci`. |
| **Backend Root** | `D:\HireLens\backend` | Root directory | Standard FastAPI directory structure (`app/`, `alembic/`, `tests/`, `requirements.txt`). |
| **Backend Entry Point** | `backend/app/main.py` | ASGI import path | `app.main:app`. Production Uvicorn command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`. |
| **Backend Python Version** | `backend/requirements.txt` | Python runtime | Python 3.11 (`3.11.9` local). Render native Python runtime supports Python 3.11. |
| **Database ORM & Driver** | `backend/app/db/session.py` | SQLAlchemy driver | SQLAlchemy 2.0.28+ with `psycopg2-binary>=2.9.9`. Requires `postgresql+psycopg2://` URL prefix. |
| **Alembic Migration Head** | `backend/alembic/versions/` | Migration graph | Exactly 1 head: `9c0d1e2f3a4b (head)`. 15 linear versions from Phase 1 to Phase 15. |
| **Health Probes** | `backend/app/main.py` | HTTP endpoints | `/health` (system), `/health/live` (liveness), `/health/ready` (`SELECT 1` DB readiness). |
| **CORS Middleware** | `backend/app/main.py` | Cross-origin headers | Configured with `BACKEND_CORS_ORIGINS` and regex `^https:\/\/.*\.vercel\.app$`. |
| **File Storage** | `backend/app/services/storage_service.py` | Resume storage | Local filesystem default (`./storage/resumes`). On Render, disk is ephemeral on free/starter tiers. |
| **AI Inference** | `backend/app/services/ai_provider_service.py` | Provider fallback | Supports `ollama`, `hosted_open_weight`, and deterministic rule-engine fallback. |
| **Celery Tasks** | `backend/app/tasks/` | Background jobs | 7 task modules (`resume_tasks`, `calendar_tasks`, `notification_tasks`, etc.). Non-blocking. |

---

## 3. Vercel Frontend Readiness Audit

### 3.1 Build & Routing Compatibility
- **Build Execution:** Tested locally with `npm run build` in `frontend/`. All 29 routes compile into optimized standalone production bundles with **0 errors**.
- **Static vs Dynamic Routes:**
  - 19 Static Pages (`/`, `/login`, `/register`, `/dashboard`, `/candidates`, `/jobs`, `/interviews`, `/settings`, `/admin`, etc.)
  - 10 Dynamic Pages (`/applications/[id]`, `/candidates/[id]`, `/interviews/[id]`, `/jobs/[id]/matches`, `/resumes/[id]`, etc.)
- **Direct Navigation / Refresh:** Because Next.js App Router uses standard HTML5 pushState and file-system routing, direct URL navigation and page reloads on Vercel resolve cleanly without 404 rewrite issues.

### 3.2 Environment Variable & API Wiring
- **Central API Client:** [frontend/lib/api.ts](file:///D:/HireLens/frontend/lib/api.ts#L1) defines:
  ```typescript
  const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000/api/v1";
  ```
- **Build-Time Variable Inlining:** Next.js embeds `NEXT_PUBLIC_*` variables into the JavaScript bundle **at build time**.
  > [!IMPORTANT]
  > `NEXT_PUBLIC_API_URL` must be added in the Vercel Dashboard **before** triggering the initial production build. Setting it after the build requires triggering a redeployment.
- **Hardcoded Localhost Audit:** Inspected all components. `http://localhost:8000` is used strictly as a fallback in 3 resume download handlers if `NEXT_PUBLIC_API_URL` is omitted. When `NEXT_PUBLIC_API_URL` is provided, all requests route to the production backend.

### 3.3 Authentication & Cross-Origin Security
- Authentication tokens are stored in `localStorage` under key `hirelens_access_token` and passed as HTTP request headers (`Authorization: Bearer <token>`).
- Cross-origin isolation issues associated with third-party cookie blocking (e.g. Chrome Privacy Sandbox, Safari ITP) do not affect HireLens AI.

---

## 4. Render Backend Readiness Audit

### 4.1 Runtime & Dependency Installation
- **Python Runtime:** Render defaults to Python 3.11 when building Python services.
- **Dependencies:** `backend/requirements.txt` specifies `psycopg2-binary>=2.9.9`. On Render's Ubuntu Linux environment, `psycopg2-binary` installs pre-compiled C wheels, eliminating the need for system-level `libpq-dev` compilation packages.
- **Build Command:**
  ```bash
  pip install --upgrade pip && pip install -r requirements.txt
  ```

### 4.2 Port Binding & Start Command
- Render injects an ephemeral port via the `$PORT` environment variable (default: `10000`).
- FastAPI must bind to `0.0.0.0` and listen on `$PORT`.
- **Start Command:**
  ```bash
  uvicorn app.main:app --host 0.0.0.0 --port $PORT
  ```

### 4.3 Database Connection & Driver Normalization
- Render provides PostgreSQL connection strings in the format `postgresql://...` or `postgres://...`.
- In SQLAlchemy 2.0, bare `postgresql://` requires the `psycopg` (v3) library, while `postgres://` raises `NoSuchModuleError`.
- **Hardening Applied:** [backend/app/core/config.py](file:///D:/HireLens/backend/app/core/config.py#L17) incorporates an automatic `@field_validator` that transparently normalizes incoming connection strings to `postgresql+psycopg2://`, preventing startup crashes when database credentials are pasted directly from Render.

### 4.4 CORS Allowlist
- Cross-Origin Resource Sharing is enforced in `app/main.py`.
- **Regex Protection Added:** `allow_origin_regex=r"^https:\/\/.*\.vercel\.app$"` automatically permits any Vercel deployment URL (including preview builds and production domains) without requiring manual CORS reconfiguration.

---

## 5. Background Jobs & Redis Architecture

| Architecture Option | Components | Pros | Cons / Tradeoffs | Recommendation for Dev Week 2 |
| :--- | :--- | :--- | :--- | :--- |
| **Option 1: Lean API + Pre-Seeded Data** | Render Web Service + Render PostgreSQL | $0 cost, zero complexity, zero cold-start race conditions. All demo candidates, scores, and pipelines are pre-computed. | Newly uploaded resumes during live walkthrough remain in `QUEUED` status unless processed synchronously. | **RECOMMENDED FOR DEV WEEK 2** |
| **Option 2: Full Cluster with Celery & Redis** | Web Service + Render Redis ($10/mo) + Render Background Worker ($7/mo) | Background workers process newly uploaded resumes and calendar tasks in real time. | Requires 3 separate Render services; potential free-tier instance-hour exhaustion; extra operational surface. | Optional upgrade if live bulk upload demonstration is mandatory. |

---

## 6. Audit Verdict

| Component | Audit Status | Evidence |
| :--- | :--- | :--- |
| **Frontend (Vercel)** | **READY** | 29/29 routes build cleanly; `NEXT_PUBLIC_API_URL` configuration verified; bearer token auth confirmed. |
| **Backend (Render)** | **READY** | Port binding, Uvicorn start command, dependencies, and health probes verified. |
| **Database (PostgreSQL)** | **READY** | Single Alembic head `9c0d1e2f3a4b`; automatic driver normalization to `postgresql+psycopg2://` active. |
| **CORS & Networking** | **READY** | Vercel domain regex allowlist active; comma/JSON origin parsing supported. |
| **AI Intelligence** | **READY** | Deterministic rule-engine active; matching and explanations function without external GPU. |
| **Security & Privacy** | **READY** | Multi-tenant isolation enforced; platform super-admin protected; zero credentials committed. |

**OVERALL AUDIT VERDICT: READY FOR DEMO PREPARATION (AWAITING OPERATOR CLOUD CREATION)**
