import json
import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from sqlalchemy import select, func

from app.db.session import get_db
from app.api.deps import get_current_user
from app.models.entities import User
from app.models.workflow import WorkflowExecution, RecruiterTask
from app.models.enums import (
    UserRole,
    WorkflowTriggerType,
    WorkflowExecutionStatus,
    WorkflowApprovalStatus,
    RecruiterTaskStatus,
    RecruiterTaskPriority,
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowRead,
    WorkflowVersionRead,
    WorkflowListResponse,
    WorkflowExecutionRead,
    WorkflowExecutionStepRead,
    WorkflowExecutionListResponse,
    WorkflowManualTriggerRequest,
    WorkflowApprovalRead,
    WorkflowApprovalDecision,
    WorkflowApprovalListResponse,
    RecruiterTaskCreate,
    RecruiterTaskUpdate,
    RecruiterTaskRead,
    RecruiterTaskListResponse,
    WorkflowMonitoringStats,
)
from app.services.workflow_service import WorkflowService

router = APIRouter()


def _format_workflow_read(wf) -> WorkflowRead:
    current_ver = None
    if wf.versions:
        latest = wf.versions[0]
        try:
            def_json = json.loads(latest.definition_json)
        except Exception:
            def_json = {}
        current_ver = WorkflowVersionRead(
            id=latest.id,
            workflow_id=latest.workflow_id,
            version_number=latest.version_number,
            definition=def_json,
            change_summary=latest.change_summary,
            created_by_user_id=latest.created_by_user_id,
            created_at=latest.created_at,
        )

    return WorkflowRead(
        id=wf.id,
        agency_id=wf.agency_id,
        name=wf.name,
        description=wf.description,
        trigger_type=wf.trigger_type,
        is_active=wf.is_active,
        created_by_user_id=wf.created_by_user_id,
        created_at=wf.created_at,
        updated_at=wf.updated_at,
        current_version=current_ver,
        execution_count=len(wf.executions) if wf.executions else 0,
    )


def _format_execution_read(e) -> WorkflowExecutionRead:
    steps_read = []
    for s in (e.steps or []):
        try:
            cfg = json.loads(s.action_config) if s.action_config else {}
        except Exception:
            cfg = {}
        try:
            out_p = json.loads(s.output_payload) if s.output_payload else None
        except Exception:
            out_p = None
        steps_read.append(
            WorkflowExecutionStepRead(
                id=s.id,
                execution_id=s.execution_id,
                step_index=s.step_index,
                action_type=s.action_type,
                status=s.status,
                action_config=cfg,
                output_payload=out_p,
                error_message=s.error_message,
                started_at=s.started_at,
                completed_at=s.completed_at,
                created_at=s.created_at,
            )
        )

    return WorkflowExecutionRead(
        id=e.id,
        agency_id=e.agency_id,
        workflow_id=e.workflow_id,
        workflow_name=e.workflow.name if e.workflow else None,
        workflow_version_id=e.workflow_version_id,
        trigger_event=e.trigger_event,
        trigger_entity_type=e.trigger_entity_type,
        trigger_entity_id=e.trigger_entity_id,
        status=e.status,
        idempotency_key=e.idempotency_key,
        retry_count=e.retry_count,
        error_message=e.error_message,
        started_at=e.started_at,
        completed_at=e.completed_at,
        created_at=e.created_at,
        steps=steps_read,
    )


