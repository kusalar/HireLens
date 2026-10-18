import uuid
from sqlalchemy import Column, String, Integer, Boolean, ForeignKey, Enum as SQLEnum, Text, Index, DateTime
from sqlalchemy.orm import relationship
from app.db.session import Base
from app.db.guid import GUID
from app.models.base import TimestampMixin, utc_now
from app.models.enums import CandidateProfileStatus

class Candidate(Base, TimestampMixin):
    __tablename__ = "candidates"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    full_name = Column(String(255), nullable=False, index=True)
    email = Column(String(255), nullable=True, index=True)
    phone_encrypted = Column(String(255), nullable=True)
    current_title = Column(String(255), nullable=True, index=True)
    total_experience_months = Column(Integer, default=0, nullable=False)
    current_location = Column(String(100), nullable=True, index=True)
    professional_summary = Column(Text, nullable=True)
    profile_status = Column(SQLEnum(CandidateProfileStatus), default=CandidateProfileStatus.ACTIVE, nullable=False, index=True)
    source = Column(String(100), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    experiences = relationship(
        "CandidateExperience",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    educations = relationship(
        "CandidateEducation",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    skills = relationship(
        "CandidateSkill",
        back_populates="candidate",
        cascade="all, delete-orphan",
    )
    notes = relationship(
        "RecruiterNote",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="RecruiterNote.created_at.desc()",
    )
    resumes = relationship(
        "Resume",
        back_populates="candidate",
    )
    match_results = relationship(
        "JobMatchResult",
        foreign_keys="JobMatchResult.candidate_id",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="JobMatchResult.created_at.desc()",
    )
    applications = relationship(
        "Application",
        foreign_keys="Application.candidate_id",
        back_populates="candidate",
        cascade="all, delete-orphan",
        order_by="Application.created_at.desc()",
    )



    __table_args__ = (
        Index("ix_candidates_agency_status", "agency_id", "profile_status"),
        Index("ix_candidates_agency_email", "agency_id", "email"),
        Index("ix_candidates_agency_source", "agency_id", "source"),
    )


class CandidateExperience(Base):
    __tablename__ = "candidate_experiences"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    company = Column(String(255), nullable=False)
    job_title = Column(String(255), nullable=False)
    start_date = Column(String(50), nullable=True)
    end_date = Column(String(50), nullable=True)
    description = Column(Text, nullable=True)

    # Relationship
    candidate = relationship("Candidate", back_populates="experiences")


class CandidateEducation(Base):
    __tablename__ = "candidate_educations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    institution = Column(String(255), nullable=False)
    qualification = Column(String(255), nullable=False)
    field_of_study = Column(String(255), nullable=True)
    start_year = Column(Integer, nullable=True)
    end_year = Column(Integer, nullable=True)

    # Relationship
    candidate = relationship("Candidate", back_populates="educations")


class CandidateSkill(Base):
    __tablename__ = "candidate_skills"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    skill_name = Column(String(150), nullable=False, index=True)
    normalized_skill = Column(String(150), nullable=True, index=True)
    proficiency = Column(String(50), nullable=True)
    evidence = Column(Text, nullable=True)
    source_page = Column(Integer, nullable=True)

    # Relationship
    candidate = relationship("Candidate", back_populates="skills")


class RecruiterNote(Base):
    __tablename__ = "recruiter_notes"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="CASCADE"), nullable=False, index=True)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    created_by = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    note = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    updated_at = Column(DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False)

    # Relationships
    candidate = relationship("Candidate", back_populates="notes")
    agency = relationship("Agency", foreign_keys=[agency_id])
    author = relationship("User", foreign_keys=[created_by])
