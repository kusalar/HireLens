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
