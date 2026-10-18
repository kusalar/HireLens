import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
    Numeric,
    Boolean,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    Index,
    DateTime,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
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


class SubscriptionPlan(Base, TimestampMixin):
    """
    Canonical SaaS subscription plan catalog (FREE, STARTER, PROFESSIONAL, BUSINESS, ENTERPRISE).
    Stores default resource bounds, pricing in INR and USD, and feature entitlements.
    """
    __tablename__ = "subscription_plans"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    slug = Column(String(50), unique=True, index=True, nullable=False)
    tier = Column(SQLEnum(SubscriptionTier), nullable=False, index=True)
    billing_interval = Column(SQLEnum(BillingInterval), default=BillingInterval.MONTHLY, nullable=False)
    price_inr = Column(Numeric(12, 2), default=0.00, nullable=False)
    price_usd = Column(Numeric(12, 2), default=0.00, nullable=False)
    max_active_jobs = Column(Integer, default=2, nullable=False)  # -1 represents unlimited
    max_recruiters = Column(Integer, default=1, nullable=False)   # -1 represents unlimited
    max_candidates_monthly = Column(Integer, default=50, nullable=False)
    max_resume_storage_mb = Column(Integer, default=250, nullable=False)
    max_ai_tokens_monthly = Column(Integer, default=50000, nullable=False)
    max_interviews_monthly = Column(Integer, default=10, nullable=False)
    max_workflow_runs_monthly = Column(Integer, default=0, nullable=False)
    features_json = Column(Text, nullable=False, default="{}")
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    subscriptions = relationship("AgencySubscription", back_populates="plan")


