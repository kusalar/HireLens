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
    WorkflowTriggerType,
    WorkflowActionType,
    WorkflowExecutionStatus,
    WorkflowStepStatus,
    WorkflowApprovalStatus,
    RecruiterTaskStatus,
    RecruiterTaskPriority,
)


class RecruitmentWorkflow(Base, TimestampMixin):
    """
    Defines a recruitment automation workflow rule scoped strictly to an agency.
    Workflow rules are versioned and can be activated/deactivated.
    """
    __tablename__ = "recruitment_workflows"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    trigger_type = Column(SQLEnum(WorkflowTriggerType), nullable=False, index=True)
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    versions = relationship(
        "WorkflowVersion",
        back_populates="workflow",
        cascade="all, delete-orphan",
        order_by="WorkflowVersion.version_number.desc()",
    )
    executions = relationship(
        "WorkflowExecution",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "WorkflowAuditLog",
        back_populates="workflow",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("ix_workflows_agency_active", "agency_id", "is_active"),
        Index("ix_workflows_agency_trigger", "agency_id", "trigger_type"),
    )


class WorkflowVersion(Base):
    """
    Immutable version snapshot of a workflow definition (trigger configuration, condition tree, and actions).
    """
    __tablename__ = "workflow_versions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    workflow_id = Column(
        GUID,
        ForeignKey("recruitment_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    version_number = Column(Integer, nullable=False)
    definition_json = Column(Text, nullable=False)  # JSON-encoded trigger_config, conditions, actions
    change_summary = Column(String(255), nullable=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    workflow = relationship("RecruitmentWorkflow", back_populates="versions")
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    executions = relationship("WorkflowExecution", back_populates="workflow_version")

    __table_args__ = (
        UniqueConstraint("workflow_id", "version_number", name="uq_workflow_versions_workflow_version"),
    )


class WorkflowExecution(Base, TimestampMixin):
    """
    Individual run instance of a workflow rule triggered by a recruitment lifecycle event.
    Guarantees idempotency and tracks step-by-step progress.
    """
    __tablename__ = "workflow_executions"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(
        GUID,
        ForeignKey("recruitment_workflows.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    workflow_version_id = Column(
        GUID,
        ForeignKey("workflow_versions.id", ondelete="SET NULL"),
        nullable=True,
    )
    trigger_event = Column(SQLEnum(WorkflowTriggerType), nullable=False)
    trigger_entity_type = Column(String(50), nullable=False)  # candidate, application, interview, etc.
    trigger_entity_id = Column(GUID, nullable=True, index=True)
    status = Column(
        SQLEnum(WorkflowExecutionStatus),
        default=WorkflowExecutionStatus.PENDING,
        nullable=False,
        index=True,
    )
    idempotency_key = Column(String(255), nullable=False, index=True)
    context_snapshot = Column(Text, nullable=True)  # JSON sanitized event and entity context
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0, nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    workflow = relationship("RecruitmentWorkflow", back_populates="executions")
    workflow_version = relationship("WorkflowVersion", back_populates="executions")
    steps = relationship(
        "WorkflowExecutionStep",
        back_populates="execution",
        cascade="all, delete-orphan",
        order_by="WorkflowExecutionStep.step_index.asc()",
    )
    approvals = relationship(
        "WorkflowApproval",
        back_populates="execution",
        cascade="all, delete-orphan",
    )
    audit_logs = relationship(
        "WorkflowAuditLog",
        back_populates="execution",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("agency_id", "idempotency_key", name="uq_workflow_executions_agency_idempotency"),
        Index("ix_workflow_executions_agency_status", "agency_id", "status"),
        Index("ix_workflow_executions_agency_created", "agency_id", "created_at"),
    )


class WorkflowExecutionStep(Base):
    """
    Granular action step inside an active workflow execution run.
    """
    __tablename__ = "workflow_execution_steps"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    execution_id = Column(
        GUID,
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index = Column(Integer, nullable=False)
    action_type = Column(SQLEnum(WorkflowActionType), nullable=False)
    action_config = Column(Text, nullable=False)  # JSON-encoded configuration
    status = Column(
        SQLEnum(WorkflowStepStatus),
        default=WorkflowStepStatus.PENDING,
        nullable=False,
    )
    input_payload = Column(Text, nullable=True)
    output_payload = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False)

    # Relationships
    execution = relationship("WorkflowExecution", back_populates="steps")
    approval = relationship("WorkflowApproval", back_populates="step", uselist=False)

    __table_args__ = (
        Index("ix_workflow_steps_exec_index", "execution_id", "step_index"),
    )


class WorkflowApproval(Base, TimestampMixin):
    """
    Human-in-the-loop approval item queued when a workflow encounters a sensitive action step.
    Must be explicitly approved or rejected by an authorized recruiter or administrator.
    """
    __tablename__ = "workflow_approvals"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    execution_id = Column(
        GUID,
        ForeignKey("workflow_executions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_id = Column(
        GUID,
        ForeignKey("workflow_execution_steps.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        SQLEnum(WorkflowApprovalStatus),
        default=WorkflowApprovalStatus.PENDING,
        nullable=False,
        index=True,
    )
    requested_action = Column(SQLEnum(WorkflowActionType), nullable=False)
    action_payload = Column(Text, nullable=True)  # JSON payload to execute once approved
    assigned_role = Column(String(50), default="AGENCY_ADMIN", nullable=False)
    assigned_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    approved_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rejection_reason = Column(Text, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=True, index=True)
    decided_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    execution = relationship("WorkflowExecution", back_populates="approvals")
    step = relationship("WorkflowExecutionStep", back_populates="approval")
    assigned_user = relationship("User", foreign_keys=[assigned_user_id])
    approved_by_user = relationship("User", foreign_keys=[approved_by_user_id])

    __table_args__ = (
        Index("ix_workflow_approvals_agency_status", "agency_id", "status"),
        Index("ix_workflow_approvals_expires", "status", "expires_at"),
    )


class RecruiterTask(Base, TimestampMixin):
    """
    Operational follow-up task created automatically by workflows or manually by team members.
    Assigned to a recruiter and linked to candidates, jobs, applications, or interviews.
    """
    __tablename__ = "recruiter_tasks"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(
        SQLEnum(RecruiterTaskPriority),
        default=RecruiterTaskPriority.MEDIUM,
        nullable=False,
    )
    status = Column(
        SQLEnum(RecruiterTaskStatus),
        default=RecruiterTaskStatus.PENDING,
        nullable=False,
        index=True,
    )
    assigned_to_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    created_by_user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    candidate_id = Column(GUID, ForeignKey("candidates.id", ondelete="SET NULL"), nullable=True, index=True)
    job_id = Column(GUID, ForeignKey("jobs.id", ondelete="SET NULL"), nullable=True, index=True)
    application_id = Column(GUID, ForeignKey("applications.id", ondelete="SET NULL"), nullable=True, index=True)
    interview_id = Column(GUID, ForeignKey("interviews.id", ondelete="SET NULL"), nullable=True, index=True)
    execution_id = Column(GUID, ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True)
    due_date = Column(DateTime(timezone=True), nullable=True, index=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    assigned_to = relationship("User", foreign_keys=[assigned_to_user_id])
    created_by = relationship("User", foreign_keys=[created_by_user_id])
    candidate = relationship("Candidate", foreign_keys=[candidate_id])
    job = relationship("Job", foreign_keys=[job_id])
    application = relationship("Application", foreign_keys=[application_id])
    interview = relationship("Interview", foreign_keys=[interview_id])

    __table_args__ = (
        Index("ix_recruiter_tasks_agency_status", "agency_id", "status"),
        Index("ix_recruiter_tasks_assigned_status", "assigned_to_user_id", "status"),
    )


class WorkflowAuditLog(Base):
    """
    Immutable audit trail of all workflow configurations, version changes, executions, and approvals.
    """
    __tablename__ = "workflow_audit_logs"

    id = Column(GUID, primary_key=True, default=uuid.uuid4)
    agency_id = Column(GUID, ForeignKey("agencies.id", ondelete="CASCADE"), nullable=False, index=True)
    workflow_id = Column(GUID, ForeignKey("recruitment_workflows.id", ondelete="SET NULL"), nullable=True, index=True)
    execution_id = Column(GUID, ForeignKey("workflow_executions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(GUID, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    action = Column(String(100), nullable=False)
    details = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utc_now, nullable=False, index=True)

    # Relationships
    agency = relationship("Agency", foreign_keys=[agency_id])
    workflow = relationship("RecruitmentWorkflow", back_populates="audit_logs")
    execution = relationship("WorkflowExecution", back_populates="audit_logs")
    user = relationship("User", foreign_keys=[user_id])

    __table_args__ = (
        Index("ix_workflow_audit_agency_created", "agency_id", "created_at"),
    )
