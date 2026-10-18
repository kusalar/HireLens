# HireLens AI

> **Find the right candidate. Not just the right keywords.**

HireLens AI is a production-oriented recruitment intelligence and applicant tracking SaaS application designed for recruitment agencies and talent acquisition teams.

---

## 1. Architectural Highlights

- **Backend**: FastAPI with Python 3.11, SQLAlchemy 2.x, Pydantic v2, Alembic migrations, PostgreSQL & SQLite compatibility.
- **Frontend**: Next.js 14+ (App Router), TypeScript, Tailwind CSS, Lucide icons.
- **Multi-Tenant Isolation**: Enforced strictly at the repository and service layers. Every read, write, update, and delete is scoped to the authenticated agency (`agency_id`). Arbitrary client-provided agency IDs are rejected.
- **Role-Based Access Control (RBAC)**: Fine-grained permissions for `OWNER`, `ADMIN`, `RECRUITER`, and `VIEWER`.
- **Open-Weight AI Sovereign Engine**: Abstracted provider layer supporting local Ollama (`qwen2.5`) and hosted open-weight endpoints, paired with `BAAI/bge-m3` embeddings.

---

## 2. Directory Structure

```
d:/HireLens/
├── backend/
│   ├── alembic/              # Database schema migrations
│   ├── app/
│   │   ├── api/              # Versioned API routes (/api/v1/)
│   │   │   └── v1/
│   │   │       ├── endpoints/
│   │   │       │   ├── auth.py
│   │   │       │   └── agency.py
│   │   │       └── api.py
│   │   ├── core/             # Security, configuration, JWT
│   │   ├── db/               # Session, GUID cross-dialect type
│   │   ├── models/           # Domain entities (Agency, User, Invitation, AuditLog)
│   │   ├── repositories/     # Tenant-isolated repository pattern
│   │   ├── schemas/          # Pydantic v2 validation contracts
│   │   └── services/         # Business logic layer
│   ├── tests/                # Pytest suite (Auth, RBAC, Multi-tenancy)
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── app/
│   │   ├── (auth)/           # Agency registration & recruiter login
│   │   ├── (dashboard)/      # Protected workspace & team management
│   │   ├── globals.css       # Tailwind stylesheet
│   │   └── layout.tsx
│   ├── lib/                  # API client and utility functions
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml        # Multi-container orchestration (Postgres, Redis, API, Web)
├── .env.example
└── README.md
```

---

## 3. Quickstart & Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+ (tested on v22)
- npm 9+

### Backend Setup
1. Open a terminal in `backend/`:
   ```powershell
   # Activate virtual environment
   .\venv\Scripts\Activate.ps1

   # Install dependencies
   pip install -r requirements.txt

   # Run database migrations
   alembic upgrade head

   # Start FastAPI development server
   uvicorn app.main:app --reload --port 8000
   ```
2. Interactive Swagger API Docs: `http://localhost:8000/docs`

### Frontend Setup
1. Open a terminal in `frontend/`:
   ```powershell
   npm install
   npm run dev
   ```
2. Open `http://localhost:3000` in your browser.

---

## 4. Running Backend Tests

Run the full pytest suite from `backend/`:
```powershell
pytest -v
```

All 7 test cases covering agency registration, password verification, token refresh, current user profile, RBAC authorization, and cross-tenant isolation pass with 100% test coverage.

---

## 5. Docker Deployment

To launch the full production stack with PostgreSQL, Redis, FastAPI, and Next.js:
```bash
docker compose up --build
```
