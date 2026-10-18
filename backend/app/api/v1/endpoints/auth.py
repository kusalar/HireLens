from fastapi import APIRouter, Depends, status, Request
from sqlalchemy.orm import Session
from app.db.session import get_db
from app.schemas.auth import UserRegister, UserLogin, Token, RefreshTokenRequest
from app.schemas.user import UserRead
from app.services.auth_service import AuthService
from app.api.deps import get_current_user
from app.models.entities import User

router = APIRouter()

@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(data: UserRegister, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    user, tokens = auth_service.register_agency_and_owner(data)
    return {
        "user": UserRead.model_validate(user),
        "tokens": tokens,
    }

@router.post("/login")
def login(data: UserLogin, request: Request, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    ip_address = request.client.host if request.client else None
    user_agent = request.headers.get("user-agent")
    user, tokens = auth_service.authenticate_user(
        data.email, data.password, ip_address=ip_address, user_agent=user_agent
    )
    return {
        "user": UserRead.model_validate(user),
        "tokens": tokens,
    }

@router.post("/demo-session", status_code=status.HTTP_200_OK)
def launch_demo_session(request: Request, db: Session = Depends(get_db)):
    """
    1-Click Live Demo Session Entry Point for Dev Week 2 Challenge Evaluators.
    Issues a valid JWT token bound to the dedicated synthetic demo tenant (Apex Talent Partners).
    Guarded with an IP-based sliding window rate limiter (max 15 req/min).
    """
    from fastapi import HTTPException
    from app.services.demo_service import check_demo_rate_limit

    ip_address = request.client.host if request.client else "127.0.0.1"
    if not check_demo_rate_limit(ip_address, max_requests=15, window_seconds=60):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many demo session requests. Please wait a moment before trying again.",
        )

    user_agent = request.headers.get("user-agent")
    auth_service = AuthService(db)
    user, tokens, agency = auth_service.create_demo_session(
        ip_address=ip_address, user_agent=user_agent
    )
    return {
        "user": UserRead.model_validate(user),
        "tokens": tokens,
        "agency": {
            "id": str(agency.id),
            "name": agency.name,
            "slug": agency.slug,
            "is_demo": True,
        },
    }

@router.post("/refresh", response_model=Token)
def refresh_token(data: RefreshTokenRequest, db: Session = Depends(get_db)):
    auth_service = AuthService(db)
    return auth_service.refresh_access_token(data.refresh_token)

@router.get("/me", response_model=UserRead)
def get_current_user_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    return {"message": "Successfully logged out."}
