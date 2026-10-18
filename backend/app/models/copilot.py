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
from app.models.enums import (
    CopilotActionType,
    CopilotMessageRole,
    CopilotContextType,
)


class CopilotConversation(Base, TimestampMixin):
    """
    Persistent conversation session between an authorized recruiter and the AI Copilot.
    Strictly isolated by agency_id with user ownership tracking.
    """
    __tablename__ = "copilot_conversations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False, default="New Recruitment Conversation")
    context_type = Column(
        SQLEnum(CopilotContextType),
        default=CopilotContextType.AGENCY_OVERVIEW,
        nullable=False,
    )
    context_id = Column(GUID, nullable=True, index=True)  # Optional reference to job, candidate, application, interview
    is_archived = Column(Boolean, default=False, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    user = relationship("User", foreign_keys=[user_id])
    messages = relationship(
        "CopilotMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CopilotMessage.created_at.asc()",
    )
    audit_logs = relationship(
        "CopilotAuditLog",
        back_populates="conversation",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_copilot_conv_agency_user", "agency_id", "user_id"),
        Index("ix_copilot_conv_agency_updated", "agency_id", "updated_at"),
    )


class CopilotMessage(Base):
    """
    Individual message turn within a Copilot conversation.
    Grounding sources and non-PII context snapshots are stored for explainability.
    """
    __tablename__ = "copilot_messages"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(
        GUID,
        ForeignKey("copilot_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role = Column(
        SQLEnum(CopilotMessageRole),
        default=CopilotMessageRole.USER,
        nullable=False,
    )
    content = Column(Text, nullable=False)
    context_snapshot = Column(Text, nullable=True)  # JSON-encoded sanitized context summary
    sources = Column(Text, nullable=True)           # JSON-encoded list of cited entity references
    model_used = Column(String(100), nullable=True)
    prompt_tokens = Column(Integer, nullable=True)
    completion_tokens = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    conversation = relationship("CopilotConversation", back_populates="messages")

    __table_args__ = (
        Index("ix_copilot_messages_conv_created", "conversation_id", "created_at"),
    )


class CopilotAuditLog(Base):
    """
    Comprehensive audit trail for every AI Copilot operation.
    Tracks user, agency, action type, target entity, duration, and status without logging PII.
    """
    __tablename__ = "copilot_audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    conversation_id = Column(
        GUID,
        ForeignKey("copilot_conversations.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    action_type = Column(
        SQLEnum(CopilotActionType),
        nullable=False,
        index=True,
    )
    target_entity_type = Column(String(50), nullable=True)  # "job", "candidate", "interview", "analytics"
    target_entity_id = Column(GUID, nullable=True, index=True)
    provider_used = Column(String(100), nullable=True)
    status = Column(String(50), default="SUCCESS", nullable=False)  # "SUCCESS", "FAILED", "BLOCKED_GUARDRAIL"
    error_message = Column(Text, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    user = relationship("User", foreign_keys=[user_id])
    conversation = relationship("CopilotConversation", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_copilot_audit_agency_created", "agency_id", "created_at"),
        Index("ix_copilot_audit_agency_action", "agency_id", "action_type"),
    )
