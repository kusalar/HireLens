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
    ModelType,
    PredictionAlgorithm,
    ForecastType,
    ConfidenceLevel,
    RecruitmentRiskType,
    RiskSeverity,
    RiskStatus,
    RecruiterUtilizationStatus,
)


class PredictionModelVersion(Base):
    """
    Registry of trained predictive models (or empirical baseline configurations)
    tracked per agency with evaluation metrics, hyper-parameters, and sample sizes.
    """
    __tablename__ = "prediction_model_versions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    model_type = Column(SQLEnum(ModelType), nullable=False, index=True)
    algorithm = Column(SQLEnum(PredictionAlgorithm), nullable=False)
    version_tag = Column(String(100), nullable=False)
    training_sample_size = Column(Integer, default=0, nullable=False)
    evaluation_metrics_json = Column(Text, nullable=True)  # JSON: {mae, rmse, r2, accuracy}
    hyperparameters_json = Column(Text, nullable=True)     # JSON dict
    feature_names_json = Column(Text, nullable=True)       # JSON list of feature names
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    trained_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    forecasts = relationship("RecruitmentForecast", back_populates="model_version")

    __table_args__ = (
        Index("ix_model_versions_agency_type_active", "agency_id", "model_type", "is_active"),
    )


class RecruitmentForecast(Base, TimestampMixin):
    """
    Agency-scoped recruitment forecasts (e.g., Time-to-Hire, Hiring Demand 30/60/90 days).
    Always stores confidence intervals and explicit fallback indicators.
    """
    __tablename__ = "recruitment_forecasts"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    department = Column(String(100), nullable=True, index=True)
    forecast_type = Column(SQLEnum(ForecastType), nullable=False, index=True)
    predicted_value = Column(Float, nullable=False)
    confidence_lower = Column(Float, nullable=False)
    confidence_upper = Column(Float, nullable=False)
    confidence_level = Column(
        SQLEnum(ConfidenceLevel),
        default=ConfidenceLevel.MEDIUM,
        nullable=False,
    )
    is_baseline_fallback = Column(Boolean, default=False, nullable=False)
    explanation = Column(Text, nullable=True)
    factors_json = Column(Text, nullable=True)  # JSON list of contributing factors
    model_version_id = Column(
        GUID,
        ForeignKey("prediction_model_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    horizon_days = Column(Integer, default=30, nullable=False)
    forecast_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    job = relationship("Job", foreign_keys=[job_id])
    model_version = relationship("PredictionModelVersion", back_populates="forecasts")
    evaluations = relationship(
        "ForecastEvaluation",
        back_populates="forecast",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_forecasts_agency_type_date", "agency_id", "forecast_type", "forecast_date"),
        Index("ix_forecasts_agency_job", "agency_id", "job_id"),
    )


class RecruitmentRisk(Base, TimestampMixin):
    """
    Detected recruitment risks across candidate pipelines, stage stagnations,
    scheduling delays, drop-off vulnerabilities, and expense overruns.
    """
    __tablename__ = "recruitment_risks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    risk_type = Column(SQLEnum(RecruitmentRiskType), nullable=False, index=True)
    severity = Column(SQLEnum(RiskSeverity), default=RiskSeverity.MEDIUM, nullable=False, index=True)
    status = Column(SQLEnum(RiskStatus), default=RiskStatus.OPEN, nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id = Column(GUID, nullable=True, index=True)
    recruiter_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    evidence_payload_json = Column(Text, nullable=True)  # JSON metrics and audit evidence
    recommended_action = Column(Text, nullable=False)
    confidence_score = Column(Float, default=0.85, nullable=False)
    acknowledged_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    resolution_notes = Column(Text, nullable=True)
    detected_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    job = relationship("Job", foreign_keys=[job_id])
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    recruiter = relationship("User", foreign_keys=[recruiter_id])
    acknowledged_by = relationship("User", foreign_keys=[acknowledged_by_user_id])

    __table_args__ = (
        Index("ix_risks_agency_status_severity", "agency_id", "status", "severity"),
        Index("ix_risks_agency_job", "agency_id", "job_id"),
    )


class CapacitySnapshot(Base):
    """
    Periodic operational capacity snapshot for a recruiter, measuring workload balance,
    interviews, active applications, and advisory workload redistribution.
    """
    __tablename__ = "capacity_snapshots"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    recruiter_id = Column(GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    active_applications_count = Column(Integer, default=0, nullable=False)
    upcoming_interviews_count = Column(Integer, default=0, nullable=False)
    open_requisitions_count = Column(Integer, default=0, nullable=False)
    workload_index = Column(Float, default=0.0, nullable=False)
    utilization_status = Column(
        SQLEnum(RecruiterUtilizationStatus),
        default=RecruiterUtilizationStatus.OPTIMAL,
        nullable=False,
    )
    recommendations_json = Column(Text, nullable=True)  # JSON list of capacity suggestions
    snapshot_date = Column(DateTime(timezone=True), default=utc_now, nullable=False)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    recruiter = relationship("User", foreign_keys=[recruiter_id])

    __table_args__ = (
        Index("ix_capacity_agency_recruiter_date", "agency_id", "recruiter_id", "snapshot_date"),
    )


class ForecastEvaluation(Base):
    """
    Ex-post accuracy evaluation comparing forecasted values with actual outcomes.
    """
    __tablename__ = "forecast_evaluations"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    forecast_id = Column(
        GUID,
        ForeignKey("recruitment_forecasts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actual_value = Column(Float, nullable=False)
    absolute_error = Column(Float, nullable=False)
    percentage_error = Column(Float, nullable=False)
    evaluated_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    forecast = relationship("RecruitmentForecast", back_populates="evaluations")
