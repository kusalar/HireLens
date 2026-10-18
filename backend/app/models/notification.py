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
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import NotificationType, NotificationDeliveryStatus


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    notification_type = Column(SQLEnum(NotificationType), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    related_entity_type = Column(String(50), nullable=True, index=True)
    related_entity_id = Column(GUID, nullable=True, index=True)
    is_read = Column(Boolean, default=False, nullable=False, index=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    recipient = relationship("User", foreign_keys=[recipient_user_id])

    __table_args__ = (
        Index("ix_notifications_agency_recipient_read", "agency_id", "recipient_user_id", "is_read"),
        Index("ix_notifications_agency_created", "agency_id", "created_at"),
    )


class NotificationPreference(Base, TimestampMixin):
    __tablename__ = "notification_preferences"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    email_enabled = Column(Boolean, default=True, nullable=False)
    interview_notifications_enabled = Column(Boolean, default=True, nullable=False)
    application_status_notifications_enabled = Column(Boolean, default=True, nullable=False)
    candidate_email_updates_enabled = Column(Boolean, default=True, nullable=False)
    default_timezone = Column(String(50), default="Asia/Kolkata", nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])


class EmailDeliveryLog(Base, TimestampMixin):
    __tablename__ = "email_delivery_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    recipient_email = Column(String(255), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    subject = Column(String(255), nullable=False)
    provider = Column(String(50), default="console", nullable=False)
    status = Column(SQLEnum(NotificationDeliveryStatus), default=NotificationDeliveryStatus.PENDING, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    last_attempt_at = Column(DateTime(timezone=True), nullable=True)
    delivered_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_delivery_logs_agency_status", "agency_id", "status"),
        Index("ix_delivery_logs_agency_created", "agency_id", "created_at"),
    )


class NotificationOutbox(Base, TimestampMixin):
    __tablename__ = "notification_outbox"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(String(50), nullable=False, index=True)
    idempotency_key = Column(String(255), unique=True, index=True, nullable=False)
    recipient_email = Column(String(255), nullable=False, index=True)
    recipient_name = Column(String(255), nullable=True)
    subject = Column(String(255), nullable=False)
    body_html = Column(Text, nullable=False)
    body_text = Column(Text, nullable=False)
    status = Column(SQLEnum(NotificationDeliveryStatus), default=NotificationDeliveryStatus.PENDING, nullable=False, index=True)
    attempt_count = Column(Integer, default=0, nullable=False)
    max_retries = Column(Integer, default=3, nullable=False)
    next_retry_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)
    last_error = Column(Text, nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_outbox_status_next_retry", "status", "next_retry_at"),
        Index("ix_outbox_agency_status", "agency_id", "status"),
    )
