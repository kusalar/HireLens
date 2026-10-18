import uuid
import json
import pytest
from datetime import datetime, timedelta, timezone
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.enums import (
    UserRole,
    WorkflowTriggerType,
    WorkflowActionType,
    WorkflowExecutionStatus,
    WorkflowStepStatus,
    WorkflowApprovalStatus,
    RecruiterTaskStatus,
    RecruiterTaskPriority,
    NotificationDeliveryStatus,
)
from app.models.workflow import (
    RecruitmentWorkflow,
    WorkflowVersion,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowApproval,
    RecruiterTask,
)
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.application import Application
from app.models.notification import NotificationOutbox
from app.services.condition_engine import (
    ConditionEngine,
    ConditionEvaluationError,
)
from app.services.workflow_service import WorkflowService


def create_agency_and_user(
    client: TestClient, agency_name: str, email: str
) -> tuple[str, str, str]:
    reg = client.post(
        "/api/v1/auth/register",
        json={
            "agency_name": agency_name,
            "full_name": f"{agency_name} Admin",
            "email": email,
            "password": "SecurePassword123!",
        },
    )
    assert reg.status_code == 201, reg.text
    token = reg.json()["tokens"]["access_token"]
    user_id = reg.json()["user"]["id"]
    agency_id = reg.json()["user"]["agency_id"]
    return token, user_id, agency_id


def create_recruiter_user(
    client: TestClient, owner_token: str, email: str, name: str = "Recruiter User"
) -> tuple[str, str]:
    invite_res = client.post(
        "/api/v1/agency/members/invite",
        headers={"Authorization": f"Bearer {owner_token}"},
        json={"email": email, "role": "RECRUITER"},
    )
    assert invite_res.status_code == 201, invite_res.text
    invite_token = invite_res.json()["token"]

    accept_res = client.post(
        "/api/v1/agency/members/accept-invite",
        json={
            "token": invite_token,
            "full_name": name,
            "password": "RecruiterPassword123!",
        },
    )
    assert accept_res.status_code == 201, accept_res.text

    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "RecruiterPassword123!"},
    )
    assert login_res.status_code == 200, login_res.text
    recruiter_token = login_res.json()["tokens"]["access_token"]
    recruiter_id = login_res.json()["user"]["id"]
    return recruiter_token, recruiter_id


# -------------------------------------------------------------
# 1. Condition Engine Unit Tests
# -------------------------------------------------------------

def test_condition_engine_operators():
    context = {
        "match_score": 88.5,
        "candidate": {
            "full_name": "Arjun Sharma",
            "skills": ["Python", "FastAPI", "PostgreSQL"],
            "total_experience_months": 48,
        },
        "application": {
            "stage": "SHORTLISTED",
            "source": "LINKEDIN",
        },
    }

    # A. Numeric greater than or equal
    tree1 = {
        "field": "match_score",
        "operator": "GREATER_THAN_OR_EQUAL",
        "value": 80.0,
    }
    matched, _ = ConditionEngine.evaluate(tree1, context)
    assert matched is True

    tree2 = {
        "field": "match_score",
        "operator": "GREATER_THAN",
        "value": 95.0,
    }
    matched, _ = ConditionEngine.evaluate(tree2, context)
    assert matched is False

    # B. List contains case-insensitive
    tree3 = {
        "field": "candidate.skills",
        "operator": "CONTAINS",
        "value": "python",
    }
    matched, _ = ConditionEngine.evaluate(tree3, context)
    assert matched is True

    tree4 = {
        "field": "candidate.skills",
        "operator": "CONTAINS",
        "value": "Kubernetes",
    }
    matched, _ = ConditionEngine.evaluate(tree4, context)
    assert matched is False

    # C. String equality
    tree5 = {
        "field": "application.stage",
        "operator": "EQUALS",
        "value": "shortlisted",
    }
    matched, _ = ConditionEngine.evaluate(tree5, context)
    assert matched is True

    # D. Missing field handling
    tree6 = {
        "field": "nonexistent.field",
        "operator": "GREATER_THAN",
        "value": 10,
    }
    matched, _ = ConditionEngine.evaluate(tree6, context)
    assert matched is False

    # E. EXISTS operator
    tree7 = {"field": "candidate.full_name", "operator": "EXISTS"}
    matched, _ = ConditionEngine.evaluate(tree7, context)
    assert matched is True

    tree8 = {"field": "candidate.missing_note", "operator": "NOT_EXISTS"}
    matched, _ = ConditionEngine.evaluate(tree8, context)
    assert matched is True


