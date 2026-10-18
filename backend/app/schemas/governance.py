import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, ConfigDict

from app.models.enums import (
    AuditEventCategory,
    AuditSeverity,
    ConsentType,
    PrivacyRequestType,
    PrivacyRequestStatus,
    RetentionCategory,
    RetentionAction,
    RetentionExecutionType,
    RetentionStatus,
)


class UserSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    device_info: Optional[str] = None
    is_active: bool
    is_current: bool = False
    created_at: datetime
    last_activity_at: datetime
    revoked_at: Optional[datetime] = None
    revocation_reason: Optional[str] = None


class RevokeSessionRequest(BaseModel):
    reason: Optional[str] = "Revoked by user"


class SecurityAuditEventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    actor_user_id: Optional[uuid.UUID] = None
    actor_email: Optional[str] = None
    event_category: AuditEventCategory
    severity: AuditSeverity
    action: str
    resource_type: str
    resource_id: Optional[str] = None
    details: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime


class SecurityAuditEventListResponse(BaseModel):
    items: List[SecurityAuditEventRead]
    total: int
    skip: int
    limit: int


class CandidateConsentRecordCreate(BaseModel):
    candidate_id: uuid.UUID
    consent_type: ConsentType
    is_granted: bool = True
    policy_version: str = "v1.0"
    purpose: str
    channel: str = "APPLICATION_PORTAL"
    metadata: Optional[Dict[str, Any]] = None


class CandidateConsentRecordRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    candidate_id: uuid.UUID
    candidate_name: Optional[str] = None
    candidate_email: Optional[str] = None
    consent_type: ConsentType
    is_granted: bool
    policy_version: str
    purpose: str
    channel: str
    granted_at: datetime
    withdrawn_at: Optional[datetime] = None
    metadata: Optional[Dict[str, Any]] = None


class CandidatePrivacyRequestCreate(BaseModel):
    candidate_id: Optional[uuid.UUID] = None
    request_type: PrivacyRequestType
    requested_by_email: str
    request_details: Optional[str] = None


class CandidatePrivacyRequestUpdate(BaseModel):
    status: Optional[PrivacyRequestStatus] = None
    resolution_notes: Optional[str] = None
    has_legal_hold: Optional[bool] = None
    legal_hold_reason: Optional[str] = None


class CandidatePrivacyRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    candidate_id: Optional[uuid.UUID] = None
    candidate_name: Optional[str] = None
    request_type: PrivacyRequestType
    status: PrivacyRequestStatus
    requested_by_email: str
    request_details: Optional[str] = None
    resolution_notes: Optional[str] = None
    has_legal_hold: bool
    legal_hold_reason: Optional[str] = None
    handled_by_name: Optional[str] = None
    created_at: datetime
    resolved_at: Optional[datetime] = None


class AIGovernancePolicyUpdate(BaseModel):
    allowed_providers: Optional[List[str]] = None
    max_tokens_per_request: Optional[int] = None
    monthly_token_budget: Optional[int] = None
    require_pii_masking: Optional[bool] = None
    safety_filter_enabled: Optional[bool] = None


class AIGovernancePolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    allowed_providers: List[str]
    max_tokens_per_request: int
    monthly_token_budget: int
    require_pii_masking: bool
    safety_filter_enabled: bool
    updated_at: datetime


class AIUsageMetricsResponse(BaseModel):
    total_requests: int
    total_tokens: int
    estimated_cost_usd: float
    fallback_count: int
    safety_filter_triggers: int
    provider_breakdown: List[Dict[str, Any]]
    feature_breakdown: List[Dict[str, Any]]


class DataRetentionPolicyUpdate(BaseModel):
    retention_days: Optional[int] = None
    action_type: Optional[RetentionAction] = None
    is_enabled: Optional[bool] = None
    exempt_legal_holds: Optional[bool] = None


class DataRetentionPolicyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    data_category: RetentionCategory
    retention_days: int
    action_type: RetentionAction
    is_enabled: bool
    exempt_legal_holds: bool
    last_executed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime


class RetentionDryRunPreview(BaseModel):
    policy_id: uuid.UUID
    data_category: RetentionCategory
    action_type: RetentionAction
    retention_days: int
    cutoff_date: str
    records_scanned: int
    records_eligible: int
    records_exempted_legal_hold: int
    affected_sample_identifiers: List[str]


class RetentionExecutionLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agency_id: uuid.UUID
    policy_id: uuid.UUID
    data_category: Optional[str] = None
    execution_type: RetentionExecutionType
    records_scanned: int
    records_affected: int
    records_exempted: int
    status: RetentionStatus
    executed_by_name: Optional[str] = None
    execution_summary: Optional[Dict[str, Any]] = None
    created_at: datetime


class GovernanceOverviewResponse(BaseModel):
    active_sessions_count: int
    security_events_24h: int
    critical_security_alerts: int
    pending_privacy_requests: int
    active_legal_holds_count: int
    ai_token_usage_month: int
    ai_budget_utilization_percent: float
    active_retention_policies_count: int
    last_retention_run_at: Optional[str] = None
    timezone: str = "Asia/Kolkata"
