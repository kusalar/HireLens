import uuid
from sqlalchemy import Column, String, Integer, Float, ForeignKey, Enum as SQLEnum, Text, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import (
    ResumeProcessingStatus,
    VerificationStatus,
    RecruiterReviewStatus,
    ParseRunStatus,
)


class Resume(Base, TimestampMixin):
    __tablename__ = "resumes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    uploaded_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    original_filename = Column(String(255), nullable=False)
    stored_filename = Column(String(255), nullable=False)
    storage_key = Column(String(512), nullable=False)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False, index=True)
    page_count = Column(Integer, nullable=True)
    extracted_text = Column(Text, nullable=True)
    language = Column(String(20), nullable=True, default="en")
    processing_status = Column(
        SQLEnum(ResumeProcessingStatus),
        default=ResumeProcessingStatus.UPLOADED,
        nullable=False,
        index=True,
    )
    upload_status = Column(String(50), default="COMPLETED", nullable=False)
    error_message = Column(Text, nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    uploader = relationship("User", foreign_keys=[uploaded_by])
    parse_runs = relationship(
        "ResumeParseRun",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeParseRun.created_at.desc()",
    )
    extracted_profiles = relationship(
        "ResumeExtractedProfile",
        back_populates="resume",
        cascade="all, delete-orphan",
        order_by="ResumeExtractedProfile.created_at.desc()",
    )
    evidences = relationship(
        "ResumeEvidence",
        back_populates="resume",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_resumes_agency_sha256", "agency_id", "sha256_hash", unique=True),
        Index("ix_resumes_agency_status", "agency_id", "processing_status"),
    )


class ResumeParseRun(Base):
    __tablename__ = "resume_parse_runs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    resume_id = Column(GUID, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    provider = Column(String(50), nullable=False)  # ollama, hosted, etc.
    model_name = Column(String(100), nullable=False)
    model_version = Column(String(50), nullable=True)
    extraction_method = Column(String(100), nullable=False)  # pymupdf+llm, docx+llm, ocr+llm
    status = Column(SQLEnum(ParseRunStatus), default=ParseRunStatus.PENDING, nullable=False, index=True)
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    processing_duration_ms = Column(Integer, nullable=True)
    error_code = Column(String(50), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="parse_runs")
    agency = relationship("Agency", foreign_keys=[agency_id])
    extracted_profile = relationship(
        "ResumeExtractedProfile",
        back_populates="parse_run",
        uselist=False,
        cascade="all, delete-orphan",
    )
    evidences = relationship(
        "ResumeEvidence",
        back_populates="parse_run",
        cascade="all, delete-orphan",
    )


class ResumeExtractedProfile(Base):
    __tablename__ = "resume_extracted_profiles"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    resume_id = Column(GUID, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    parse_run_id = Column(GUID, ForeignKey("resume_parse_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    extracted_name = Column(String(255), nullable=True)
    extracted_email = Column(String(255), nullable=True)
    extracted_phone = Column(String(100), nullable=True)
    extracted_location = Column(String(255), nullable=True)
    extracted_current_title = Column(String(255), nullable=True)
    extracted_summary = Column(Text, nullable=True)
    extracted_experience_months = Column(Integer, nullable=True)
    structured_extraction_json = Column(Text, nullable=True)  # Validated JSON string
    overall_confidence = Column(Float, nullable=True, default=0.0)
    recruiter_review_status = Column(
        SQLEnum(RecruiterReviewStatus),
        default=RecruiterReviewStatus.PENDING,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="extracted_profiles")
    parse_run = relationship("ResumeParseRun", back_populates="extracted_profile")
    agency = relationship("Agency", foreign_keys=[agency_id])


class ResumeEvidence(Base):
    __tablename__ = "resume_evidences"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    parse_run_id = Column(GUID, ForeignKey("resume_parse_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    resume_id = Column(GUID, ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False, index=True)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    field_name = Column(String(100), nullable=False, index=True)
    extracted_value = Column(Text, nullable=False)
    corrected_value = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)
    source_excerpt = Column(Text, nullable=True)
    confidence = Column(Float, nullable=True, default=1.0)
    verification_status = Column(
        SQLEnum(VerificationStatus),
        default=VerificationStatus.UNREVIEWED,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    resume = relationship("Resume", back_populates="evidences")
    parse_run = relationship("ResumeParseRun", back_populates="evidences")
    agency = relationship("Agency", foreign_keys=[agency_id])
