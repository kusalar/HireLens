import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.schemas.user import UserRead
from app.schemas.billing import (
    AgencySubscriptionRead,
    AgencyBillingProfileRead,
    BillingInvoiceRead,
    EntitlementOverrideRead,
)


class PlatformOverviewResponse(BaseModel):
    total_agencies: int
    active_agencies: int
    suspended_agencies: int
    total_users: int
    active_users: int
    total_jobs: int
    active_jobs: int
    total_candidates: int
    total_applications: int
    total_interviews: int
    total_resumes_processed: int
    subscriptions_by_tier: Dict[str, int]
    subscriptions_by_status: Dict[str, int]
    mrr_inr: float
    mrr_usd: float
    arr_inr: float
    arr_usd: float
    total_revenue_inr: float
    total_revenue_usd: float
    total_invoices_paid: int
    system_status: str = "HEALTHY"


class PlatformAgencyItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    domain: Optional[str] = None
    country: str = "IN"
    is_active: bool
    created_at: datetime
    user_count: int = 0
    job_count: int = 0
    candidate_count: int = 0
    current_plan: str = "FREE"
    subscription_status: str = "ACTIVE"


class PlatformAgencyListResponse(BaseModel):
    items: List[PlatformAgencyItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class PlatformAgencyDetailResponse(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    domain: Optional[str] = None
    country: str
    is_active: bool
    created_at: datetime
    users: List[UserRead]
    subscription: Optional[AgencySubscriptionRead] = None
    billing_profile: Optional[AgencyBillingProfileRead] = None
    active_jobs_count: int = 0
    total_candidates_count: int = 0
    total_applications_count: int = 0
    recent_invoices: List[BillingInvoiceRead] = Field(default_factory=list)
    entitlement_overrides: List[EntitlementOverrideRead] = Field(default_factory=list)


class PlatformAgencyStatusUpdate(BaseModel):
    is_active: bool
    reason: str = Field(..., min_length=3, max_length=500)


class PlatformAuditLogItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    agency_name: Optional[str] = None
    actor_user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    event_category: str
    severity: str
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    created_at: datetime


class PlatformAuditLogListResponse(BaseModel):
    items: List[PlatformAuditLogItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class PlatformSystemHealthResponse(BaseModel):
    status: str  # HEALTHY, DEGRADED, UNHEALTHY
    database: Dict[str, Any]
    redis: Dict[str, Any]
    celery: Dict[str, Any]
    storage: Dict[str, Any]
    timestamp: datetime
