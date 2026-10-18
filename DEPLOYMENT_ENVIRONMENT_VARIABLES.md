# HireLens AI — Deployment Environment Variables Registry

**Project:** `D:\HireLens`  
**Deployment Target:** Vercel (Frontend) + Render (Backend & Database)  
**Target Environment:** Temporary Public Demo for Dev Week 2  
**Security Classification:** Strict — No Actual Secret Values Documented  

---

## 1. Overview & Security Rules

This document establishes the definitive environment variable catalog for deploying HireLens AI to Vercel (Next.js frontend) and Render (FastAPI backend + PostgreSQL).

### Critical Safety Principles
1. **Never commit actual secrets:** This registry provides variable names, types, descriptions, safe placeholder patterns, and default fallbacks.
2. **Build-Time Inlining:** Next.js embeds all `NEXT_PUBLIC_*` variables into client-side JavaScript bundles during `npm run build`. Never place sensitive keys (API secrets, private tokens, passwords) in `NEXT_PUBLIC_*` variables.
3. **Database URL Normalization:** Render provides PostgreSQL connection strings with `postgres://` or bare `postgresql://`. The HireLens backend configuration (`backend/app/core/config.py`) automatically translates these to `postgresql+psycopg2://` at runtime.
4. **Tenant & Demo Protection:** Demo credentials must be injected securely via platform environment variables or generated using the idempotent database seed script (`python -m app.db.seed_demo`).

---

## 2. Vercel Frontend Environment Variables

Configure these variables in the **Vercel Project Dashboard** under **Settings > Environment Variables**.

| Variable Name | Required | Target Env | Is Secret? | Description & Value Guidance | Default / Fallback if Omitted |
|---|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **YES** | Production, Preview, Development | **NO** | Base URL of the deployed FastAPI backend. Must include protocol and no trailing slash. <br>Example: `https://hirelens-api.onrender.com` | `http://localhost:8000` (Will fail in production if omitted) |
| `NEXT_PUBLIC_APP_ENV` | Optional | Production, Preview | **NO** | Current frontend environment indicator for UI badges or logging. <br>Recommended: `production` | `development` |
| `NEXT_PUBLIC_APP_NAME` | Optional | Production | **NO** | Display name for the application in headers and titles. <br>Recommended: `HireLens AI` | `HireLens AI` |

> [!IMPORTANT]
> **Vercel Build Requirement:** In Next.js App Router, `NEXT_PUBLIC_API_URL` is baked into static assets during build time. Set this variable in Vercel **before** triggering the initial production build. If changed later, a redeployment (with cleared cache) is required.

---

## 3. Render Backend Environment Variables

Configure these variables in the **Render Dashboard** under **Web Service > Environment > Environment Variables**.

### 3.1 Core Application & Security

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `PROJECT_NAME` | Optional | **NO** | `HireLens AI` | Application title reported in Swagger UI and OpenAPI schemas. Default: `HireLens` |
| `ENVIRONMENT` | **YES** | **NO** | `production` | Runtime mode. Disables mock authentication bypasses and enforces strict security headers. Default: `development` |
| `DEBUG` | **YES** | **NO** | `False` | Disables verbose exception tracebacks in public HTTP responses to prevent information leakage. |
| `SECRET_KEY` | **YES** | **YES** | `[GENERATE_64_CHAR_HEX]` | High-entropy cryptographic key used for signing JWT access tokens and session cookies. Generate via: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ALGORITHM` | Optional | **NO** | `HS256` | JWT signing algorithm. Default: `HS256` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | **NO** | `480` | Access token lifespan in minutes. Recommended: 8 hours (`480`) for evaluator convenience during testing. Default: `60` |
| `BACKEND_CORS_ORIGINS` | **YES** | **NO** | `https://hirelens-demo.vercel.app` *(or comma-separated URLs)* | Allowed CORS origins. Can be provided as a comma-separated list or JSON array. Note: The backend also contains built-in regex matching for `https://.*\.vercel\.app`. |

### 3.2 Database & Storage

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `DATABASE_URL` | **YES** | **YES** | Render PostgreSQL Connection String | Connection string provided by Render PostgreSQL. Use the **Internal Database URL** if the database is in the same Render region, or the **External Database URL** if connecting cross-region/externally. <br>Format: `postgresql://user:pass@dpg-xxx-a:5432/hirelens_demo` |
| `STORAGE_BACKEND` | Optional | **NO** | `local` | Resume and document storage provider. `local` uses the container filesystem (`/tmp/uploads` or `./uploads`). For temporary demo, pre-seeded candidate data does not require object storage. |
| `UPLOAD_DIR` | Optional | **NO** | `./uploads` | Directory for uploaded resume binaries. Created automatically on container startup if it does not exist. |

### 3.3 Artificial Intelligence & Matching

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `GEMINI_API_KEY` | Optional | **YES** | *(Leave blank or provide developer key)* | API key for Google Gemini model inference (match explanations and Copilot assistance). |
| `GEMINI_MODEL` | Optional | **NO** | `gemini-1.5-flash` | Selected Gemini model variant. |
| `FALLBACK_RULE_ENGINE_ACTIVE` | Optional | **NO** | `True` | **Critical for demo stability:** When enabled, if `GEMINI_API_KEY` is absent or rate-limited, all match scoring, skill matching, and candidate breakdowns automatically fall back to the deterministic math/rule engine with zero evaluator errors. |

