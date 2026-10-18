# HireLens AI — ₹0 Free-Tier Environment Variables Registry

**Architecture:** Vercel Hobby (Frontend) + Render Free (Backend) + Neon Free (Database)  
**Cost Commitment:** **₹0 / $0.00 — Zero Paid Subscriptions or Upgrades Required**  
**Classification:** Strict Security Isolation (Public Frontend vs Private Backend Secrets)  

---

## 1. Classification & Scope Boundaries

To ensure complete application security and zero information leakage, environment variables are partitioned into three distinct tiers:
1. **Tier 1: Safe Public Variables (Vercel Frontend)** — Inlined into browser bundles during Next.js compilation. Must **never** contain passwords, database URIs, or secret tokens.
2. **Tier 2: Backend-Only Application Secrets (Render Web Service)** — Stored securely in Render's encrypted environment store. Never exposed to browsers or API responses.
3. **Tier 3: Database Connection Credentials (Neon to Render)** — Encrypted connection string linking the Render API to Neon PostgreSQL.

---

## 2. Tier 1: Vercel Frontend Environment Variables (Public)

Configure these in the **Vercel Dashboard** under **Project Settings > Environment Variables**.

| Variable Name | Required | Target Envs | Is Secret? | Demo Recommendation | Purpose & Fallback Behavior |
|---|---|---|---|---|---|
| `NEXT_PUBLIC_API_URL` | **YES** | Production, Preview, Development | **NO** | `https://hirelens-api.onrender.com` | Base URL of your deployed Render backend. Must not have a trailing slash. If omitted, frontend defaults to `http://localhost:8000` (which breaks in production). |
| `NEXT_PUBLIC_APP_ENV` | Optional | Production, Preview | **NO** | `production` | Designates the runtime environment in headers or client-side telemetry. |
| `NEXT_PUBLIC_APP_NAME` | Optional | Production | **NO** | `HireLens AI` | Application brand name displayed across page headers and metadata tags. |

> [!WARNING]
> **Vercel Inlining Rule:** Do **not** place `DATABASE_URL`, `SECRET_KEY`, or any payment keys in Vercel. Next.js App Router only requires `NEXT_PUBLIC_API_URL`.

---

## 3. Tier 2: Render Backend Environment Variables (Private Secrets)

Configure these in the **Render Dashboard** under **Web Service > Environment**.

### 3.1 Core Security & Framework Settings

| Variable Name | Required | Is Secret? | ₹0 Demo Value | Technical Purpose & Fallback |
|---|---|---|---|---|
| `ENVIRONMENT` | **YES** | **NO** | `production` | Enforces production security headers and cookie protections. |
| `DEBUG` | **YES** | **NO** | `False` | Disables traceback dumps on HTTP 500 errors to prevent information disclosure. |
| `PROJECT_NAME` | Optional | **NO** | `HireLens AI` | Application identifier in OpenAPI/Swagger documentation (`/docs`). |
| `SECRET_KEY` | **YES** | **YES** | `[GENERATE_64_CHAR_HEX]` | Cryptographic key for signing HS256 JWT access tokens. Generate locally via: `python -c "import secrets; print(secrets.token_hex(32))"`. |
| `ALGORITHM` | Optional | **NO** | `HS256` | JWT signing algorithm. Default: `HS256`. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Optional | **NO** | `480` | Session lifetime (8 hours). Prevents evaluator session expiry during testing. |
| `BACKEND_CORS_ORIGINS` | **YES** | **NO** | `https://hirelens-demo.vercel.app` | Allowed CORS origins. The backend also includes built-in regex matching for `https://.*\.vercel\.app`. |

### 3.2 Database & Storage (Neon Integration)

| Variable Name | Required | Is Secret? | ₹0 Demo Value | Technical Purpose & Fallback |
|---|---|---|---|---|
| `DATABASE_URL` | **YES** | **YES** | *Paste Neon Pooled String* | Neon PostgreSQL connection string. Format: <br>`postgresql://neondb_owner:[PASSWORD]@[ENDPOINT]-pooler.[REGION].neon.tech/neondb?sslmode=require` |
| `STORAGE_BACKEND` | Optional | **NO** | `local` | Document store backend. Set to `local` to store uploads in container filesystem (`./uploads`). Free and requires zero external S3 buckets. |
| `UPLOAD_DIR` | Optional | **NO** | `./uploads` | Local directory for resume binaries. Created on startup. |

