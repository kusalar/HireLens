import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
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
    AuditEventCategory,
    AuditSeverity,
    ConsentType,
    PrivacyRequestType,
    PrivacyRequestStatus,
    RetentionCategory,
    RetentionAction,
    RetentionExecutionType,
    RetentionStatus,
)


class UserSession(Base):
    """
    Active and revoked user authentication session records with server-side revocation tracking.
    """
    __tablename__ = "user_sessions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    session_token_hash = Column(String(64), nullable=True, index=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    device_info = Column(String(100), nullable=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    last_activity_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    revocation_reason = Column(String(255), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_user_sessions_user_active", "user_id", "is_active"),
        Index("ix_user_sessions_agency_active", "agency_id", "is_active"),
    )


class SecurityAuditEvent(Base):
    """
    Unified, immutable security audit event tracking for compliance, access logs,
    and administrative operations. Records cannot be updated or deleted via API.
    """
    __tablename__ = "security_audit_events"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = Column(String(255), nullable=True)
    event_category = Column(SQLEnum(AuditEventCategory), nullable=False, index=True)
    severity = Column(SQLEnum(AuditSeverity), default=AuditSeverity.LOW, nullable=False, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=False, index=True)
    resource_id = Column(String(100), nullable=True)
    details_json = Column(Text, nullable=True)
    ip_address = Column(String(50), nullable=True)
    user_agent = Column(String(500), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    actor = relationship("User", foreign_keys=[actor_user_id])

    __table_args__ = (
        Index("ix_sec_audit_agency_created", "agency_id", "created_at"),
        Index("ix_sec_audit_agency_severity", "agency_id", "severity"),
    )


class CandidateConsentRecord(Base):
    """
    Candidate privacy consent tracking per legal policy version, purpose, and channel.
    Maintains immutable grant and withdrawal timestamps.
    """
    __tablename__ = "candidate_consent_records"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    consent_type = Column(SQLEnum(ConsentType), nullable=False, index=True)
    is_granted = Column(Boolean, default=True, nullable=False)
    policy_version = Column(String(50), nullable=False, default="v1.0")
    purpose = Column(String(255), nullable=False)
    channel = Column(String(50), nullable=False, default="APPLICATION_PORTAL")
    granted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    withdrawn_at = Column(DateTime(timezone=True), nullable=True)
    metadata_json = Column(Text, nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    candidate = relationship("Candidate", foreign_keys=[candidate_id])

    __table_args__ = (
        Index("ix_consent_agency_candidate", "agency_id", "candidate_id"),
    )


class CandidatePrivacyRequest(Base):
    """
    Candidate data subject privacy requests (Access, Correction, Deletion/Anonymization,
    Consent Withdrawal, Processing Restriction) with legal-hold exemptions.
    """
    __tablename__ = "candidate_privacy_requests"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    request_type = Column(SQLEnum(PrivacyRequestType), nullable=False, index=True)
    status = Column(SQLEnum(PrivacyRequestStatus), default=PrivacyRequestStatus.PENDING, nullable=False, index=True)
    requested_by_email = Column(String(255), nullable=False)
    request_details = Column(Text, nullable=True)
    resolution_notes = Column(Text, nullable=True)
    has_legal_hold = Column(Boolean, default=False, nullable=False)
    legal_hold_reason = Column(Text, nullable=True)
    handled_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    handled_by = relationship("User", foreign_keys=[handled_by_user_id])

    __table_args__ = (
        Index("ix_privacy_requests_agency_status", "agency_id", "status"),
    )


class AIGovernancePolicy(Base, TimestampMixin):
    """
    Agency-level governance policy defining allowed AI providers, token limits,
    cost caps, and safety-filter enforcement.
    """
    __tablename__ = "ai_governance_policies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    allowed_providers_json = Column(Text, nullable=False, default='["OLLAMA", "HOSTED_OPEN_WEIGHT"]')
    max_tokens_per_request = Column(Integer, default=4000, nullable=False)
    monthly_token_budget = Column(Integer, default=500000, nullable=False)
    require_pii_masking = Column(Boolean, default=True, nullable=False)
    safety_filter_enabled = Column(Boolean, default=True, nullable=False)
    updated_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    updated_by = relationship("User", foreign_keys=[updated_by_user_id])


class AIUsageLog(Base):
    """
    Audit log of AI request invocations tracking token counts, latency, cost, and provider fallbacks.
    """
    __tablename__ = "ai_usage_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    feature_name = Column(String(100), nullable=False, index=True)
    provider = Column(String(50), nullable=False, index=True)
    model = Column(String(100), nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    latency_ms = Column(Float, default=0.0, nullable=False)
    estimated_cost_usd = Column(Float, default=0.0, nullable=False)
    is_fallback = Column(Boolean, default=False, nullable=False)
    fallback_reason = Column(String(255), nullable=True)
    safety_filter_triggered = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_ai_usage_agency_created", "agency_id", "created_at"),
        Index("ix_ai_usage_agency_feature", "agency_id", "feature_name"),
    )


class DataRetentionPolicy(Base, TimestampMixin):
    """
    Configurable retention policy per agency and data category with legal-hold exemption controls.
    """
    __tablename__ = "data_retention_policies"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    data_category = Column(SQLEnum(RetentionCategory), nullable=False, index=True)
    retention_days = Column(Integer, default=365, nullable=False)
    action_type = Column(SQLEnum(RetentionAction), default=RetentionAction.ARCHIVE, nullable=False)
    is_enabled = Column(Boolean, default=False, nullable=False)
    exempt_legal_holds = Column(Boolean, default=True, nullable=False)
    last_executed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    execution_logs = relationship(
        "RetentionExecutionLog",
        back_populates="policy",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("agency_id", "data_category", name="uq_agency_data_retention_category"),
    )


class RetentionExecutionLog(Base):
    """
    Immutable execution audit for retention policy evaluations (dry-run previews and live runs).
    """
    __tablename__ = "retention_execution_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    policy_id = Column(
        GUID,
        ForeignKey("data_retention_policies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    execution_type = Column(SQLEnum(RetentionExecutionType), nullable=False)
    records_scanned = Column(Integer, default=0, nullable=False)
    records_affected = Column(Integer, default=0, nullable=False)
    records_exempted = Column(Integer, default=0, nullable=False)
    status = Column(SQLEnum(RetentionStatus), default=RetentionStatus.COMPLETED, nullable=False)
    executed_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    execution_summary_json = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    policy = relationship("DataRetentionPolicy", back_populates="execution_logs")
    executed_by = relationship("User", foreign_keys=[executed_by_user_id])