class AgencySubscription(Base, TimestampMixin):
    """
    Active subscription record for an agency.
    Owned at the agency level, governing all member recruiters.
    """
    __tablename__ = "agency_subscriptions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    plan_id = Column(GUID, ForeignKey("subscription_plans.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(SQLEnum(SubscriptionStatus), default=SubscriptionStatus.ACTIVE, nullable=False, index=True)
    billing_interval = Column(SQLEnum(BillingInterval), default=BillingInterval.MONTHLY, nullable=False)
    currency = Column(SQLEnum(BillingCurrency), default=BillingCurrency.INR, nullable=False)
    current_period_start = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    current_period_end = Column(DateTime(timezone=True), nullable=False)
    trial_end = Column(DateTime(timezone=True), nullable=True)
    cancel_at_period_end = Column(Boolean, default=False, nullable=False)
    canceled_at = Column(DateTime(timezone=True), nullable=True)
    payment_gateway = Column(SQLEnum(PaymentGateway), default=PaymentGateway.MOCK, nullable=False)
    gateway_customer_id = Column(String(255), nullable=True)
    gateway_subscription_id = Column(String(255), nullable=True, index=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    plan = relationship("SubscriptionPlan", back_populates="subscriptions")

    __table_args__ = (
        Index("ix_agency_subscriptions_status_period", "status", "current_period_end"),
    )


class SubscriptionHistory(Base):
    """
    Immutable audit history of all plan modifications, upgrades, downgrades, renewals, and cancellations.
    """
    __tablename__ = "subscription_histories"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    from_plan_id = Column(GUID, ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=True)
    to_plan_id = Column(GUID, ForeignKey("subscription_plans.id", ondelete="SET NULL"), nullable=False)
    status_before = Column(SQLEnum(SubscriptionStatus), nullable=True)
    status_after = Column(SQLEnum(SubscriptionStatus), nullable=False)
    change_reason = Column(String(255), nullable=True)
    changed_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    from_plan = relationship("SubscriptionPlan", foreign_keys=[from_plan_id])
    to_plan = relationship("SubscriptionPlan", foreign_keys=[to_plan_id])
    changed_by = relationship("User", foreign_keys=[changed_by_user_id])


class FeatureEntitlement(Base, TimestampMixin):
    """
    Specific feature enablement and granular capacity limits for an agency.
    """
    __tablename__ = "feature_entitlements"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_key = Column(String(100), nullable=False, index=True)
    is_enabled = Column(Boolean, default=True, nullable=False)
    max_limit = Column(Integer, default=-1, nullable=False)  # -1 = unlimited
    current_usage = Column(Integer, default=0, nullable=False)
    reset_frequency = Column(String(50), default="MONTHLY", nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        UniqueConstraint("agency_id", "feature_key", name="uq_agency_feature_entitlement"),
    )


class EntitlementOverride(Base, TimestampMixin):
    """
    Administrative entitlement override granting customized resource limits or special feature access.
    """
    __tablename__ = "entitlement_overrides"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(SQLEnum(QuotaResourceType), nullable=False, index=True)
    override_limit = Column(Integer, nullable=False)
    is_unlimited = Column(Boolean, default=False, nullable=False)
    reason = Column(String(255), nullable=False)
    granted_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    granted_by = relationship("User", foreign_keys=[granted_by_user_id])

    __table_args__ = (
        UniqueConstraint("agency_id", "resource_type", name="uq_agency_resource_override"),
    )


class UsageMeter(Base):
    """
    Monthly aggregated resource usage meter.
    Maintains current usage with versioning for concurrent request safety.
    """
    __tablename__ = "usage_meters"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(SQLEnum(QuotaResourceType), nullable=False, index=True)
    period_start = Column(DateTime(timezone=True), nullable=False)
    period_end = Column(DateTime(timezone=True), nullable=False)
    current_usage = Column(Integer, default=0, nullable=False)
    soft_limit = Column(Integer, default=0, nullable=False)
    hard_limit = Column(Integer, default=0, nullable=False)
    is_unlimited = Column(Boolean, default=False, nullable=False)
    version = Column(Integer, default=1, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        UniqueConstraint("agency_id", "resource_type", "period_start", name="uq_agency_resource_meter_period"),
        Index("ix_usage_meters_agency_resource", "agency_id", "resource_type"),
    )


class UsageRecord(Base):
    """
    Granular audit trail of individual quota consumption events with idempotency keys.
    """
    __tablename__ = "usage_records"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(SQLEnum(QuotaResourceType), nullable=False, index=True)
    quantity = Column(Integer, default=1, nullable=False)
    idempotency_key = Column(String(255), nullable=True, index=True)
    operation_reference = Column(String(255), nullable=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_usage_records_agency_created", "agency_id", "created_at"),
    )


class UsageReservation(Base):
    """
    Temporary quota hold for multi-step atomic operations (e.g., bulk resume processing).
    """
    __tablename__ = "usage_reservations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    resource_type = Column(SQLEnum(QuotaResourceType), nullable=False, index=True)
    reserved_quantity = Column(Integer, nullable=False)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    is_committed = Column(Boolean, default=False, nullable=False)
    is_released = Column(Boolean, default=False, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])


class PaymentTransaction(Base):
    """
    Record of checkout sessions, gateway charges, amounts, and reconciliation status.
    """
    __tablename__ = "payment_transactions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    gateway = Column(SQLEnum(PaymentGateway), nullable=False, index=True)
    gateway_transaction_id = Column(String(255), unique=True, nullable=True, index=True)
    gateway_order_id = Column(String(255), nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(SQLEnum(BillingCurrency), default=BillingCurrency.INR, nullable=False)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.PENDING, nullable=False, index=True)
    description = Column(String(255), nullable=True)
    error_message = Column(Text, nullable=True)
    receipt_url = Column(String(500), nullable=True)
    idempotency_key = Column(String(255), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    refunds = relationship("RefundRecord", back_populates="transaction", cascade="all, delete-orphan")


class PaymentWebhookEvent(Base):
    """
    Log of incoming payment provider webhooks with signature verification and replay prevention.
    """
    __tablename__ = "payment_webhook_events"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    gateway = Column(SQLEnum(PaymentGateway), nullable=False, index=True)
    event_id = Column(String(255), unique=True, nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)
    payload_json = Column(Text, nullable=False)
    signature_verified = Column(Boolean, default=False, nullable=False)
    processed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)


