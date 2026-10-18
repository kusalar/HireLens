import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status, Request
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.models.enums import (
    UserRole,
    AuditEventCategory,
    AuditSeverity,
    PrivacyRequestStatus,
    PrivacyRequestType,
)
from app.schemas.governance import (
    UserSessionRead,
    RevokeSessionRequest,
    SecurityAuditEventListResponse,
    CandidateConsentRecordCreate,
    CandidateConsentRecordRead,
    CandidatePrivacyRequestCreate,
    CandidatePrivacyRequestUpdate,
    CandidatePrivacyRequestRead,
    AIGovernancePolicyUpdate,
    AIGovernancePolicyRead,
    AIUsageMetricsResponse,
    DataRetentionPolicyUpdate,
    DataRetentionPolicyRead,
    RetentionDryRunPreview,
    RetentionExecutionLogRead,
    GovernanceOverviewResponse,
)
from app.services.governance_service import GovernanceService

router = APIRouter()


def require_owner_or_admin(user: User):
    if user.role not in [UserRole.OWNER, UserRole.ADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires OWNER or ADMIN role.",
        )


def require_recruiter_or_above(user: User):
    if user.role not in [UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation requires at least RECRUITER permissions.",
        )


# =============================================================================
# 1. Overview
# =============================================================================
@router.get("/overview", response_model=GovernanceOverviewResponse)
def get_governance_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get executive security, compliance, and governance summary.
    """
    service = GovernanceService(db, current_user.agency_id)
    return service.get_overview()


# =============================================================================
# 2. Security Audit Events
# =============================================================================
@router.get("/audit-events", response_model=SecurityAuditEventListResponse)
def list_security_audit_events(
    category: Optional[AuditEventCategory] = None,
    severity: Optional[AuditSeverity] = None,
    actor_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Unified security audit event center. Ordinary users cannot modify or purge audit records.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.list_audit_events(
        category=category,
        severity=severity,
        actor_id=actor_id,
        skip=skip,
        limit=limit,
    )


# =============================================================================
# 3. Session & Access Management
# =============================================================================
@router.get("/sessions", response_model=List[UserSessionRead])
def list_user_sessions(
    user_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List active user sessions. Ordinary users see their own; OWNER/ADMIN see agency-wide sessions.
    """
    service = GovernanceService(db, current_user.agency_id)
    return service.list_user_sessions(current_user=current_user, target_user_id=user_id)


@router.delete("/sessions/{session_id}", response_model=UserSessionRead)
def revoke_user_session(
    session_id: uuid.UUID,
    data: Optional[RevokeSessionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Revoke a specific authentication session.
    """
    reason = data.reason if data else "Revoked by user"
    service = GovernanceService(db, current_user.agency_id)
    return service.revoke_session(session_id=session_id, current_user=current_user, reason=reason)


@router.post("/sessions/global-logout")
def global_logout(
    target_user_id: Optional[uuid.UUID] = None,
    data: Optional[RevokeSessionRequest] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Perform global logout, invalidating all active sessions and refresh tokens for user.
    """
    reason = data.reason if data else "Global logout requested"
    service = GovernanceService(db, current_user.agency_id)
    return service.global_logout(current_user=current_user, target_user_id=target_user_id, reason=reason)


# =============================================================================
# 4. Candidate Privacy & Consent Management
# =============================================================================
@router.get("/consent", response_model=List[CandidateConsentRecordRead])
def list_consent_records(
    candidate_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve candidate consent records and withdrawal histories.
    """
    service = GovernanceService(db, current_user.agency_id)
    return service.list_consent_records(candidate_id=candidate_id)


@router.post("/consent", response_model=CandidateConsentRecordRead)
def record_candidate_consent(
    data: CandidateConsentRecordCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Record candidate consent grant with version and purpose tracking.
    """
    require_recruiter_or_above(current_user)
    ip_address = request.client.host if request.client else None
    service = GovernanceService(db, current_user.agency_id)
    return service.record_candidate_consent(data=data, ip_address=ip_address)


@router.post("/consent/{consent_id}/withdraw", response_model=CandidateConsentRecordRead)
def withdraw_candidate_consent(
    consent_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Withdraw previously granted consent record.
    """
    require_recruiter_or_above(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.withdraw_candidate_consent(consent_id=consent_id)


# =============================================================================
# 5. Candidate Privacy Requests & Legal Holds
# =============================================================================
@router.get("/privacy-requests", response_model=List[CandidatePrivacyRequestRead])
def list_privacy_requests(
    status: Optional[PrivacyRequestStatus] = None,
    request_type: Optional[PrivacyRequestType] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List data subject access, correction, and deletion requests.
    """
    require_recruiter_or_above(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.list_privacy_requests(status_filter=status, request_type=request_type)


@router.post("/privacy-requests", response_model=CandidatePrivacyRequestRead)
def create_privacy_request(
    data: CandidatePrivacyRequestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Log a candidate privacy data subject request.
    """
    require_recruiter_or_above(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.create_privacy_request(data=data)


@router.patch("/privacy-requests/{request_id}", response_model=CandidatePrivacyRequestRead)
def update_privacy_request(
    request_id: uuid.UUID,
    data: CandidatePrivacyRequestUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update request status, apply/remove legal hold, or execute compliant anonymization.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.update_privacy_request(
        request_id=request_id,
        data=data,
        current_user=current_user,
    )


# =============================================================================
# 6. AI Governance & Policies
# =============================================================================
@router.get("/ai-policy", response_model=AIGovernancePolicyRead)
def get_ai_governance_policy(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get agency AI provider governance policy and token constraints.
    """
    service = GovernanceService(db, current_user.agency_id)
    policy = service.get_or_create_ai_policy()
    return service._to_ai_policy_read(policy)


@router.put("/ai-policy", response_model=AIGovernancePolicyRead)
def update_ai_governance_policy(
    data: AIGovernancePolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Configure allowed AI providers, token limits, and safety filters. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.update_ai_policy(data=data, current_user=current_user)


@router.get("/ai-usage", response_model=AIUsageMetricsResponse)
def get_ai_usage_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    View monthly AI token usage, provider breakdown, and fallback counts.
    """
    service = GovernanceService(db, current_user.agency_id)
    return service.get_ai_usage_metrics()


# =============================================================================
# 7. Data Retention & Lifecycle Governance
# =============================================================================
@router.get("/retention-policies", response_model=List[DataRetentionPolicyRead])
def list_data_retention_policies(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List configured retention policies across all 6 data categories.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.list_retention_policies()


@router.put("/retention-policies/{policy_id}", response_model=DataRetentionPolicyRead)
def update_data_retention_policy(
    policy_id: uuid.UUID,
    data: DataRetentionPolicyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update retention policy duration, action type, and enablement. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.update_retention_policy(policy_id=policy_id, data=data, current_user=current_user)


@router.post("/retention-policies/{policy_id}/preview", response_model=RetentionDryRunPreview)
def preview_data_retention_policy(
    policy_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Safe dry-run preview: scans eligible records and legal-hold exemptions without modifying data.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.preview_retention_policy(policy_id=policy_id)


@router.post("/retention-policies/{policy_id}/execute", response_model=RetentionExecutionLogRead)
def execute_data_retention_policy(
    policy_id: uuid.UUID,
    dry_run: bool = Query(False),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Execute data retention policy lifecycle action with legal-hold safeguards. OWNER/ADMIN only.
    """
    require_owner_or_admin(current_user)
    service = GovernanceService(db, current_user.agency_id)
    return service.execute_retention_policy(policy_id=policy_id, current_user=current_user, is_dry_run=dry_run)
