import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
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
    CalendarProviderType,
    CalendarSyncStatus,
    CalendarSyncDirection,
    CalendarSyncOperation,
    MeetingProviderType,
)


class CalendarConnection(Base, TimestampMixin):
    __tablename__ = "calendar_connections"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(SQLEnum(CalendarProviderType), nullable=False, index=True)
    provider_account_id = Column(String(255), nullable=True)
    provider_account_email = Column(String(255), nullable=True)
    encrypted_access_token = Column(Text, nullable=True)
    encrypted_refresh_token = Column(Text, nullable=True)
    access_token_expires_at = Column(DateTime(timezone=True), nullable=True)
    selected_calendar_id = Column(String(255), default="primary", nullable=False)
    selected_calendar_name = Column(String(255), default="Primary Calendar", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    user = relationship("User", foreign_keys=[user_id])
    event_mappings = relationship(
        "CalendarEventMapping",
        back_populates="connection",
        cascade="all, delete-orphan",
    )
    sync_jobs = relationship(
        "CalendarSyncJob",
        back_populates="connection",
        cascade="all, delete-orphan",
    )
    webhook_subscriptions = relationship(
        "CalendarWebhookSubscription",
        back_populates="connection",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("agency_id", "user_id", "provider", name="uq_calendar_connections_agency_user_provider"),
        Index("ix_calendar_connections_agency_active", "agency_id", "is_active"),
    )


class CalendarEventMapping(Base, TimestampMixin):
    __tablename__ = "calendar_event_mappings"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(GUID, ForeignKey("calendar_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(GUID, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    external_event_id = Column(String(255), nullable=False, index=True)
    external_calendar_id = Column(String(255), default="primary", nullable=False)
    provider = Column(SQLEnum(CalendarProviderType), nullable=False)
    meeting_link = Column(String(1024), nullable=True)
    meeting_provider = Column(
        SQLEnum(MeetingProviderType),
        default=MeetingProviderType.NONE,
        nullable=False,
    )
    sync_status = Column(
        SQLEnum(CalendarSyncStatus),
        default=CalendarSyncStatus.SYNCED,
        nullable=False,
        index=True,
    )
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    connection = relationship("CalendarConnection", back_populates="event_mappings")
    interview = relationship("Interview", foreign_keys=[interview_id])

    __table_args__ = (
        UniqueConstraint("agency_id", "interview_id", "connection_id", name="uq_calendar_event_mappings_agency_interview_conn"),
        UniqueConstraint("connection_id", "external_event_id", name="uq_calendar_event_mappings_conn_external_event"),
        Index("ix_calendar_event_mappings_agency_status", "agency_id", "sync_status"),
    )


class CalendarSyncJob(Base, TimestampMixin):
    __tablename__ = "calendar_sync_jobs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(GUID, ForeignKey("calendar_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(GUID, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    operation = Column(SQLEnum(CalendarSyncOperation), nullable=False)
    status = Column(String(32), default="PENDING", nullable=False, index=True)  # PENDING, PROCESSING, COMPLETED, FAILED, DEAD_LETTER
    attempt_count = Column(Integer, default=0, nullable=False)
    max_attempts = Column(Integer, default=5, nullable=False)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    scheduled_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    last_error = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    connection = relationship("CalendarConnection", back_populates="sync_jobs")
    interview = relationship("Interview", foreign_keys=[interview_id])

    __table_args__ = (
        Index("ix_calendar_sync_jobs_agency_status_scheduled", "agency_id", "status", "scheduled_at"),
    )


class CalendarSyncLog(Base):
    __tablename__ = "calendar_sync_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(GUID, nullable=True, index=True)
    interview_id = Column(GUID, nullable=True, index=True)
    direction = Column(SQLEnum(CalendarSyncDirection), nullable=False)
    operation = Column(SQLEnum(CalendarSyncOperation), nullable=False)
    status = Column(String(32), nullable=False, index=True)  # SUCCESS, FAILED, CONFLICT
    details = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_calendar_sync_logs_agency_created", "agency_id", "created_at"),
    )


class CalendarWebhookSubscription(Base, TimestampMixin):
    __tablename__ = "calendar_webhook_subscriptions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    connection_id = Column(GUID, ForeignKey("calendar_connections.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(SQLEnum(CalendarProviderType), nullable=False)
    external_subscription_id = Column(String(255), unique=True, index=True, nullable=False)
    resource_id = Column(String(255), nullable=True)
    client_state_or_token = Column(String(255), nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    connection = relationship("CalendarConnection", back_populates="webhook_subscriptions")
