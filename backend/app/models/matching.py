import uuid
from sqlalchemy import (
    Column,
    String,
    Integer,
    Float,
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
from app.models.base import utc_now
from app.models.enums import (
    JobMatchRunStatus,
    MatchStatus,
    VerificationStatus,
)


class JobMatchRun(Base):
    __tablename__ = "job_match_runs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    initiated_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    scoring_version = Column(String(50), nullable=False, default="v1.0")
    matching_provider = Column(String(50), nullable=False, default="deterministic+semantic")
    embedding_model = Column(String(100), nullable=True)
    candidate_count = Column(Integer, default=0, nullable=False)
    completed_count = Column(Integer, default=0, nullable=False)
    failed_count = Column(Integer, default=0, nullable=False)
    status = Column(
        SQLEnum(JobMatchRunStatus),
        default=JobMatchRunStatus.PENDING,
        nullable=False,
        index=True,
    )
    started_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    job = relationship("Job", foreign_keys=[job_id], back_populates="match_runs")
    initiator = relationship("User", foreign_keys=[initiated_by])
    results = relationship(
        "JobMatchResult",
        back_populates="match_run",
        cascade="all, delete-orphan",
        order_by="JobMatchResult.overall_score.desc()",
    )

    __table_args__ = (
        Index("ix_match_runs_agency_job", "agency_id", "job_id"),
        Index("ix_match_runs_agency_status", "agency_id", "status"),
    )


class JobMatchResult(Base):
    __tablename__ = "job_match_results"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    match_run_id = Column(GUID, ForeignKey("job_match_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    overall_score = Column(Float, nullable=False, default=0.0)
    required_skills_score = Column(Float, nullable=False, default=0.0)
    experience_score = Column(Float, nullable=False, default=0.0)
    preferred_skills_score = Column(Float, nullable=False, default=0.0)
    project_relevance_score = Column(Float, nullable=False, default=0.0)
    other_criteria_score = Column(Float, nullable=False, default=0.0)
    matched_requirements_count = Column(Integer, default=0, nullable=False)
    partial_requirements_count = Column(Integer, default=0, nullable=False)
    missing_requirements_count = Column(Integer, default=0, nullable=False)
    needs_verification_count = Column(Integer, default=0, nullable=False)
    explanation = Column(Text, nullable=True)
    strengths = Column(Text, nullable=True)  # JSON-serialized list of strings
    skill_gaps = Column(Text, nullable=True)  # JSON-serialized list of strings
    verification_items = Column(Text, nullable=True)  # JSON-serialized list of strings
    suggested_questions = Column(Text, nullable=True)  # JSON-serialized list of strings
    scoring_version = Column(String(50), nullable=False, default="v1.0")
    source_fingerprint = Column(String(64), nullable=True)
    status = Column(String(50), nullable=False, default="COMPLETED")  # COMPLETED, STALE, HISTORICAL, FAILED
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)


    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    job = relationship("Job", foreign_keys=[job_id], back_populates="match_results")
    candidate = relationship("Candidate", foreign_keys=[candidate_id], back_populates="match_results")
    match_run = relationship("JobMatchRun", back_populates="results")

    evidences = relationship(
        "MatchEvidence",
        back_populates="match_result",
        cascade="all, delete-orphan",
        order_by="MatchEvidence.created_at.asc()",
    )

    __table_args__ = (
        UniqueConstraint("match_run_id", "candidate_id", name="uq_match_run_candidate"),
        Index("ix_match_results_agency_job_score", "agency_id", "job_id", "overall_score"),
        Index("ix_match_results_candidate", "candidate_id"),
    )


class MatchEvidence(Base):
    __tablename__ = "match_evidences"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    match_result_id = Column(GUID, ForeignKey("job_match_results.id", ondelete="CASCADE"), nullable=False, index=True)
    job_requirement_id = Column(GUID, ForeignKey("job_requirements.id", ondelete="SET NULL"), nullable=True, index=True)
    criterion_name = Column(String(255), nullable=False)
    criterion_type = Column(String(50), nullable=False, default="SKILL")  # REQUIRED_SKILL, PREFERRED_SKILL, EXPERIENCE, PROJECT, OTHER
    expected_requirement = Column(Text, nullable=False)
    evidence_status = Column(SQLEnum(MatchStatus), default=MatchStatus.NOT_FOUND, nullable=False, index=True)
    candidate_evidence = Column(Text, nullable=True)
    source_resume_id = Column(GUID, ForeignKey("resumes.id", ondelete="SET NULL"), nullable=True, index=True)
    source_page = Column(Integer, nullable=True)
    source_excerpt = Column(Text, nullable=True)
    semantic_similarity = Column(Float, nullable=True)
    score_contribution = Column(Float, default=0.0, nullable=False)
    explanation = Column(Text, nullable=True)
    verification_status = Column(
        SQLEnum(VerificationStatus),
        default=VerificationStatus.UNREVIEWED,
        nullable=False,
        index=True,
    )
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    match_result = relationship("JobMatchResult", back_populates="evidences")
    job_requirement = relationship("JobRequirement", foreign_keys=[job_requirement_id])
    source_resume = relationship("Resume", foreign_keys=[source_resume_id])

    __table_args__ = (
        Index("ix_match_evidences_result", "match_result_id"),
        Index("ix_match_evidences_status", "agency_id", "evidence_status"),
    )