def _format_task_read(t) -> RecruiterTaskRead:
    return RecruiterTaskRead(
        id=t.id,
        agency_id=t.agency_id,
        title=t.title,
        description=t.description,
        priority=t.priority,
        status=t.status,
        assigned_to_user_id=t.assigned_to_user_id,
        assigned_to_name=t.assigned_to.full_name if t.assigned_to else None,
        created_by_user_id=t.created_by_user_id,
        candidate_id=t.candidate_id,
        candidate_name=t.candidate.full_name if t.candidate else None,
        job_id=t.job_id,
        job_title=t.job.title if t.job else None,
        application_id=t.application_id,
        interview_id=t.interview_id,
        due_date=t.due_date,
        completed_at=t.completed_at,
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


# -------------------------------------------------------------
# 1. Monitoring & Stats (Static Sub-route)
# -------------------------------------------------------------

@router.get("/monitoring/stats", response_model=WorkflowMonitoringStats)
def get_monitoring_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    return service.get_monitoring_stats()


# -------------------------------------------------------------
# 2. Workflow Executions (Static Sub-routes)
# -------------------------------------------------------------

@router.get("/executions", response_model=WorkflowExecutionListResponse)
def list_executions(
    workflow_id: Optional[uuid.UUID] = None,
    status: Optional[WorkflowExecutionStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    query = select(WorkflowExecution).where(WorkflowExecution.agency_id == current_user.agency_id)

    if workflow_id:
        query = query.where(WorkflowExecution.workflow_id == workflow_id)
    if status:
        query = query.where(WorkflowExecution.status == status)

    count_q = select(func.count()).select_from(query.subquery())
    total = db.scalar(count_q) or 0

    items = db.scalars(
        query.order_by(WorkflowExecution.created_at.desc()).offset(skip).limit(limit)
    ).all()

    return WorkflowExecutionListResponse(
        items=[_format_execution_read(e) for e in items],
        total=total,
    )


@router.get("/executions/{id}", response_model=WorkflowExecutionRead)
def get_execution(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    execution = db.scalars(
        select(WorkflowExecution).where(
            WorkflowExecution.id == id,
            WorkflowExecution.agency_id == current_user.agency_id,
        )
    ).first()

    if not execution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workflow execution not found.",
        )

    return _format_execution_read(execution)


# -------------------------------------------------------------
# 3. Human Approvals (Static Sub-routes)
# -------------------------------------------------------------

@router.get("/approvals", response_model=WorkflowApprovalListResponse)
def list_approvals(
    status: Optional[WorkflowApprovalStatus] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    items, total = service.list_approvals(status_filter=status, skip=skip, limit=limit)

    read_items = []
    for a in items:
        try:
            payload = json.loads(a.action_payload) if a.action_payload else None
        except Exception:
            payload = None

        read_items.append(
            WorkflowApprovalRead(
                id=a.id,
                agency_id=a.agency_id,
                execution_id=a.execution_id,
                step_id=a.step_id,
                title=a.title,
                description=a.description,
                status=a.status,
                requested_action=a.requested_action,
                action_payload=payload,
                assigned_role=a.assigned_role,
                assigned_user_id=a.assigned_user_id,
                approved_by_user_id=a.approved_by_user_id,
                rejection_reason=a.rejection_reason,
                expires_at=a.expires_at,
                decided_at=a.decided_at,
                created_at=a.created_at,
                workflow_name=a.execution.workflow.name if (a.execution and a.execution.workflow) else None,
            )
        )

    return WorkflowApprovalListResponse(items=read_items, total=total)


@router.post("/approvals/{id}/decision", response_model=WorkflowApprovalRead)
def decide_approval(
    id: uuid.UUID,
    data: WorkflowApprovalDecision,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    appr = service.decide_approval(id, current_user, data)

    try:
        payload = json.loads(appr.action_payload) if appr.action_payload else None
    except Exception:
        payload = None

    return WorkflowApprovalRead(
        id=appr.id,
        agency_id=appr.agency_id,
        execution_id=appr.execution_id,
        step_id=appr.step_id,
        title=appr.title,
        description=appr.description,
        status=appr.status,
        requested_action=appr.requested_action,
        action_payload=payload,
        assigned_role=appr.assigned_role,
        assigned_user_id=appr.assigned_user_id,
        approved_by_user_id=appr.approved_by_user_id,
        rejection_reason=appr.rejection_reason,
        expires_at=appr.expires_at,
        decided_at=appr.decided_at,
        created_at=appr.created_at,
        workflow_name=appr.execution.workflow.name if (appr.execution and appr.execution.workflow) else None,
    )


# -------------------------------------------------------------
# 4. Recruiter Tasks (Static Sub-routes)
# -------------------------------------------------------------

@router.post("/tasks", response_model=RecruiterTaskRead, status_code=status.HTTP_201_CREATED)
def create_recruiter_task(
    data: RecruiterTaskCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    t = service.create_task(current_user, data)
    return _format_task_read(t)


@router.get("/tasks", response_model=RecruiterTaskListResponse)
def list_recruiter_tasks(
    status: Optional[RecruiterTaskStatus] = None,
    priority: Optional[RecruiterTaskPriority] = None,
    assigned_to_user_id: Optional[uuid.UUID] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    items, total = service.list_tasks(
        status_filter=status,
        priority_filter=priority,
        assigned_to_user_id=assigned_to_user_id,
        skip=skip,
        limit=limit,
    )
    return RecruiterTaskListResponse(
        items=[_format_task_read(t) for t in items],
        total=total,
    )


@router.get("/tasks/{id}", response_model=RecruiterTaskRead)
def get_recruiter_task(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    task = db.scalars(
        select(RecruiterTask).where(
            RecruiterTask.id == id,
            RecruiterTask.agency_id == current_user.agency_id,
        )
    ).first()

    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recruiter task not found.",
        )

    return _format_task_read(task)


@router.put("/tasks/{id}", response_model=RecruiterTaskRead)
def update_recruiter_task(
    id: uuid.UUID,
    data: RecruiterTaskUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    t = service.update_task(id, current_user, data)
    return _format_task_read(t)


# -------------------------------------------------------------
# 5. Core Workflow Rule Endpoints
# -------------------------------------------------------------

@router.post("", response_model=WorkflowRead, status_code=status.HTTP_201_CREATED)
def create_workflow(
    data: WorkflowCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agency owners and administrators can configure recruitment workflows.",
        )

    service = WorkflowService(db, current_user.agency_id)
    wf = service.create_workflow(current_user, data)
    return _format_workflow_read(wf)


@router.get("", response_model=WorkflowListResponse)
def list_workflows(
    is_active: Optional[bool] = None,
    trigger_type: Optional[WorkflowTriggerType] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    items, total = service.list_workflows(
        is_active=is_active,
        trigger_type=trigger_type,
        skip=skip,
        limit=limit,
    )
    return WorkflowListResponse(
        items=[_format_workflow_read(w) for w in items],
        total=total,
    )


@router.get("/{id}", response_model=WorkflowRead)
def get_workflow(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    wf = service.get_workflow(id)
    return _format_workflow_read(wf)


@router.put("/{id}", response_model=WorkflowRead)
def update_workflow(
    id: uuid.UUID,
    data: WorkflowUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agency owners and administrators can modify recruitment workflows.",
        )

    service = WorkflowService(db, current_user.agency_id)
    wf = service.update_workflow(id, current_user, data)
    return _format_workflow_read(wf)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_workflow(
    id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only agency owners and administrators can delete recruitment workflows.",
        )

    service = WorkflowService(db, current_user.agency_id)
    service.delete_workflow(id, current_user)
    return None


@router.post("/{id}/trigger", response_model=List[WorkflowExecutionRead])
def manual_trigger_workflow(
    id: uuid.UUID,
    data: WorkflowManualTriggerRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    service = WorkflowService(db, current_user.agency_id)
    wf = service.get_workflow(id)
    executions = service.trigger_event(
        trigger_type=wf.trigger_type,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        current_user=current_user,
    )
    return [_format_execution_read(e) for e in executions]
