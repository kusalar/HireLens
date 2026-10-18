# HireLens AI — Phase 15: Production Deployment & Operations Guide

**System:** HireLens AI Platform  
**Target Workspace:** `D:\HireLens`  
**Current Date:** October 17, 2026  
**Status:** Enterprise Production Ready  

---

## 1. Production Architecture Overview

HireLens AI is designed as a cloud-native, multi-tenant recruitment SaaS platform structured into containerized microservices:

```
                          ┌──────────────────────────┐
                          │   Internet / Cloudflare  │
                          └─────────────┬────────────┘
                                        │ (HTTPS / TLS 1.3)
                                        ▼
                          ┌──────────────────────────┐
                          │   Reverse Proxy / Ingress│
                          │      (Nginx / Traefik)   │
                          └──────┬────────────┬──────┘
                                 │            │
             ┌───────────────────┘            └───────────────────┐
             ▼ (Port 3000)                                        ▼ (Port 8000)
┌──────────────────────────┐                          ┌──────────────────────────┐
│   hirelens-frontend      │                          │   hirelens-backend       │
│   (Next.js 14 App Server)│                          │   (FastAPI / Uvicorn)    │
└──────────────────────────┘                          └──────┬────────────┬──────┘
                                                             │            │
                                       ┌─────────────────────┘            └─────────────────────┐
                                       ▼                                                        ▼
                        ┌──────────────────────────┐                             ┌──────────────────────────┐
                        │   hirelens-postgres      │                             │   hirelens-redis         │
                        │   (PostgreSQL 16 Cluster)│                             │   (Redis 7 Task Broker)  │
                        └──────────────────────────┘                             └──────┬────────────┬──────┘
                                                                                        │            │
                                                                  ┌─────────────────────┘            └─────────────────────┐
                                                                  ▼                                                        ▼
                                                   ┌──────────────────────────┐                             ┌──────────────────────────┐
                                                   │  hirelens-celery-worker  │                             │  hirelens-celery-beat    │
                                                   │  (Async Task Execution)  │                             │  (Periodic Schedulers)   │
                                                   └──────────────────────────┘                             └──────────────────────────┘
```

---

## 2. Docker & Container Orchestration

### 2.1 Backend Container (`backend/Dockerfile`)
The backend is built using `python:3.11-slim`, with non-root runtime best practices:
```dockerfile
FROM python:3.11-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 2.2 Frontend Container (`frontend/Dockerfile`)
The frontend uses a two-stage build (Builder & Runner) using `node:20-alpine` producing an optimized production bundle:
```dockerfile
FROM node:20-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .
RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /app/package*.json ./
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/public ./public
COPY --from=builder /app/node_modules ./node_modules
EXPOSE 3000
CMD ["npm", "run", "start"]
```

### 2.3 Docker Compose Orchestration (`docker-compose.yml`)
To start the complete production-like stack locally or on a single host:
```bash
docker compose up -d --build
```

---

## 3. Environment Configuration & Secret Management

Create `.env` in `backend/`:
```env
# Production App Settings
PROJECT_NAME="HireLens AI"
API_V1_STR="/api/v1"
SECRET_KEY="<GENERATE_64_CHAR_RANDOM_HEX_STRING>"
ALGORITHM="HS256"
ACCESS_TOKEN_EXPIRE_MINUTES=1440
REFRESH_TOKEN_EXPIRE_DAYS=7
DEFAULT_TIMEZONE="Asia/Kolkata"

# Database Connection (PostgreSQL Production)
DATABASE_URL="postgresql://hirelens:hirelens_password@postgres:5432/hirelens_db"

# Redis & Celery
CELERY_BROKER_URL="redis://redis:6379/0"
CELERY_RESULT_BACKEND="redis://redis:6379/0"

# AI Inference Provider
AI_PROVIDER="hosted" # or "ollama"
HOSTED_AI_BASE_URL="https://api.openai.com/v1"
HOSTED_AI_API_KEY="sk-..."
HOSTED_AI_MODEL="gpt-4o-mini"

# Storage
STORAGE_TYPE="local"
LOCAL_STORAGE_PATH="/app/storage/resumes"

# Payment Gateways (Phase 14)
RAZORPAY_KEY_ID="rzp_live_..."
RAZORPAY_KEY_SECRET="..."
RAZORPAY_WEBHOOK_SECRET="..."
STRIPE_PUBLISHABLE_KEY="pk_live_..."
STRIPE_SECRET_KEY="sk_live_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
```

---

## 4. Database Migrations & Single Head Verification

Before launching the web services, execute Alembic migrations:
```bash
# Verify current migration status
alembic current

# Run upgrade to latest single head
alembic upgrade head

# Verify migration revision
alembic heads
# Expected Output: 9c0d1e2f3a4b (head)
```

---

## 5. Health & Readiness Probes (Kubernetes / Docker)

The backend provides three operational endpoints:
1. **Liveness Probe (`GET /health/live`):**
   - Lightweight container liveness check.
   - Returns: `{"status": "alive", "service": "HireLens AI"}`.
2. **Readiness Probe (`GET /health/ready`):**
   - Validates live database query execution (`SELECT 1`).
   - If database is healthy: returns HTTP 200 with `{"status": "ready", "database": "connected"}`.
   - If database is down: returns HTTP 503 with `{"status": "not_ready", "database": "disconnected"}`.
3. **Deep System Health Probe (`GET /api/v1/platform/health`):**
   - Platform super admin probe testing database latency, Redis ping, Celery status, and disk write-ability with free space MB.

---

## 6. Celery Beat Periodic Schedulers

Periodic scheduled tasks are managed automatically by `celery_beat`:
1. `daily-subscription-renewal-check`: Runs at `00:00 UTC` daily, identifying subscriptions due for renewal, transitioning grace periods, and marking delinquent accounts past-due.
2. `hourly-trial-expiration-check`: Runs every hour, expiring trials and downgrading tenants to the FREE tier.
3. `daily-data-retention-sweep`: Runs at `02:00 UTC` daily, executing configured GDPR/DPDP data retention rules and generating audit logs.

---

## 7. Database Backup & Disaster Recovery Runbook

### 7.1 Automated Daily Backup Script
Execute via cron on the database host:
```bash
#!/bin/bash
BACKUP_DIR="/var/backups/hirelens"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
FILENAME="hirelens_backup_${TIMESTAMP}.sql.gz"

mkdir -p ${BACKUP_DIR}

# Execute pg_dump with compression
docker exec hirelens-postgres pg_dump -U hirelens -d hirelens_db | gzip > "${BACKUP_DIR}/${FILENAME}"

# Retain backups for 30 days
find ${BACKUP_DIR} -type f -name "*.sql.gz" -mtime +30 -exec rm {} \;

echo "Backup completed: ${FILENAME}"
```

### 7.2 Restoration Procedure
In the event of database disaster recovery:
```bash
# 1. Stop web traffic
docker compose stop backend celery_worker celery_beat

# 2. Decompress and restore SQL dump
gunzip < /var/backups/hirelens/hirelens_backup_YYYYMMDD_HHMMSS.sql.gz | docker exec -i hirelens-postgres psql -U hirelens -d hirelens_db

# 3. Verify database integrity and Alembic head
docker compose run --rm backend alembic heads

# 4. Restart services
docker compose start backend celery_worker celery_beat
```

---

## 8. Rollback Procedures

If a deployment failure occurs during rollout:
1. Revert container image tags to the previous stable release.
2. If database schema was modified, downgrade Alembic revision:
   ```bash
   alembic downgrade -1
   ```
3. Restart application containers and verify `/health/ready`.
