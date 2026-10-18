from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from app.core.config import settings
from app.core.logging import setup_logging
from app.api.v1.api import api_router
from app.db.session import engine, Base
import app.models  # ensure models are registered with Base

# Initialize logging
setup_logging(level="INFO")

# Automatically initialize tables in dev mode if using SQLite
if settings.DATABASE_URL.startswith("sqlite"):
    Base.metadata.create_all(bind=engine)


app = FastAPI(
    title=settings.PROJECT_NAME,
    description="HireLens AI — Recruitment Intelligence and Applicant Tracking SaaS",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
    allow_origin_regex=r"^https:\/\/.*\.vercel\.app$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API V1
app.include_router(api_router, prefix=settings.API_V1_STR)

# Root-level router aliases for client resilience against missing /api/v1 prefix in API_URL
from app.api.v1.endpoints import auth
app.include_router(auth.router, prefix="/auth", tags=["Authentication (Root Alias)"])
app.include_router(auth.router, prefix="/api/auth", tags=["Authentication (API Alias)"])

@app.get("/health", tags=["System"])
def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": "1.0.0",
    }

@app.get("/health/live", tags=["System"])
def liveness_probe():
    return {
        "status": "alive",
        "service": settings.PROJECT_NAME,
        "timestamp": Base.metadata.schema or "utc",
    }

@app.get("/health/ready", tags=["System"])
def readiness_probe():
    from sqlalchemy import text
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "service": settings.PROJECT_NAME,
        }
    except Exception as exc:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content={
                "status": "not_ready",
                "database": "disconnected",
                "error": str(exc),
            },
        )

@app.get("/", tags=["System"])
def root():
    return {
        "name": settings.PROJECT_NAME,
        "tagline": "Find the right candidate. Not just the right keywords.",
        "api_docs": "/docs",
        "health": "/health",
        "readiness": "/health/ready",
        "liveness": "/health/live",
    }

