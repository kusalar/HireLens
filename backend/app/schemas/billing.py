import uuid
from typing import List, Dict, Any, Optional
from datetime import datetime
from pydantic import BaseModel, Field, EmailStr, ConfigDict
from app.models.enums import (
    SubscriptionTier,
    SubscriptionStatus,
    BillingInterval,
    PaymentGateway,
    PaymentStatus,
    InvoiceStatus,
    QuotaResourceType,
    BillingCurrency,
)


class SubscriptionPlanRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    slug: str
    tier: SubscriptionTier
    billing_interval: BillingInterval
    price_inr: float
    price_usd: float
    max_active_jobs: int
    max_recruiters: int
    max_candidates_monthly: int
    max_resume_storage_mb: int
    max_ai_tokens_monthly: int
    max_interviews_monthly: int
    max_workflow_runs_monthly: int
    features: Dict[str, Any] = Field(default_factory=dict)
    is_active: bool


class AgencySubscriptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    plan_id: uuid.UUID
    plan_name: str
    plan_slug: str
    tier: SubscriptionTier
    status: SubscriptionStatus
    billing_interval: BillingInterval
    currency: BillingCurrency
    current_period_start: datetime
    current_period_end: datetime
    trial_end: Optional[datetime] = None
    cancel_at_period_end: bool
    canceled_at: Optional[datetime] = None
    payment_gateway: PaymentGateway
    is_in_grace_period: bool = False


class SubscriptionChangeRequest(BaseModel):
    plan_slug: str
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    currency: BillingCurrency = BillingCurrency.INR


class UsageMeterRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    resource_type: QuotaResourceType
    current_usage: int
    soft_limit: int
    hard_limit: int
    is_unlimited: bool
    utilization_pct: float
    is_soft_limit_exceeded: bool
    is_hard_limit_exceeded: bool


class UsageOverviewResponse(BaseModel):
    agency_id: uuid.UUID
    plan_name: str
    tier: SubscriptionTier
    period_start: datetime
    period_end: datetime
    meters: Dict[str, UsageMeterRead]
    has_warnings: bool
    has_exhausted_quotas: bool


class FeatureEntitlementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    feature_key: str
    is_enabled: bool
    max_limit: int
    current_usage: int
    reset_frequency: str


class CheckoutSessionCreate(BaseModel):
    plan_slug: str
    billing_interval: BillingInterval = BillingInterval.MONTHLY
    currency: BillingCurrency = BillingCurrency.INR
    gateway: PaymentGateway = PaymentGateway.MOCK
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    order_id: Optional[str] = None
    gateway: PaymentGateway
    amount: float
    currency: BillingCurrency
    checkout_url: Optional[str] = None
    publishable_key: Optional[str] = None
    plan_name: str
    plan_slug: str
    billing_interval: BillingInterval


class PaymentVerificationRequest(BaseModel):
    gateway: PaymentGateway
    session_id: Optional[str] = None
    order_id: Optional[str] = None
    payment_id: Optional[str] = None
    signature: Optional[str] = None
    idempotency_key: Optional[str] = None


class PaymentVerificationResponse(BaseModel):
    success: bool
    subscription_status: SubscriptionStatus
    transaction_id: str
    message: str
    invoice_number: Optional[str] = None


class InvoiceLineItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    description: str
    quantity: int
    unit_price: float
    total_price: float


class BillingInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    invoice_number: str
    status: InvoiceStatus
    currency: BillingCurrency
    subtotal: float
    tax_rate_pct: float
    tax_amount: float
    total_amount: float
    customer_name: str
    customer_email: str
    customer_gstin: Optional[str] = None
    is_domestic_india: bool
    paid_at: Optional[datetime] = None
    due_date: Optional[datetime] = None
    download_url: str
    created_at: datetime


class BillingInvoiceDetailRead(BillingInvoiceRead):
    customer_address: Optional[str] = None
    line_items: List[InvoiceLineItemRead] = Field(default_factory=list)


class AgencyBillingProfileUpdate(BaseModel):
    legal_name: str
    billing_email: EmailStr
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: str = "IN"
    gstin: Optional[str] = None
    currency: BillingCurrency = BillingCurrency.INR


class AgencyBillingProfileRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    legal_name: str
    billing_email: str
    address_line1: Optional[str] = None
    address_line2: Optional[str] = None
    city: Optional[str] = None
    state_province: Optional[str] = None
    postal_code: Optional[str] = None
    country: str
    gstin: Optional[str] = None
    currency: BillingCurrency
    is_gstin_valid: bool = False
    updated_at: Optional[datetime] = None


class EntitlementOverrideCreate(BaseModel):
    resource_type: QuotaResourceType
    override_limit: int
    is_unlimited: bool = False
    reason: str
    expires_at: Optional[datetime] = None


class EntitlementOverrideRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    resource_type: QuotaResourceType
    override_limit: int
    is_unlimited: bool
    reason: str
    granted_by_user_id: Optional[uuid.UUID] = None
    expires_at: Optional[datetime] = None
    created_at: datetime


class PlatformBillingOverviewResponse(BaseModel):
    total_agencies: int
    subscriptions_by_tier: Dict[str, int]
    subscriptions_by_status: Dict[str, int]
    mrr_inr: float
    mrr_usd: float
    arr_inr: float
    arr_usd: float
    trial_conversion_rate_pct: float
    payment_failure_count: int
    recent_transactions_count: int


class PlatformSubscriptionActionRequest(BaseModel):
    action: str = Field(..., description="SUSPEND, REACTIVATE, or CANCEL")
    reason: str


class RefundRequest(BaseModel):
    transaction_id: str
    amount: Optional[float] = None
    reason: str
