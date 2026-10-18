import uuid
from typing import Optional
from pydantic import BaseModel, EmailStr, Field
from app.models.enums import UserRole

class UserRegister(BaseModel):
    agency_name: str = Field(..., min_length=2, max_length=255, description="Name of the recruitment agency")
    full_name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: Optional[str] = None
    type: Optional[str] = None
    exp: Optional[int] = None

class RefreshTokenRequest(BaseModel):
    refresh_token: str