def test_condition_engine_nested_groups_and_complexity():
    context = {
        "match_score": 85.0,
        "candidate": {"skills": ["Python", "React"]},
        "application": {"stage": "INTERVIEW"},
    }

    # Nested AND with child OR
    nested_tree = {
        "logical_operator": "AND",
        "conditions": [
            {
                "field": "match_score",
                "operator": "GREATER_THAN_OR_EQUAL",
                "value": 75.0,
            },
            {
                "logical_operator": "OR",
                "conditions": [
                    {"field": "candidate.skills", "operator": "CONTAINS", "value": "Go"},
                    {"field": "candidate.skills", "operator": "CONTAINS", "value": "Python"},
                ],
            },
        ],
    }
    matched, explain = ConditionEngine.evaluate(nested_tree, context)
    assert matched is True
    assert explain["logical_operator"] == "AND"

    # Complexity limit: deeply nested condition exceeding MAX_EVALUATION_DEPTH (5)
    deep_tree = {"field": "match_score", "operator": "GREATER_THAN", "value": 0}
    for _ in range(7):
        deep_tree = {"logical_operator": "AND", "conditions": [deep_tree]}

    with pytest.raises(ConditionEvaluationError):
        ConditionEngine.evaluate(deep_tree, context)


# -------------------------------------------------------------
# 2. Workflow CRUD and Versioning Tests
# -------------------------------------------------------------

