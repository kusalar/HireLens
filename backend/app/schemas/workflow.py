import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any, Union, Literal
from pydantic import BaseModel, Field, ConfigDict, field_validator
from app.models.enums import (
    WorkflowTriggerType,
    WorkflowActionType,
    WorkflowExecutionStatus,
    WorkflowStepStatus,
    WorkflowApprovalStatus,
    RecruiterTaskStatus,
    RecruiterTaskPriority,
)

# -------------------------------------------------------------
# Condition Engine Schemas
# -------------------------------------------------------------

ConditionOperator = Literal[
    "EQUALS",
    "NOT_EQUALS",
    "GREATER_THAN",
    "GREATER_THAN_OR_EQUAL",
    "LESS_THAN",
    "LESS_THAN_OR_EQUAL",
    "CONTAINS",
    "NOT_CONTAINS",
    "IN",
    "NOT_IN",
    "EXISTS",
    "NOT_EXISTS",
]


class ConditionLeaf(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: str = Field(..., min_length=1, max_length=100, description="Field path e.g. 'match_score', 'candidate.skills'")
    operator: ConditionOperator
    value: Optional[Any] = Field(default=None, description="Expected literal value, number, string, or list")


class ConditionGroup(BaseModel):
    model_config = ConfigDict(extra="forbid")

    logical_operator: Literal["AND", "OR"] = "AND"
    conditions: List[Union["ConditionLeaf", "ConditionGroup"]] = Field(
        default_factory=list,
        max_length=20,
        description="Nested child conditions or leaf nodes",
    )


# Enable recursive model definition
ConditionGroup.model_rebuild()

# A ConditionTree is either a group or a single leaf or empty
ConditionTree = Union[ConditionGroup, ConditionLeaf]


# -------------------------------------------------------------
# Action Step Schemas
# -------------------------------------------------------------

class WorkflowActionStepConfig(BaseModel):
    model_config = ConfigDict(extra="allow")

    # Common parameters
    action_type: WorkflowActionType
    step_index: int = 0
    description: Optional[str] = None
    requires_approval: bool = False
    approval_role: Optional[str] = "AGENCY_ADMIN"

    # Action-specific config payloads:
    # 1. SEND_CANDIDATE_COMMUNICATION
    email_subject: Optional[str] = None
    email_body_template: Optional[str] = None

    # 2. NOTIFY_RECRUITERS
    notification_title: Optional[str] = None
    notification_message: Optional[str] = None
    target_recruiter_ids: Optional[List[uuid.UUID]] = None

    # 3. GENERATE_INTERVIEW_PREP
    interview_round_type: Optional[str] = None

    # 4. CREATE_RECRUITER_TASK
    task_title: Optional[str] = None
    task_description: Optional[str] = None
    task_priority: Optional[RecruiterTaskPriority] = RecruiterTaskPriority.MEDIUM
    task_due_days: Optional[int] = 2

    # 5. TRIGGER_CALENDAR_SYNC
    calendar_operation: Optional[str] = "RESYNC"

    # 6. GENERATE_ANALYTICS_EVENT
    event_name: Optional[str] = None
    event_metadata: Optional[Dict[str, Any]] = None

    # Delay execution option
    delay_minutes: Optional[int] = Field(default=0, ge=0, le=10080)  # up to 7 days


class WorkflowDefinition(BaseModel):
    trigger_config: Optional[Dict[str, Any]] = Field(default_factory=dict)
    conditions: Optional[ConditionGroup] = None
    actions: List[WorkflowActionStepConfig] = Field(default_factory=list, max_length=15)


# -------------------------------------------------------------
# Workflow CRUD Schemas
# -------------------------------------------------------------

class WorkflowCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    trigger_type: WorkflowTriggerType
    is_active: bool = True
    definition: WorkflowDefinition
    change_summary: Optional[str] = "Initial workflow creation"


class WorkflowUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    trigger_type: Optional[WorkflowTriggerType] = None
    is_active: Optional[bool] = None
    definition: Optional[WorkflowDefinition] = None
    change_summary: Optional[str] = None


class WorkflowVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workflow_id: uuid.UUID
    version_number: int
    definition: Dict[str, Any]
    change_summary: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime


class WorkflowRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    name: str
    description: Optional[str] = None
    trigger_type: WorkflowTriggerType
    is_active: bool
    created_by_user_id: Optional[uuid.UUID] = None
    created_at: datetime
    updated_at: datetime
    current_version: Optional[WorkflowVersionRead] = None
    execution_count: int = 0


class WorkflowListResponse(BaseModel):
    items: List[WorkflowRead]
    total: int


# -------------------------------------------------------------
# Workflow Execution Schemas
# -------------------------------------------------------------

class WorkflowExecutionStepRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    execution_id: uuid.UUID
    step_index: int
    action_type: WorkflowActionType
    status: WorkflowStepStatus
    action_config: Optional[Dict[str, Any]] = None
    input_payload: Optional[Dict[str, Any]] = None
    output_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime


class WorkflowExecutionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    workflow_id: uuid.UUID
    workflow_name: Optional[str] = None
    workflow_version_id: Optional[uuid.UUID] = None
    trigger_event: WorkflowTriggerType
    trigger_entity_type: str
    trigger_entity_id: Optional[uuid.UUID] = None
    status: WorkflowExecutionStatus
    idempotency_key: str
    retry_count: int
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    steps: List[WorkflowExecutionStepRead] = []


class WorkflowExecutionListResponse(BaseModel):
    items: List[WorkflowExecutionRead]
    total: int


class WorkflowManualTriggerRequest(BaseModel):
    entity_type: str = Field(..., description="candidate, application, or interview")
    entity_id: uuid.UUID


# -------------------------------------------------------------
# Human Approval Schemas
# -------------------------------------------------------------

class WorkflowApprovalDecision(BaseModel):
    decision: Literal["APPROVE", "REJECT"]
    rejection_reason: Optional[str] = None

    @field_validator("rejection_reason")
    @classmethod
    def validate_rejection_reason(cls, v, info):
        # Mandatory rejection reason if rejected
        data = info.data
        if data.get("decision") == "REJECT" and (not v or not v.strip()):
            raise ValueError("Rejection reason is mandatory when rejecting a workflow approval request.")
        return v.strip() if v else None


class WorkflowApprovalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    execution_id: uuid.UUID
    step_id: Optional[uuid.UUID] = None
    title: str
    description: Optional[str] = None
    status: WorkflowApprovalStatus
    requested_action: WorkflowActionType
    action_payload: Optional[Dict[str, Any]] = None
    assigned_role: str
    assigned_user_id: Optional[uuid.UUID] = None
    approved_by_user_id: Optional[uuid.UUID] = None
    rejection_reason: Optional[str] = None
    expires_at: Optional[datetime] = None
    decided_at: Optional[datetime] = None
    created_at: datetime
    workflow_name: Optional[str] = None


class WorkflowApprovalListResponse(BaseModel):
    items: List[WorkflowApprovalRead]
    total: int


# -------------------------------------------------------------
# Recruiter Task Schemas
# -------------------------------------------------------------

class RecruiterTaskCreate(BaseModel):
    title: str = Field(..., min_length=2, max_length=255)
    description: Optional[str] = None
    priority: RecruiterTaskPriority = RecruiterTaskPriority.MEDIUM
    assigned_to_user_id: Optional[uuid.UUID] = None
    candidate_id: Optional[uuid.UUID] = None
    job_id: Optional[uuid.UUID] = None
    application_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None


class RecruiterTaskUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=2, max_length=255)
    description: Optional[str] = None
    priority: Optional[RecruiterTaskPriority] = None
    status: Optional[RecruiterTaskStatus] = None
    assigned_to_user_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None


class RecruiterTaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    title: str
    description: Optional[str] = None
    priority: RecruiterTaskPriority
    status: RecruiterTaskStatus
    assigned_to_user_id: Optional[uuid.UUID] = None
    assigned_to_name: Optional[str] = None
    created_by_user_id: Optional[uuid.UUID] = None
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = None
    job_id: Optional[uuid.UUID] = None
    job_title: Optional[str] = None
    application_id: Optional[uuid.UUID] = None
    interview_id: Optional[uuid.UUID] = None
    due_date: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RecruiterTaskListResponse(BaseModel):
    items: List[RecruiterTaskRead]
    total: int


# -------------------------------------------------------------
# Monitoring & Metrics Schemas
# -------------------------------------------------------------

class WorkflowMonitoringStats(BaseModel):
    total_workflows: int
    active_workflows: int
    total_executions: int
    successful_executions: int
    failed_executions: int
    pending_approvals: int
    average_duration_ms: float
    retry_count: int
    success_rate_percent: float
    recent_executions: List[WorkflowExecutionRead]