### 3.3 Artificial Intelligence & Matching (Zero-Cost Mode)

| Variable Name | Required | Is Secret? | ₹0 Demo Value | Technical Purpose & Fallback |
|---|---|---|---|---|
| `FALLBACK_RULE_ENGINE_ACTIVE` | **YES** | **NO** | `True` | **Critical for ₹0 demo:** Enables the deterministic mathematical matching engine (TF-IDF, rule weights, candidate score breakdowns). Delivers sub-50ms responses with **zero paid external API calls**. |
| `GEMINI_API_KEY` | **NO** | **YES** | *(Leave blank)* | Optional LLM key. When omitted, all matching, explanations, and copilot flows use the built-in deterministic rule engine at ₹0 cost. |

### 3.4 Payment Gateways (Mock Simulation — Zero Real Charges)

| Variable Name | Required | Is Secret? | ₹0 Demo Value | Technical Purpose & Fallback |
|---|---|---|---|---|
| `RAZORPAY_KEY_ID` | Optional | **NO** | `mock_rzp_key_placeholder` | Public test identifier. Operates in mock checkout mode. |
| `RAZORPAY_KEY_SECRET` | Optional | **YES** | `mock_rzp_secret_placeholder` | Mock signature validation. No live payments processed. |
| `STRIPE_PUBLISHABLE_KEY` | Optional | **NO** | `mock_stripe_pk_placeholder` | Disabled or test simulation mode. |
| `STRIPE_SECRET_KEY` | Optional | **YES** | `mock_stripe_sk_placeholder` | Disabled or test simulation mode. |

### 3.5 Email & Communications (Console Mock Logging)

| Variable Name | Required | Is Secret? | ₹0 Demo Value | Technical Purpose & Fallback |
|---|---|---|---|---|
| `EMAIL_PROVIDER` | Optional | **NO** | `console` | Outgoing notification emails are logged directly to the Render service stdout/logs with zero SMTP cost. |
| `EMAILS_FROM_EMAIL` | Optional | **NO** | `noreply@hirelens.ai` | From header in email templates. |
| `EMAILS_FROM_NAME` | Optional | **NO** | `HireLens AI Demo` | Sender display name. |

---

## 4. Ready-to-Copy Dashboard Templates

### Template A: Render Web Service Environment (Paste into Render Dashboard)
```env
# Application
ENVIRONMENT=production
DEBUG=False
PROJECT_NAME=HireLens AI
SECRET_KEY=REPLACE_WITH_GENERATED_64_CHAR_HEX
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=480
BACKEND_CORS_ORIGINS=https://hirelens-demo.vercel.app

# Database (Neon Serverless Pooled Connection)
DATABASE_URL=postgresql://neondb_owner:YOUR_NEON_PASSWORD@ep-plain-forest-a57q8f94-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require

# Zero-Cost AI & Storage
FALLBACK_RULE_ENGINE_ACTIVE=True
STORAGE_BACKEND=local
UPLOAD_DIR=./uploads

# Mock Integrations
RAZORPAY_KEY_ID=mock_rzp_key_placeholder
RAZORPAY_KEY_SECRET=dummy_secret_for_demo
EMAIL_PROVIDER=console
EMAILS_FROM_EMAIL=noreply@hirelens.ai
EMAILS_FROM_NAME=HireLens AI Demo
```

### Template B: Vercel Frontend Environment (Paste into Vercel Dashboard)
```env
NEXT_PUBLIC_API_URL=https://hirelens-api.onrender.com
NEXT_PUBLIC_APP_ENV=production
NEXT_PUBLIC_APP_NAME=HireLens AI
```

---

## 5. Security & Cost Audit Affirmation

- [x] Zero credit card details required for any service.
- [x] No live payment processing keys enabled.
- [x] No external paid LLM APIs required to execute candidate matches.
- [x] Database credentials restricted entirely to Render Web Service.
- [x] No credentials or keys in Vercel client bundle.