def test_workflow_crud_and_versioning(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Workflow Agency", "wf_owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create workflow
    payload = {
        "name": "High Match Auto-Communication",
        "description": "Send acknowledgment to high-scoring candidates",
        "trigger_type": "APPLICATION_SUBMITTED",
        "is_active": True,
        "definition": {
            "trigger_config": {},
            "conditions": {
                "logical_operator": "AND",
                "conditions": [
                    {"field": "match_score", "operator": "GREATER_THAN_OR_EQUAL", "value": 70.0}
                ],
            },
            "actions": [
                {
                    "action_type": "SEND_CANDIDATE_COMMUNICATION",
                    "step_index": 0,
                    "email_subject": "Application Update for {{candidate_name}}",
                    "email_body_template": "Hello {{candidate_name}}, we received your application.",
                }
            ],
        },
        "change_summary": "Initial draft",
    }
    create_res = client.post("/api/v1/workflows", headers=headers, json=payload)
    assert create_res.status_code == 201, create_res.text
    wf_data = create_res.json()
    wf_id = wf_data["id"]
    assert wf_data["name"] == "High Match Auto-Communication"
    assert wf_data["current_version"]["version_number"] == 1

    # 2. Update workflow definition (creates version 2)
    update_payload = {
        "name": "High Match Auto-Communication v2",
        "definition": {
            "trigger_config": {},
            "conditions": {
                "logical_operator": "AND",
                "conditions": [
                    {"field": "match_score", "operator": "GREATER_THAN_OR_EQUAL", "value": 80.0}
                ],
            },
            "actions": [
                {
                    "action_type": "NOTIFY_RECRUITERS",
                    "step_index": 0,
                    "notification_title": "Top Candidate Applied",
                }
            ],
        },
        "change_summary": "Raised threshold to 80 and added recruiter alert",
    }
    update_res = client.put(f"/api/v1/workflows/{wf_id}", headers=headers, json=update_payload)
    assert update_res.status_code == 200, update_res.text
    updated_data = update_res.json()
    assert updated_data["name"] == "High Match Auto-Communication v2"
    assert updated_data["current_version"]["version_number"] == 2

    # 3. List workflows
    list_res = client.get("/api/v1/workflows", headers=headers)
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1

    # 4. Delete workflow
    del_res = client.delete(f"/api/v1/workflows/{wf_id}", headers=headers)
    assert del_res.status_code == 204

    # Confirm 404 on get
    get_res = client.get(f"/api/v1/workflows/{wf_id}", headers=headers)
    assert get_res.status_code == 404


# -------------------------------------------------------------
# 3. RBAC & Multi-Tenant Isolation Tests
# -------------------------------------------------------------

def test_workflow_rbac_and_tenant_isolation(client: TestClient):
    # Agency 1 Owner & Recruiter
    a1_owner_token, _, a1_id = create_agency_and_user(client, "Agency One", "a1_owner@example.com")
    a1_rec_token, _ = create_recruiter_user(client, a1_owner_token, "a1_rec@example.com")

    # Agency 2 Owner
    a2_owner_token, _, a2_id = create_agency_and_user(client, "Agency Two", "a2_owner@example.com")

    # 1. Recruiter cannot create workflow (403 Forbidden)
    payload = {
        "name": "Recruiter Attempt",
        "trigger_type": "APPLICATION_SUBMITTED",
        "definition": {"actions": []},
    }
    rec_create = client.post(
        "/api/v1/workflows",
        headers={"Authorization": f"Bearer {a1_rec_token}"},
        json=payload,
    )
    assert rec_create.status_code == 403

    # 2. Owner creates workflow in Agency 1
    owner_create = client.post(
        "/api/v1/workflows",
        headers={"Authorization": f"Bearer {a1_owner_token}"},
        json=payload,
    )
    assert owner_create.status_code == 201
    a1_wf_id = owner_create.json()["id"]

    # 3. Recruiter CAN list workflows (read-only)
    rec_list = client.get(
        "/api/v1/workflows",
        headers={"Authorization": f"Bearer {a1_rec_token}"},
    )
    assert rec_list.status_code == 200

    # 4. Cross-tenant access: Agency 2 cannot view or edit Agency 1's workflow (404 Not Found)
    a2_get = client.get(
        f"/api/v1/workflows/{a1_wf_id}",
        headers={"Authorization": f"Bearer {a2_owner_token}"},
    )
    assert a2_get.status_code == 404

    a2_put = client.put(
        f"/api/v1/workflows/{a1_wf_id}",
        headers={"Authorization": f"Bearer {a2_owner_token}"},
        json={"name": "Hacked Name"},
    )
    assert a2_put.status_code == 404


# -------------------------------------------------------------
# 4. Action Engine & Outbox Execution Tests
# -------------------------------------------------------------

def test_workflow_action_execution_notification_outbox(client: TestClient, db_session: Session):
    token, _, agency_id_str = create_agency_and_user(client, "Action Agency", "action_owner@example.com")
    agency_id = uuid.UUID(agency_id_str)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a candidate
    cand_res = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={
            "full_name": "Priya Patel",
            "email": "priya.patel@example.com",
            "total_experience_months": 36,
        },
    )
    assert cand_res.status_code == 201
    candidate_id = cand_res.json()["id"]

    # 2. Create workflow triggered on CANDIDATE_CREATED with action SEND_CANDIDATE_COMMUNICATION
    wf_payload = {
        "name": "Welcome New Candidate",
        "trigger_type": "CANDIDATE_CREATED",
        "is_active": True,
        "definition": {
            "trigger_config": {},
            "conditions": None,  # no conditions -> always run
            "actions": [
                {
                    "action_type": "SEND_CANDIDATE_COMMUNICATION",
                    "step_index": 0,
                    "email_subject": "Welcome to HireLens {{candidate_name}}",
                    "email_body_template": "Hi {{candidate_name}}, your profile was created successfully.",
                }
            ],
        },
    }
    wf_res = client.post("/api/v1/workflows", headers=headers, json=wf_payload)
    assert wf_res.status_code == 201

    # 3. Trigger event manually via service
    service = WorkflowService(db_session, agency_id)
    executions = service.trigger_event(
        trigger_type=WorkflowTriggerType.CANDIDATE_CREATED,
        entity_type="candidate",
        entity_id=uuid.UUID(candidate_id),
    )
    assert len(executions) == 1
    exec_id = executions[0].id

    # 4. Verify execution completed
    db_exec = db_session.scalars(select(WorkflowExecution).where(WorkflowExecution.id == exec_id)).first()
    assert db_exec.status == WorkflowExecutionStatus.COMPLETED

    # 5. Verify NotificationOutbox record was created
    outbox_item = db_session.scalars(
        select(NotificationOutbox).where(
            NotificationOutbox.agency_id == agency_id,
            NotificationOutbox.recipient_email == "priya.patel@example.com",
        )
    ).first()
    assert outbox_item is not None
    assert "Welcome to HireLens Priya Patel" in outbox_item.subject
    assert "Priya Patel" in outbox_item.body_text
    assert outbox_item.status == NotificationDeliveryStatus.PENDING


