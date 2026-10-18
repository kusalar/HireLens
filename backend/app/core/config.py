import json
from typing import List, Optional, Any
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import AnyHttpUrl, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "HireLens AI"
    API_V1_STR: str = "/api/v1"
    SECRET_KEY: str = "hirelens-super-secret-key-change-in-production-2026-secure-token"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 1 day
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    DEFAULT_TIMEZONE: str = "Asia/Kolkata"

    # Database: Defaults to SQLite for immediate local Windows development without requiring PostgreSQL
    # In production/Docker, set DATABASE_URL=postgresql://user:password@localhost:5432/hirelens
    DATABASE_URL: str = "sqlite:///./hirelens.db"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_db_url(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip()
            # Ensure SSL mode is enforced for Neon serverless endpoints
            if "neon.tech" in v_clean and "sslmode" not in v_clean:
                v_clean += ("&" if "?" in v_clean else "?") + "sslmode=require"
            if v_clean.startswith("postgres://"):
                return v_clean.replace("postgres://", "postgresql+psycopg2://", 1)
            elif v_clean.startswith("postgresql://") and not v_clean.startswith("postgresql+"):
                return v_clean.replace("postgresql://", "postgresql+psycopg2://", 1)
            return v_clean
        return v

    # AI Configuration (Open-weight, Ollama, etc.)
    AI_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:1.5b"
    EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:8000",
    ]

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Any) -> Any:
        if isinstance(v, str):
            v_clean = v.strip()
            if v_clean.startswith("[") and v_clean.endswith("]"):
                try:
                    return json.loads(v_clean)
                except Exception:
                    pass
            return [i.strip() for i in v_clean.split(",") if i.strip()]
        elif isinstance(v, (list, tuple)):
            return list(v)
        return v

    # Storage
    STORAGE_TYPE: str = "local"
    LOCAL_STORAGE_PATH: str = "./storage/resumes"
    MAX_RESUME_FILE_SIZE_BYTES: int = 15 * 1024 * 1024  # 15 MB
    S3_BUCKET: Optional[str] = None
    S3_ENDPOINT_URL: Optional[str] = None
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_REGION: Optional[str] = "us-east-1"

    # Background Tasks & Celery
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    # Document Extraction & OCR
    ENABLE_OCR: bool = False

    # AI Configuration (Open-weight, Ollama, Hosted)
    HOSTED_AI_BASE_URL: Optional[str] = None
    HOSTED_AI_API_KEY: Optional[str] = None
    HOSTED_AI_MODEL: Optional[str] = None

    # Email Configuration
    EMAIL_PROVIDER: str = "console"  # "console", "smtp", "mock"
    SMTP_HOST: Optional[str] = None
    SMTP_PORT: int = 587
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    SMTP_TLS: bool = True
    EMAILS_FROM_EMAIL: str = "noreply@hirelens.ai"
    EMAILS_FROM_NAME: str = "HireLens AI"

    # Calendar Integration & OAuth Configuration (Phase 9)
    TOKEN_ENCRYPTION_KEY: Optional[str] = "4bZJ6e7lOq3eQ1lU9mYx8zXw7vP5n2sA1dF4gH7jK0="  # 32-byte urlsafe base64 default for dev
    CALENDAR_WEBHOOK_BASE_URL: str = "http://localhost:8000"
    USE_MOCK_CALENDAR_PROVIDER: bool = True

    # Google OAuth & Calendar
    GOOGLE_CLIENT_ID: Optional[str] = None
    GOOGLE_CLIENT_SECRET: Optional[str] = None
    GOOGLE_REDIRECT_URI: str = "http://localhost:3000/settings/integrations?provider=google"
    GOOGLE_CALENDAR_SCOPES: List[str] = [
        "https://www.googleapis.com/auth/calendar.events",
        "https://www.googleapis.com/auth/calendar.readonly",
        "https://www.googleapis.com/auth/userinfo.email",
    ]

    # Microsoft OAuth & Outlook (Microsoft Graph)
    MICROSOFT_CLIENT_ID: Optional[str] = None
    MICROSOFT_CLIENT_SECRET: Optional[str] = None
    MICROSOFT_TENANT_ID: str = "common"
    MICROSOFT_REDIRECT_URI: str = "http://localhost:3000/settings/integrations?provider=microsoft"
    MICROSOFT_CALENDAR_SCOPES: List[str] = [
        "Calendars.ReadWrite",
        "offline_access",
        "User.Read",
    ]
    # Payment Gateways (Razorpay & Stripe) (Phase 14)
    RAZORPAY_KEY_ID: Optional[str] = None
    RAZORPAY_KEY_SECRET: Optional[str] = None
    RAZORPAY_WEBHOOK_SECRET: Optional[str] = None

    STRIPE_PUBLISHABLE_KEY: Optional[str] = None
    STRIPE_SECRET_KEY: Optional[str] = None
    STRIPE_WEBHOOK_SECRET: Optional[str] = None

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()

