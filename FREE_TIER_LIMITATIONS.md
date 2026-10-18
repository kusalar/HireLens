# HireLens AI — ₹0 Free-Tier Limitations & Operational Guide

**Hosting Environment:** Vercel Hobby + Render Free + Neon Free  
**Hosting Cost:** **₹0 / $0.00 (Zero Credit Card Required)**  
**Target:** Dev Week 2 Demonstration  

---

## 1. Executive Summary

This document transparently records every architectural limitation, resource ceiling, and operational constraint of running HireLens AI entirely within cloud free tiers.

By understanding these constraints and implementing the documented mitigations, you can present a reliable, high-fidelity demonstration to Dev Week 2 evaluators with **zero financial expenditure**.

---

## 2. Resource Constraints & Operational Mitigations

### 2.1 Render Free Web Service: 15-Minute Cold-Start Hibernation
- **Constraint:** Render's Free Web Service automatically spins down container instances after 15 minutes of zero incoming HTTP requests.
- **Evaluator Impact:** When an evaluator visits the demo after an idle window, the initial API call triggers container boot-up, taking **30 to 50 seconds** before the backend responds. Subsequent requests respond in under 100ms.
- **Recommended Free Mitigations:**
  1. **Pre-Warming:** Before sharing your demo link with an evaluator or entering an evaluation presentation, open `https://hirelens-api.onrender.com/health/ready` in your browser. This wakes the container and ensures the evaluator experiences instant response times.
  2. **Free Scheduled Uptime Ping:** Configure a free external ping service (e.g., [cron-job.org](https://cron-job.org) or [UptimeRobot](https://uptimerobot.com) — both 100% free with no credit card required) to send an HTTP GET request to `https://hirelens-api.onrender.com/health/live` every 10 minutes. This prevents the container from sleeping during the review period.

---

### 2.2 Neon Serverless PostgreSQL: 5-Minute Compute Suspension
- **Constraint:** Neon Free projects automatically suspend the compute endpoint after 5 minutes of inactivity (scale-to-zero) to conserve resources.
- **Evaluator Impact:** When a request arrives while compute is suspended, Neon takes approximately **500ms to 1000ms** to resume the database.
- **Codebase Mitigation Implemented:**
  - In `backend/app/db/session.py`, SQLAlchemy's connection pool has been explicitly configured with:
    - `pool_pre_ping=True`: Tests connection liveness with a lightweight query (`SELECT 1`) before execution. If the socket was closed by Neon's scale-to-zero, SQLAlchemy quietly discards it and reconnects without raising a 500 error to the user.
    - `pool_recycle=300`: Automatically recycles connections every 5 minutes to prevent stale TCP sockets.
    - `pool_size=5, max_overflow=10`: Keeps connection count well below Neon Free Tier's 100-connection limit.

---

### 2.3 Storage Limits & Local Container Ephemerality
- **Neon Free Storage:** 0.5 GiB (512 MB). The complete HireLens AI demo schema and synthetic demo dataset consume approximately **2.5 MB**, utilizing less than 0.5% of Neon's free capacity.
- **Render Ephemeral Filesystem:** When the Render container restarts or redeploys, any files saved to local disk (`./uploads`) are wiped.
- **Mitigation Implemented:**
  - The demo utilizes a dedicated synthetic data seeder (`seed_demo.py`).
  - All four candidate profiles (Elena Rostova, Marcus Vance, Priya Sharma, David Kim), their extracted skills, work histories, and multi-factor matching runs are pre-populated directly into PostgreSQL.
  - Evaluators can inspect candidate profiles and deep matching evidence without needing to upload new PDF files to ephemeral storage.

---

### 2.4 Background Workers (Celery & Redis Disabled)
- **Constraint:** To achieve ₹0 hosting cost, separate Render Background Workers and Redis instances are omitted (saving $17/month).
- **Evaluator Impact:** None.
  - Pre-computed matching runs provide instant access to score breakdowns and candidate evidence.
  - Real-time matching triggers utilize the sub-50ms deterministic rule engine (TF-IDF + weighted skill overlap), which executes synchronously inside the FastAPI process.

---

### 2.5 External Integrations in Mock Mode
- **Payment Processing (Razorpay & Stripe):** Operates with test keys and mock checkout handlers. Evaluators can navigate billing tiers and view invoices, but no real credit cards are charged.
- **Email Delivery:** Configured to `EMAIL_PROVIDER=console`. All notification and interview invite emails are written directly to the Render service stdout logs.
- **Calendar & OAuth:** Disabled. Demo recruiters authenticate via standard, secure JWT email/password login.

---

## 3. Comparison: Free Tier vs Paid Tier

| Feature / Metric | ₹0 Free Stack (Neon + Render + Vercel) | Commercial Production Tier |
|---|---|---|
| **Hosting Cost** | **₹0 / $0.00** | $25 – $75 / month |
| **Credit Card Required?** | **NO** | YES |
| **Cold-Start Delay** | 30–50s after 15 min idle (mitigated by pings) | 0s (Always-on containers) |
| **Database Auto-Deletion** | **NO (Neon retains data indefinitely)** | NO |
| **AI Matching Latency** | <50ms (Deterministic rule engine) | 1.5s – 3.0s (External LLM) |
| **Data Isolation & RBAC** | Fully Enforced (Agency-scoped) | Fully Enforced (Agency-scoped) |
| **Evaluator Experience** | Identical UI & Workflow | Identical UI & Workflow |

---

## 4. Evaluator Guidance Note

When presenting or sharing the demo with Dev Week 2 evaluators, you may include this brief performance note:

> *"HireLens AI is hosted on a high-efficiency serverless architecture targeting ₹0 infrastructure cost. If the demo has been idle, the initial page load may take approximately 30 seconds while the serverless containers initialize. All subsequent interactions will be instantaneous."*