def test_workflow_action_recruiter_task_creation(client: TestClient, db_session: Session):
    token, _, agency_id_str = create_agency_and_user(client, "Task Agency", "task_owner@example.com")
    agency_id = uuid.UUID(agency_id_str)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create Job and Candidate
    job_res = client.post(
        "/api/v1/jobs",
        headers=headers,
        json={
            "title": "Backend Lead",
            "department": "Engineering",
            "work_mode": "HYBRID",
            "employment_type": "FULL_TIME",
            "minimum_experience": 5,
        },
    )
    job_id = job_res.json()["id"]

    cand_res = client.post(
        "/api/v1/candidates",
        headers=headers,
        json={"full_name": "Rohan Verma", "email": "rohan@example.com", "total_experience_months": 60},
    )
    cand_id = cand_res.json()["id"]

    # 2. Create workflow that creates a Recruiter Task
    wf_payload = {
        "name": "Screening Task Workflow",
        "trigger_type": "APPLICATION_SUBMITTED",
        "is_active": True,
        "definition": {
            "actions": [
                {
                    "action_type": "CREATE_RECRUITER_TASK",
                    "step_index": 0,
                    "task_title": "Conduct Phone Screening",
                    "task_description": "Review candidate portfolio and schedule initial call",
                    "task_priority": "HIGH",
                    "task_due_days": 3,
                }
            ],
        },
    }
    wf_res = client.post("/api/v1/workflows", headers=headers, json=wf_payload)
    assert wf_res.status_code == 201

    # 3. Trigger event
    service = WorkflowService(db_session, agency_id)
    executions = service.trigger_event(
        trigger_type=WorkflowTriggerType.APPLICATION_SUBMITTED,
        entity_type="candidate",
        entity_id=uuid.UUID(cand_id),
    )
    assert len(executions) == 1

    # 4. Verify RecruiterTask was created in database
    task = db_session.scalars(
        select(RecruiterTask).where(
            RecruiterTask.agency_id == agency_id,
            RecruiterTask.candidate_id == uuid.UUID(cand_id),
        )
    ).first()
    assert task is not None
    assert task.title == "Conduct Phone Screening"
    assert task.priority == RecruiterTaskPriority.HIGH
    assert task.status == RecruiterTaskStatus.PENDING


# -------------------------------------------------------------
# 5. Idempotency & Deduplication Test
# -------------------------------------------------------------

def test_workflow_idempotency_prevents_duplicate_runs(client: TestClient, db_session: Session):
    token, _, agency_id_str = create_agency_and_user(client, "Idemp Agency", "idemp_owner@example.com")
    agency_id = uuid.UUID(agency_id_str)
    headers = {"Authorization": f"Bearer {token}"}

    # Create workflow
    wf_payload = {
        "name": "Idempotent Flow",
        "trigger_type": "CANDIDATE_CREATED",
        "is_active": True,
        "definition": {"actions": []},
    }
    client.post("/api/v1/workflows", headers=headers, json=wf_payload)

    entity_id = uuid.uuid4()
    service = WorkflowService(db_session, agency_id)

    # First trigger -> creates execution
    runs_1 = service.trigger_event(
        trigger_type=WorkflowTriggerType.CANDIDATE_CREATED,
        entity_type="candidate",
        entity_id=entity_id,
    )
    assert len(runs_1) == 1

    # Second trigger with same entity in same time bucket -> skipped
    runs_2 = service.trigger_event(
        trigger_type=WorkflowTriggerType.CANDIDATE_CREATED,
        entity_type="candidate",
        entity_id=entity_id,
    )
    assert len(runs_2) == 0


# -------------------------------------------------------------
# 6. Human Approval & Review Queue Lifecycle Tests
# -------------------------------------------------------------