### 3.4 Payment Gateways (Mock/Test Mode Only)

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `RAZORPAY_KEY_ID` | Optional | **NO** | `rzp_test_placeholder_key` | Public test key. Application operates in mock payment mode if dummy keys are supplied. |
| `RAZORPAY_KEY_SECRET` | Optional | **YES** | `dummy_secret_for_demo` | Secret test key for HMAC verification. |
| `STRIPE_API_KEY` | Optional | **YES** | `sk_test_placeholder_key` | Stripe secret key. Disabled or test mode. |
| `STRIPE_WEBHOOK_SECRET` | Optional | **YES** | `whsec_dummy_secret` | Webhook signing key. |

> [!NOTE]
> For the Dev Week 2 evaluation, payment billing is fully configured with simulated webhook event handlers and mock order generators. No live charges will occur.

### 3.5 Email & Communications (Safe Console Mocking)

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `SMTP_HOST` | Optional | **NO** | `localhost` | Mail server host. When pointing to localhost or non-existent server, notification services gracefully log outgoing emails to stdout/console. |
| `SMTP_PORT` | Optional | **NO** | `1025` | Mail server port. |
| `SMTP_USER` | Optional | **NO** | `demo@hirelens.ai` | Sender username. |
| `SMTP_PASSWORD` | Optional | **YES** | `dummy_smtp_password` | Mail password. |
| `EMAILS_FROM_EMAIL` | Optional | **NO** | `noreply@hirelens.ai` | From address header. |
| `EMAILS_FROM_NAME` | Optional | **NO** | `HireLens AI Demo` | Display sender name. |

### 3.6 Calendar & OAuth (Disabled for Demo)

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `GOOGLE_CLIENT_ID` | Optional | **NO** | *(Leave empty)* | Google OAuth client ID. Disabled for demo; email/password authentication is used. |
| `GOOGLE_CLIENT_SECRET` | Optional | **YES** | *(Leave empty)* | Google OAuth secret. |
| `MICROSOFT_CLIENT_ID` | Optional | **NO** | *(Leave empty)* | Microsoft Entra client ID. Disabled for demo. |
| `MICROSOFT_CLIENT_SECRET` | Optional | **YES** | *(Leave empty)* | Microsoft Entra client secret. |

### 3.7 Background Workers & Redis (Optional / Not Required for Demo)

| Variable Name | Required | Is Secret? | Demo Recommendation | Description & Fallback |
|---|---|---|---|---|
| `REDIS_URL` | Optional | **YES** | *(Leave empty)* | Celery broker / Redis cache URL. Since the demo uses pre-computed matching and synchronous fallback services, a separate Redis container is **not required**. |
| `CELERY_BROKER_URL` | Optional | **YES** | *(Leave empty)* | Celery task queue broker. |
| `CELERY_RESULT_BACKEND` | Optional | **YES** | *(Leave empty)* | Celery task result backend. |

---

## 4. Render Database Environment Variables

When creating the **Render PostgreSQL** instance, the dashboard generates these variables automatically:

| Variable | Description |
|---|---|
| `Internal Database URL` | High-speed connection string for services hosted in the same Render region: <br>`postgres://hirelens_db_user:[PASSWORD]@dpg-[INSTANCE_ID]-a/hirelens_demo` |
| `External Database URL` | Secure SSL connection string for external access (e.g., local Alembic migrations or pg_dump): <br>`postgres://hirelens_db_user:[PASSWORD]@dpg-[INSTANCE_ID]-a.frankfurt-postgres.render.com/hirelens_demo` |
| `Host` | Internal/External hostname |
| `Port` | `5432` |
| `Database` | `hirelens_demo` |
| `User` | `hirelens_db_user` |
| `Password` | Auto-generated secure alphanumeric string |

---

## 5. Ready-to-Copy Environment Templates

### Template A: Render Web Service Environment (.env format)
```env
# --- Application Core ---
PROJECT_NAME=HireLens AI
ENVIRONMENT=production
DEBUG=False
SECRET_KEY=REPLACE_WITH_GENERATED_64_CHAR_HEX
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
BACKEND_CORS_ORIGINS=https://hirelens-demo.vercel.app

# --- Database ---
# Paste the Render Internal Database URL here:
DATABASE_URL=postgres://hirelens_user:SECRET@dpg-xxx-a:5432/hirelens_demo

# --- Storage & AI ---
STORAGE_BACKEND=local
UPLOAD_DIR=./uploads
FALLBACK_RULE_ENGINE_ACTIVE=True
# Optional Gemini Key (Leave commented out to use deterministic rule engine):
# GEMINI_API_KEY=AIzaSy...

# --- Mock Gateways (No Live Charges) ---
RAZORPAY_KEY_ID=rzp_test_demo_placeholder
RAZORPAY_KEY_SECRET=rzp_secret_demo_placeholder
EMAILS_FROM_EMAIL=demo@hirelens.ai
EMAILS_FROM_NAME=HireLens AI Demo
```

### Template B: Vercel Frontend Environment (.env format)
```env
NEXT_PUBLIC_API_URL=https://hirelens-api.onrender.com
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_APP_NAME=HireLens AI
```

---

## 6. Verification Checklist

- [ ] `NEXT_PUBLIC_API_URL` contains no trailing slash.
- [ ] `SECRET_KEY` on Render is a fresh, 64-character random hex string.
- [ ] `DEBUG` is strictly set to `False` on the backend.
- [ ] `DATABASE_URL` connects to the newly created Render PostgreSQL instance, not a local or development database.
- [ ] No payment gateway live keys or production mail server credentials are present.
- [ ] `BACKEND_CORS_ORIGINS` reflects the public Vercel domain.
