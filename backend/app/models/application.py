import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    ForeignKey,
    Enum as SQLEnum,
    Text,
    Index,
    DateTime,
    text,
)
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import PipelineStageType


class Application(Base, TimestampMixin):
    __tablename__ = "applications"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="RESTRICT"), nullable=False, index=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="RESTRICT"), nullable=False, index=True)
    status = Column(
        SQLEnum(PipelineStageType),
        default=PipelineStageType.APPLIED,
        nullable=False,
        index=True,
    )
    source = Column(String(100), default="DIRECT_APPLICATION", nullable=True)
    applied_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    shortlisted_at = Column(DateTime(timezone=True), nullable=True)
    last_activity_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    assigned_recruiter_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    recruiter_summary = Column(Text, nullable=True)
    archived_at = Column(DateTime(timezone=True), nullable=True)
    version = Column(Integer, default=1, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    job = relationship("Job", foreign_keys=[job_id], back_populates="applications")
    candidate = relationship("Candidate", foreign_keys=[candidate_id], back_populates="applications")
    assigned_recruiter = relationship("User", foreign_keys=[assigned_recruiter_id])
    stage_history = relationship(
        "ApplicationStageHistory",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationStageHistory.created_at.asc()",
    )
    notes = relationship(
        "ApplicationNote",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="ApplicationNote.created_at.desc()",
    )
    interviews = relationship(
        "Interview",
        back_populates="application",
        cascade="all, delete-orphan",
        order_by="Interview.scheduled_start.desc()",
    )

    __table_args__ = (
        Index("ix_applications_agency_job", "agency_id", "job_id"),
        Index("ix_applications_agency_candidate", "agency_id", "candidate_id"),
        Index("ix_applications_agency_job_candidate", "agency_id", "job_id", "candidate_id"),
        Index("ix_applications_agency_status", "agency_id", "status"),
        Index("ix_applications_agency_recruiter", "agency_id", "assigned_recruiter_id"),
        Index("ix_applications_agency_source", "agency_id", "source"),
        Index("ix_applications_agency_applied_at", "agency_id", "applied_at"),
        Index(
            "uq_active_application_per_job_candidate",
            "agency_id",
            "job_id",
            "candidate_id",
            unique=True,
            postgresql_where=text("archived_at IS NULL AND status != 'WITHDRAWN'"),
            sqlite_where=text("archived_at IS NULL AND status != 'WITHDRAWN'"),
        ),
    )


class ApplicationStageHistory(Base):
    __tablename__ = "application_stage_histories"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    previous_stage = Column(SQLEnum(PipelineStageType), nullable=True)
    new_stage = Column(SQLEnum(PipelineStageType), nullable=False)
    changed_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="stage_history")
    user = relationship("User", foreign_keys=[changed_by])
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_stage_histories_app_created", "application_id", "created_at"),
    )


class ApplicationNote(Base):
    __tablename__ = "application_notes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    application_id = Column(GUID, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False, index=True)
    author_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    application = relationship("Application", back_populates="notes")
    author = relationship("User", foreign_keys=[author_id])
    agency = relationship("Agency", foreign_keys=[agency_id])

    __table_args__ = (
        Index("ix_application_notes_app_created", "application_id", "created_at"),
    )
