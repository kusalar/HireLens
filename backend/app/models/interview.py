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
    InterviewMode,
    InterviewStatus,
    InterviewRoundType,
    ParticipantRole,
    AttendanceStatus,
    FeedbackRecommendation,
)


class Interview(Base, TimestampMixin):
    __tablename__ = "interviews"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(GUID, ForeignKey("applications.id", ondelete="RESTRICT"), nullable=False, index=True)
    round_name = Column(String(100), nullable=False)
    round_type = Column(
        SQLEnum(InterviewRoundType),
        default=InterviewRoundType.TECHNICAL,
        nullable=False,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    interview_mode = Column(
        SQLEnum(InterviewMode),
        default=InterviewMode.ONLINE,
        nullable=False,
    )
    scheduled_start = Column(DateTime(timezone=True), nullable=False, index=True)
    scheduled_end = Column(DateTime(timezone=True), nullable=False, index=True)
    timezone = Column(String(50), default="Asia/Kolkata", nullable=False)
    location = Column(String(255), nullable=True)
    meeting_url = Column(String(500), nullable=True)
    status = Column(
        SQLEnum(InterviewStatus),
        default=InterviewStatus.SCHEDULED,
        nullable=False,
        index=True,
    )
    version = Column(Integer, default=1, nullable=False)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    cancellation_reason = Column(Text, nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    application = relationship("Application", foreign_keys=[application_id], back_populates="interviews")
    creator = relationship("User", foreign_keys=[created_by])
    participants = relationship(
        "InterviewParticipant",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewParticipant.created_at.asc()",
    )
    feedbacks = relationship(
        "InterviewFeedback",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewFeedback.created_at.asc()",
    )
    history = relationship(
        "InterviewHistory",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewHistory.created_at.desc()",
    )

    __table_args__ = (
        Index("ix_interviews_agency_app", "agency_id", "application_id"),
        Index("ix_interviews_agency_status", "agency_id", "status"),
        Index("ix_interviews_agency_start", "agency_id", "scheduled_start"),
        Index("ix_interviews_agency_app_status", "agency_id", "application_id", "status"),
    )


class InterviewParticipant(Base):
    __tablename__ = "interview_participants"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(GUID, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    participant_name = Column(String(150), nullable=False)
    participant_email = Column(String(255), nullable=False)
    participant_role = Column(
        SQLEnum(ParticipantRole),
        default=ParticipantRole.INTERVIEWER,
        nullable=False,
    )
    attendance_status = Column(
        SQLEnum(AttendanceStatus),
        default=AttendanceStatus.INVITED,
        nullable=False,
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    interview = relationship("Interview", back_populates="participants")
    user = relationship("User", foreign_keys=[user_id])
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_participants_interview_email", "interview_id", "participant_email"),
        Index("ix_participants_interview_user", "interview_id", "user_id"),
    )


class InterviewFeedback(Base):
    __tablename__ = "interview_feedbacks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(GUID, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    reviewer_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_rating = Column(Integer, nullable=False)  # 1 to 5
    recommendation = Column(
        SQLEnum(FeedbackRecommendation),
        nullable=False,
        index=True,
    )
    technical_assessment = Column(Text, nullable=True)
    communication_assessment = Column(Text, nullable=True)
    problem_solving_assessment = Column(Text, nullable=True)
    role_specific_assessment = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)  # JSON-encoded array of strengths
    concerns = Column(Text, nullable=True)   # JSON-encoded array of concerns
    detailed_feedback = Column(Text, nullable=False)
    is_private = Column(Boolean, default=False, nullable=False)
    submitted_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    interview = relationship("Interview", back_populates="feedbacks")
    reviewer = relationship("User", foreign_keys=[reviewer_id])
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        UniqueConstraint("interview_id", "reviewer_id", name="uq_interview_reviewer_feedback"),
        Index("ix_interview_feedbacks_interview", "interview_id"),
    )


class InterviewHistory(Base):
    __tablename__ = "interview_histories"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    interview_id = Column(GUID, ForeignKey("interviews.id", ondelete="CASCADE"), nullable=False, index=True)
    actor_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    action = Column(String(100), nullable=False)
    previous_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    interview = relationship("Interview", back_populates="history")
    actor = relationship("User", foreign_keys=[actor_id])
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_interview_histories_interview_created", "interview_id", "created_at"),
    )