def test_human_approval_lifecycle_approve_and_reject(client: TestClient, db_session: Session):
    token, _, agency_id_str = create_agency_and_user(client, "Approval Agency", "approval_owner@example.com")
    agency_id = uuid.UUID(agency_id_str)
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a workflow with requires_approval: True
    wf_payload = {
        "name": "Offer Letter Preparation Flow",
        "trigger_type": "INTERVIEW_COMPLETED",
        "is_active": True,
        "definition": {
            "actions": [
                {
                    "action_type": "SEND_CANDIDATE_COMMUNICATION",
                    "step_index": 0,
                    "description": "Send candidate provisional offer email",
                    "requires_approval": True,
                    "approval_role": "AGENCY_ADMIN",
                    "email_subject": "Provisional Offer",
                    "email_body_template": "Congratulations!",
                }
            ],
        },
    }
    client.post("/api/v1/workflows", headers=headers, json=wf_payload)

    # 2. Trigger workflow
    dummy_interview_id = uuid.uuid4()
    service = WorkflowService(db_session, agency_id)
    runs = service.trigger_event(
        trigger_type=WorkflowTriggerType.INTERVIEW_COMPLETED,
        entity_type="interview",
        entity_id=dummy_interview_id,
    )
    assert len(runs) == 1
    execution = runs[0]

    # Verify execution paused in WAITING_FOR_APPROVAL
    db_session.refresh(execution)
    assert execution.status == WorkflowExecutionStatus.WAITING_FOR_APPROVAL

    # 3. Verify approval queue has 1 pending item
    appr_list_res = client.get("/api/v1/workflows/approvals?status=PENDING", headers=headers)
    assert appr_list_res.status_code == 200, appr_list_res.text
    approvals = appr_list_res.json()["items"]
    assert len(approvals) == 1
    approval_id = approvals[0]["id"]
    assert approvals[0]["status"] == "PENDING"

    # 4. Reject without reason fails validation (HTTP 422)
    bad_reject = client.post(
        f"/api/v1/workflows/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "REJECT", "rejection_reason": ""},
    )
    assert bad_reject.status_code == 422

    # 5. Approve decision
    approve_res = client.post(
        f"/api/v1/workflows/approvals/{approval_id}/decision",
        headers=headers,
        json={"decision": "APPROVE"},
    )
    assert approve_res.status_code == 200
    assert approve_res.json()["status"] == "APPROVED"

    # 6. Verify execution completed
    db_session.refresh(execution)
    assert execution.status == WorkflowExecutionStatus.COMPLETED


# -------------------------------------------------------------
# 7. Recruiter Tasks Management & Monitoring Tests
# -------------------------------------------------------------

def test_recruiter_task_endpoints_and_monitoring(client: TestClient):
    token, _, _ = create_agency_and_user(client, "Metrics Agency", "metrics_owner@example.com")
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a task manually
    task_res = client.post(
        "/api/v1/workflows/tasks",
        headers=headers,
        json={
            "title": "Verify Education Credentials",
            "description": "Contact university registrar for degree verification",
            "priority": "HIGH",
        },
    )
    assert task_res.status_code == 201
    task_id = task_res.json()["id"]
    assert task_res.json()["status"] == "PENDING"

    # 2. Update task to COMPLETED
    update_res = client.put(
        f"/api/v1/workflows/tasks/{task_id}",
        headers=headers,
        json={"status": "COMPLETED"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "COMPLETED"
    assert update_res.json()["completed_at"] is not None

    # 3. Check Monitoring Stats
    stats_res = client.get("/api/v1/workflows/monitoring/stats", headers=headers)
    assert stats_res.status_code == 200
    stats = stats_res.json()
    assert "total_workflows" in stats
    assert "total_executions" in stats
    assert "success_rate_percent" in stats
    assert isinstance(stats["recent_executions"], list)


# -------------------------------------------------------------
# 8. Prohibited Autonomous Actions Verification
# -------------------------------------------------------------

def test_prohibited_autonomous_actions_boundary():
    """
    Verify that WorkflowActionType strictly excludes autonomous hiring decisions,
    rejections, or stage mutations.
    """
    valid_actions = {a.value for a in WorkflowActionType}
    prohibited = {
        "HIRE_CANDIDATE",
        "REJECT_CANDIDATE",
        "SHORTLIST_CANDIDATE",
        "STAGE_CHANGE",
        "APPLICATION_STATUS_CHANGE",
    }
    overlap = valid_actions.intersection(prohibited)
    assert not overlap, f"Prohibited actions found in WorkflowActionType: {overlap}"
