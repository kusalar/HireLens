import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, ConfigDict
from app.models.enums import UserRole, InvitationStatus
from app.schemas.user import UserRead

class AgencyBase(BaseModel):
    name: str
    domain: Optional[str] = None
    country: str = "IN"

class AgencyCreate(AgencyBase):
    pass

class AgencyUpdate(BaseModel):
    name: Optional[str] = None
    domain: Optional[str] = None
    country: Optional[str] = None

class AgencyRead(AgencyBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    slug: str
    is_active: bool
    created_at: datetime

class AgencyInviteCreate(BaseModel):
    email: EmailStr
    role: UserRole = UserRole.RECRUITER

class AgencyInviteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    email: EmailStr
    role: UserRole
    token: str
    status: InvitationStatus
    expires_at: datetime
    created_at: datetime
    invited_by_user_id: Optional[uuid.UUID] = None

class AcceptInviteRequest(BaseModel):
    token: str
    full_name: str
    password: str


class AgencyMemberUpdateStatus(BaseModel):
    is_active: bool


class AgencyOverviewResponse(BaseModel):
    agency: AgencyRead
    total_members: int
    members_by_role: dict[str, int]
    active_jobs_count: int
    total_candidates_count: int
    total_applications_count: int
    interviews_this_month_count: int
    subscription_tier: str
    subscription_status: str
    billing_interval: str
    current_period_end: Optional[datetime] = None
    soft_quota_warning: bool = False

