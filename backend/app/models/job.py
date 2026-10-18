import uuid
from sqlalchemy import Column, String, Integer, Float, Boolean, ForeignKey, Enum as SQLEnum, Text, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import WorkMode, EmploymentType, JobStatus, RequirementType

class Job(Base, TimestampMixin):
    __tablename__ = "jobs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    title = Column(String(255), nullable=False, index=True)
    department = Column(String(100), nullable=True)
    description = Column(Text, nullable=True)
    responsibilities = Column(Text, nullable=True)
    location = Column(String(100), nullable=True)
    work_mode = Column(SQLEnum(WorkMode), default=WorkMode.ONSITE, nullable=False)
    employment_type = Column(SQLEnum(EmploymentType), default=EmploymentType.FULL_TIME, nullable=False)
    minimum_experience = Column(Integer, default=0, nullable=False)
    maximum_experience = Column(Integer, nullable=True)
    status = Column(SQLEnum(JobStatus), default=JobStatus.ACTIVE, nullable=False, index=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    creator = relationship("User", foreign_keys=[created_by])
    requirements = relationship(
        "JobRequirement",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobRequirement.created_at",
    )
    match_runs = relationship(
        "JobMatchRun",
        foreign_keys="JobMatchRun.job_id",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="JobMatchRun.created_at.desc()",
    )
    match_results = relationship(
        "JobMatchResult",
        foreign_keys="JobMatchResult.job_id",
        back_populates="job",
        cascade="all, delete-orphan",
    )
    applications = relationship(
        "Application",
        foreign_keys="Application.job_id",
        back_populates="job",
        cascade="all, delete-orphan",
        order_by="Application.created_at.desc()",
    )



    __table_args__ = (
        Index("ix_jobs_agency_status", "agency_id", "status"),
    )


class JobRequirement(Base):
    __tablename__ = "job_requirements"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    requirement_text = Column(Text, nullable=False)
    normalized_skill = Column(String(150), nullable=True, index=True)
    requirement_type = Column(SQLEnum(RequirementType), default=RequirementType.SKILL, nullable=False)
    importance_weight = Column(Float, default=1.0, nullable=False)
    is_mandatory = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationship
    job = relationship("Job", back_populates="requirements")