class BillingInvoice(Base):
    """
    Formal tax invoice for subscription charges and add-ons.
    Maintains GST compliance for Indian entities and tax-exempt export categorization for international entities.
    """
    __tablename__ = "billing_invoices"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    invoice_number = Column(String(50), unique=True, nullable=False, index=True)
    status = Column(SQLEnum(InvoiceStatus), default=InvoiceStatus.ISSUED, nullable=False, index=True)
    currency = Column(SQLEnum(BillingCurrency), default=BillingCurrency.INR, nullable=False)
    subtotal = Column(Numeric(12, 2), default=0.00, nullable=False)
    tax_rate_pct = Column(Float, default=0.0, nullable=False)
    tax_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    total_amount = Column(Numeric(12, 2), default=0.00, nullable=False)
    customer_name = Column(String(255), nullable=False)
    customer_email = Column(String(255), nullable=False)
    customer_address = Column(Text, nullable=True)
    customer_gstin = Column(String(20), nullable=True, index=True)
    is_domestic_india = Column(Boolean, default=True, nullable=False)
    paid_at = Column(DateTime(timezone=True), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True)
    download_token = Column(String(64), unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    line_items = relationship("InvoiceLineItem", back_populates="invoice", cascade="all, delete-orphan")
    credit_notes = relationship("CreditNote", back_populates="invoice", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_billing_invoices_agency_created", "agency_id", "created_at"),
    )


class InvoiceLineItem(Base):
    """
    Itemized service line item attached to a billing invoice.
    """
    __tablename__ = "invoice_line_items"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    invoice_id = Column(GUID, ForeignKey("billing_invoices.id", ondelete="CASCADE"), nullable=False, index=True)
    description = Column(String(255), nullable=False)
    quantity = Column(Integer, default=1, nullable=False)
    unit_price = Column(Numeric(12, 2), nullable=False)
    total_price = Column(Numeric(12, 2), nullable=False)

    # Relationships
    invoice = relationship("BillingInvoice", back_populates="line_items")


class CreditNote(Base):
    """
    Financial adjustment or credit issued against a paid invoice.
    """
    __tablename__ = "credit_notes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    invoice_id = Column(GUID, ForeignKey("billing_invoices.id", ondelete="RESTRICT"), nullable=False, index=True)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    credit_number = Column(String(50), unique=True, nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    reason = Column(String(255), nullable=False)
    issued_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    invoice = relationship("BillingInvoice", back_populates="credit_notes")
    agency = relationship("Agency", foreign_keys=[agency_id])
    issued_by = relationship("User", foreign_keys=[issued_by_user_id])


class RefundRecord(Base):
    """
    Payment gateway refund tracking record.
    """
    __tablename__ = "refund_records"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    payment_transaction_id = Column(GUID, ForeignKey("payment_transactions.id", ondelete="RESTRICT"), nullable=False, index=True)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    gateway_refund_id = Column(String(255), unique=True, nullable=True, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(SQLEnum(BillingCurrency), default=BillingCurrency.INR, nullable=False)
    reason = Column(String(255), nullable=True)
    status = Column(SQLEnum(PaymentStatus), default=PaymentStatus.SUCCEEDED, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    transaction = relationship("PaymentTransaction", back_populates="refunds")
    agency = relationship("Agency", foreign_keys=[agency_id])


class AgencyBillingProfile(Base, TimestampMixin):
    """
    Legal corporate billing details, address, and GSTIN registration for an agency.
    """
    __tablename__ = "agency_billing_profiles"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    legal_name = Column(String(255), nullable=False)
    billing_email = Column(String(255), nullable=False)
    address_line1 = Column(String(255), nullable=True)
    address_line2 = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state_province = Column(String(100), nullable=True)
    postal_code = Column(String(20), nullable=True)
    country = Column(String(10), default="IN", nullable=False)
    gstin = Column(String(20), nullable=True, index=True)
    currency = Column(SQLEnum(BillingCurrency), default=BillingCurrency.INR, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])


class BillingAuditLog(Base):
    """
    Specialized audit log for financial operations, subscription changes, and payment webhooks.
    """
    __tablename__ = "billing_audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False)
    resource_id = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    actor = relationship("User", foreign_keys=[actor_user_id])

    __table_args__ = (
        Index("ix_billing_audit_agency_created", "agency_id", "created_at"),
    )
