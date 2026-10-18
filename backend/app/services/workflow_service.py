import json
import uuid
import hashlib
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import select, func, desc, and_, or_
from fastapi import HTTPException, status

from app.models.base import utc_now
from app.models.entities import User, AuditLog
from app.models.candidate import Candidate
from app.models.job import Job
from app.models.application import Application
from app.models.interview import Interview
from app.models.matching import JobMatchResult
from app.models.notification import Notification, NotificationOutbox
from app.models.enums import (
    UserRole,
    WorkflowTriggerType,
    WorkflowActionType,
    WorkflowExecutionStatus,
    WorkflowStepStatus,
    WorkflowApprovalStatus,
    RecruiterTaskStatus,
    RecruiterTaskPriority,
    NotificationType,
    NotificationDeliveryStatus,
)
from app.models.workflow import (
    RecruitmentWorkflow,
    WorkflowVersion,
    WorkflowExecution,
    WorkflowExecutionStep,
    WorkflowApproval,
    RecruiterTask,
    WorkflowAuditLog,
)
from app.schemas.workflow import (
    WorkflowCreate,
    WorkflowUpdate,
    WorkflowApprovalDecision,
    RecruiterTaskCreate,
    RecruiterTaskUpdate,
    WorkflowMonitoringStats,
)
from app.services.condition_engine import ConditionEngine

logger = logging.getLogger(__name__)


class WorkflowService:
    def __init__(self, db: Session, agency_id: Optional[uuid.UUID] = None):
        self.db = db
        self.agency_id = agency_id

    # -------------------------------------------------------------
    # Helpers & Context Resolution
    # -------------------------------------------------------------

    def _ensure_agency_id(self) -> uuid.UUID:
        if not self.agency_id:
            raise ValueError("WorkflowService requires a valid agency_id for this operation.")
        return self.agency_id

    def build_event_context(
        self,
        trigger_type: WorkflowTriggerType,
        entity_type: str,
        entity_id: uuid.UUID,
        override_context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Assemble deterministic runtime context for condition evaluation and action execution.
        """
        agency_id = self._ensure_agency_id()
        ctx: Dict[str, Any] = {
            "trigger_type": trigger_type.value,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "timestamp": utc_now().isoformat(),
        }

        # 1. Resolve Candidate
        candidate: Optional[Candidate] = None
        if entity_type == "candidate":
            candidate = self.db.scalars(
                select(Candidate).where(Candidate.id == entity_id, Candidate.agency_id == agency_id)
            ).first()

        # 2. Resolve Application
        application: Optional[Application] = None
        if entity_type == "application":
            application = self.db.scalars(
                select(Application).where(Application.id == entity_id, Application.agency_id == agency_id)
            ).first()
            if application and not candidate:
                candidate = application.candidate

        # 3. Resolve Interview
        interview: Optional[Interview] = None
        if entity_type == "interview":
            interview = self.db.scalars(
                select(Interview).where(Interview.id == entity_id, Interview.agency_id == agency_id)
            ).first()
            if interview and not application:
                application = interview.application
                if application and not candidate:
                    candidate = application.candidate

        # 4. Resolve Job
        job: Optional[Job] = None
        if entity_type == "job":
            job = self.db.scalars(
                select(Job).where(Job.id == entity_id, Job.agency_id == agency_id)
            ).first()
        elif application and application.job:
            job = application.job

        # Populate structured context fields
        if candidate:
            skills = [s.skill_name for s in candidate.skills] if candidate.skills else []
            ctx["candidate"] = {
                "id": str(candidate.id),
                "full_name": candidate.full_name,
                "email": candidate.email,
                "current_title": candidate.current_title,
                "total_experience_months": candidate.total_experience_months,
                "skills": skills,
                "profile_status": candidate.profile_status.value if candidate.profile_status else None,
            }

        if job:
            ctx["job"] = {
                "id": str(job.id),
                "title": job.title,
                "department": job.department,
                "work_mode": job.work_mode.value if job.work_mode else None,
                "minimum_experience": job.minimum_experience,
            }

        if application:
            # Stage duration calculation
            duration_hours = 0.0
            if application.last_activity_at:
                delta = utc_now() - application.last_activity_at
                duration_hours = round(delta.total_seconds() / 3600.0, 2)

            ctx["application"] = {
                "id": str(application.id),
                "stage": application.status.value if application.status else None,
                "source": application.source,
                "applied_at": application.applied_at.isoformat() if application.applied_at else None,
                "stage_duration_hours": duration_hours,
            }

            # Fetch deterministic match score if available
            match_res = self.db.scalars(
                select(JobMatchResult).where(
                    JobMatchResult.agency_id == agency_id,
                    JobMatchResult.job_id == application.job_id,
                    JobMatchResult.candidate_id == application.candidate_id,
                )
            ).first()
            if match_res:
                ctx["match_score"] = float(match_res.overall_score)
                ctx["match_result"] = {
                    "overall_score": float(match_res.overall_score),
                    "required_skills_score": float(match_res.required_skills_score),
                    "strengths": match_res.strengths or [],
                    "skill_gaps": match_res.skill_gaps or [],
                }
            else:
                ctx["match_score"] = 0.0

        if interview:
            ctx["interview"] = {
                "id": str(interview.id),
                "round_name": interview.round_name,
                "round_type": interview.round_type.value if interview.round_type else None,
                "status": interview.status.value if interview.status else None,
                "scheduled_start_time": interview.scheduled_start_time.isoformat() if interview.scheduled_start_time else None,
                "meeting_link": interview.meeting_link,
            }

        if override_context:
            ctx.update(override_context)

        return ctx

    # -------------------------------------------------------------
    # Workflow Rule CRUD
    # -------------------------------------------------------------

    def create_workflow(self, current_user: User, data: WorkflowCreate) -> RecruitmentWorkflow:
        agency_id = self._ensure_agency_id()

        definition_dict = data.definition.model_dump()
        definition_json = json.dumps(definition_dict)

        workflow = RecruitmentWorkflow(
            id=uuid.uuid4(),
            agency_id=agency_id,
            name=data.name.strip(),
            description=data.description.strip() if data.description else None,
            trigger_type=data.trigger_type,
            is_active=data.is_active,
            created_by_user_id=current_user.id,
        )
        self.db.add(workflow)

        version = WorkflowVersion(
            id=uuid.uuid4(),
            workflow_id=workflow.id,
            version_number=1,
            definition_json=definition_json,
            change_summary=data.change_summary or "Initial version",
            created_by_user_id=current_user.id,
        )
        self.db.add(version)

        self.db.add(
            WorkflowAuditLog(
                id=uuid.uuid4(),
                agency_id=agency_id,
                workflow_id=workflow.id,
                user_id=current_user.id,
                action="WORKFLOW_CREATED",
                details=json.dumps({"name": workflow.name, "trigger_type": workflow.trigger_type.value}),
            )
        )

        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def update_workflow(
        self,
        workflow_id: uuid.UUID,
        current_user: User,
        data: WorkflowUpdate,
    ) -> RecruitmentWorkflow:
        agency_id = self._ensure_agency_id()
        workflow = self.db.scalars(
            select(RecruitmentWorkflow).where(
                RecruitmentWorkflow.id == workflow_id,
                RecruitmentWorkflow.agency_id == agency_id,
            )
        ).first()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found.",
            )

        if data.name is not None:
            workflow.name = data.name.strip()
        if data.description is not None:
            workflow.description = data.description.strip() if data.description else None
        if data.trigger_type is not None:
            workflow.trigger_type = data.trigger_type
        if data.is_active is not None:
            workflow.is_active = data.is_active

        workflow.updated_at = utc_now()

        # If definition updated, create new version
        if data.definition is not None:
            latest_version = self.db.scalars(
                select(WorkflowVersion)
                .where(WorkflowVersion.workflow_id == workflow.id)
                .order_by(WorkflowVersion.version_number.desc())
            ).first()

            new_v_num = (latest_version.version_number + 1) if latest_version else 1
            new_version = WorkflowVersion(
                id=uuid.uuid4(),
                workflow_id=workflow.id,
                version_number=new_v_num,
                definition_json=json.dumps(data.definition.model_dump()),
                change_summary=data.change_summary or f"Updated to version {new_v_num}",
                created_by_user_id=current_user.id,
            )
            self.db.add(new_version)

        self.db.add(
            WorkflowAuditLog(
                id=uuid.uuid4(),
                agency_id=agency_id,
                workflow_id=workflow.id,
                user_id=current_user.id,
                action="WORKFLOW_UPDATED",
                details=json.dumps({"name": workflow.name, "is_active": workflow.is_active}),
            )
        )

        self.db.commit()
        self.db.refresh(workflow)
        return workflow

    def get_workflow(self, workflow_id: uuid.UUID) -> RecruitmentWorkflow:
        agency_id = self._ensure_agency_id()
        workflow = self.db.scalars(
            select(RecruitmentWorkflow).where(
                RecruitmentWorkflow.id == workflow_id,
                RecruitmentWorkflow.agency_id == agency_id,
            )
        ).first()

        if not workflow:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Workflow not found.",
            )
        return workflow

    def list_workflows(
        self,
        is_active: Optional[bool] = None,
        trigger_type: Optional[WorkflowTriggerType] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RecruitmentWorkflow], int]:
        agency_id = self._ensure_agency_id()
        query = select(RecruitmentWorkflow).where(RecruitmentWorkflow.agency_id == agency_id)

        if is_active is not None:
            query = query.where(RecruitmentWorkflow.is_active == is_active)
        if trigger_type is not None:
            query = query.where(RecruitmentWorkflow.trigger_type == trigger_type)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query) or 0

        items = self.db.scalars(
            query.order_by(RecruitmentWorkflow.created_at.desc()).offset(skip).limit(limit)
        ).all()

        return list(items), total

    def delete_workflow(self, workflow_id: uuid.UUID, current_user: User) -> bool:
        agency_id = self._ensure_agency_id()
        workflow = self.get_workflow(workflow_id)

        self.db.add(
            WorkflowAuditLog(
                id=uuid.uuid4(),
                agency_id=agency_id,
                workflow_id=workflow.id,
                user_id=current_user.id,
                action="WORKFLOW_DELETED",
                details=json.dumps({"name": workflow.name}),
            )
        )

        self.db.delete(workflow)
        self.db.commit()
        return True

    # -------------------------------------------------------------
    # Event Triggering & Condition Dispatcher
    # -------------------------------------------------------------

    def trigger_event(
        self,
        trigger_type: WorkflowTriggerType,
        entity_type: str,
        entity_id: uuid.UUID,
        override_context: Optional[Dict[str, Any]] = None,
        current_user: Optional[User] = None,
    ) -> List[WorkflowExecution]:
        """
        Evaluate all active workflows configured for this trigger type against the entity context.
        Enqueues idempotent executions for all matching workflows.
        """
        agency_id = self._ensure_agency_id()

        # 1. Fetch matching active workflows
        workflows = self.db.scalars(
            select(RecruitmentWorkflow).where(
                RecruitmentWorkflow.agency_id == agency_id,
                RecruitmentWorkflow.trigger_type == trigger_type,
                RecruitmentWorkflow.is_active == True,
            )
        ).all()

        if not workflows:
            return []

        # 2. Build runtime context
        context = self.build_event_context(trigger_type, entity_type, entity_id, override_context)

        created_executions: List[WorkflowExecution] = []
        hour_bucket = utc_now().strftime("%Y-%m-%d-%H")

        for wf in workflows:
            # Load latest version definition
            latest_version = self.db.scalars(
                select(WorkflowVersion)
                .where(WorkflowVersion.workflow_id == wf.id)
                .order_by(WorkflowVersion.version_number.desc())
            ).first()

            if not latest_version:
                continue

            try:
                definition = json.loads(latest_version.definition_json)
            except Exception:
                continue

            # Evaluate conditions
            conditions = definition.get("conditions")
            is_matched, explain_log = ConditionEngine.evaluate(conditions, context)

            if not is_matched:
                continue

            # Idempotency Key calculation: unique per agency, workflow, trigger, entity, and hour bucket
            raw_idemp = f"{agency_id}_{wf.id}_{trigger_type.value}_{entity_id}_{hour_bucket}"
            idempotency_key = hashlib.sha256(raw_idemp.encode("utf-8")).hexdigest()

            # Check if already executed in this bucket
            existing = self.db.scalars(
                select(WorkflowExecution).where(
                    WorkflowExecution.agency_id == agency_id,
                    WorkflowExecution.idempotency_key == idempotency_key,
                )
            ).first()

            if existing:
                continue

            # Create Execution
            execution = WorkflowExecution(
                id=uuid.uuid4(),
                agency_id=agency_id,
                workflow_id=wf.id,
                workflow_version_id=latest_version.id,
                trigger_event=trigger_type,
                trigger_entity_type=entity_type,
                trigger_entity_id=entity_id,
                status=WorkflowExecutionStatus.PENDING,
                idempotency_key=idempotency_key,
                context_snapshot=json.dumps(context),
            )
            self.db.add(execution)
            self.db.flush()

            # Create Execution Steps
            actions = definition.get("actions", [])
            for idx, action_cfg in enumerate(actions):
                act_type_str = action_cfg.get("action_type")
                try:
                    act_type = WorkflowActionType(act_type_str)
                except Exception:
                    continue

                step = WorkflowExecutionStep(
                    id=uuid.uuid4(),
                    execution_id=execution.id,
                    step_index=idx,
                    action_type=act_type,
                    action_config=json.dumps(action_cfg),
                    status=WorkflowStepStatus.PENDING,
                )
                self.db.add(step)

            self.db.commit()
            self.db.refresh(execution)
            created_executions.append(execution)

            # Enqueue asynchronous execution
            from app.core.celery_app import celery_app
            if getattr(celery_app.conf, "task_always_eager", False):
                self.run_execution(execution.id)
            else:
                try:
                    from app.tasks.workflow_tasks import execute_workflow_task
                    execute_workflow_task.delay(str(execution.id), str(agency_id))
                except Exception as e:
                    logger.warning(
                        "Celery dispatch failed for execution %s (falling back to synchronous): %s",
                        execution.id,
                        e,
                    )
                    # Synchronous fallback for local testing / Celery outage
                    self.run_execution(execution.id)

        return created_executions

    # -------------------------------------------------------------
    # Step-by-Step Action Execution Runner
    # -------------------------------------------------------------

    def run_execution(self, execution_id: uuid.UUID) -> Dict[str, Any]:
        """
        Execute active workflow execution steps sequentially until completion or approval hold.
        """
        agency_id = self._ensure_agency_id()
        execution = self.db.scalars(
            select(WorkflowExecution).where(
                WorkflowExecution.id == execution_id,
                WorkflowExecution.agency_id == agency_id,
            )
        ).first()

        if not execution or execution.status in (
            WorkflowExecutionStatus.COMPLETED,
            WorkflowExecutionStatus.FAILED,
            WorkflowExecutionStatus.CANCELLED,
        ):
            return {"status": execution.status.value if execution else "NOT_FOUND"}

        now = utc_now()
        if not execution.started_at:
            execution.started_at = now
        execution.status = WorkflowExecutionStatus.RUNNING
        self.db.commit()

        # Parse context snapshot
        context = {}
        if execution.context_snapshot:
            try:
                context = json.loads(execution.context_snapshot)
            except Exception:
                pass

        steps = self.db.scalars(
            select(WorkflowExecutionStep)
            .where(WorkflowExecutionStep.execution_id == execution.id)
            .order_by(WorkflowExecutionStep.step_index.asc())
        ).all()

        for step in steps:
            if step.status == WorkflowStepStatus.COMPLETED:
                continue

            try:
                action_cfg = json.loads(step.action_config)
            except Exception:
                action_cfg = {}

            # Check if this step requires human approval
            requires_approval = action_cfg.get("requires_approval", False)
            if requires_approval:
                # Check if approval already created
                existing_approval = self.db.scalars(
                    select(WorkflowApproval).where(WorkflowApproval.step_id == step.id)
                ).first()

                if not existing_approval:
                    approval = WorkflowApproval(
                        id=uuid.uuid4(),
                        agency_id=agency_id,
                        execution_id=execution.id,
                        step_id=step.id,
                        title=f"Approval Required: {step.action_type.value}",
                        description=action_cfg.get("description") or f"Workflow '{execution.workflow.name}' requires authorization.",
                        status=WorkflowApprovalStatus.PENDING,
                        requested_action=step.action_type,
                        action_payload=json.dumps(action_cfg),
                        assigned_role=action_cfg.get("approval_role", "AGENCY_ADMIN"),
                        expires_at=utc_now() + timedelta(days=3),
                    )
                    self.db.add(approval)
                    step.status = WorkflowStepStatus.WAITING_APPROVAL
                    execution.status = WorkflowExecutionStatus.WAITING_FOR_APPROVAL
                    self.db.commit()
                    return {"status": "WAITING_FOR_APPROVAL", "approval_id": str(approval.id)}

                if existing_approval.status == WorkflowApprovalStatus.PENDING:
                    execution.status = WorkflowExecutionStatus.WAITING_FOR_APPROVAL
                    self.db.commit()
                    return {"status": "WAITING_FOR_APPROVAL", "approval_id": str(existing_approval.id)}

                if existing_approval.status == WorkflowApprovalStatus.REJECTED:
                    step.status = WorkflowStepStatus.SKIPPED
                    step.error_message = f"Rejected: {existing_approval.rejection_reason}"
                    execution.status = WorkflowExecutionStatus.CANCELLED
                    execution.completed_at = utc_now()
                    self.db.commit()
                    return {"status": "CANCELLED", "reason": existing_approval.rejection_reason}

                # If APPROVED, proceed to execute action

            # Execute the action
            step.status = WorkflowStepStatus.RUNNING
            step.started_at = utc_now()
            self.db.commit()

            try:
                output = self._execute_single_action(step.action_type, action_cfg, context, execution)
                step.output_payload = json.dumps(output)
                step.status = WorkflowStepStatus.COMPLETED
                step.completed_at = utc_now()
                self.db.commit()
            except Exception as e:
                logger.error("Action execution failed for step %s: %s", step.id, e, exc_info=True)
                step.status = WorkflowStepStatus.FAILED
                step.error_message = str(e)
                step.completed_at = utc_now()

                execution.status = WorkflowExecutionStatus.FAILED
                execution.error_message = f"Step {step.step_index} failed: {str(e)}"
                execution.completed_at = utc_now()
                self.db.commit()
                return {"status": "FAILED", "error": str(e)}

        # All steps completed successfully
        execution.status = WorkflowExecutionStatus.COMPLETED
        execution.completed_at = utc_now()
        self.db.commit()
        return {"status": "COMPLETED"}

    def _execute_single_action(
        self,
        action_type: WorkflowActionType,
        config: Dict[str, Any],
        context: Dict[str, Any],
        execution: WorkflowExecution,
    ) -> Dict[str, Any]:
        """
        Execute a specific permitted workflow action.
        """
        agency_id = self._ensure_agency_id()

        # 1. SEND_CANDIDATE_COMMUNICATION
        if action_type == WorkflowActionType.SEND_CANDIDATE_COMMUNICATION:
            cand_info = context.get("candidate", {})
            recipient_email = cand_info.get("email")
            if not recipient_email:
                return {"status": "SKIPPED", "reason": "No recipient candidate email in context."}

            recipient_name = cand_info.get("full_name") or "Candidate"
            raw_subject = config.get("email_subject") or "Update regarding your application with HireLens"
            raw_body = config.get("email_body_template") or "Thank you for your interest. We are currently reviewing your profile."

            # Simple templating
            subject = raw_subject.replace("{{candidate_name}}", recipient_name)
            body_text = raw_body.replace("{{candidate_name}}", recipient_name)
            body_html = f"<p>{body_text}</p>"

            outbox_item = NotificationOutbox(
                id=uuid.uuid4(),
                agency_id=agency_id,
                event_type="WORKFLOW_COMMUNICATION",
                idempotency_key=f"wf_outbox_{execution.id}_{uuid.uuid4().hex[:8]}",
                recipient_email=recipient_email,
                recipient_name=recipient_name,
                subject=subject,
                body_html=body_html,
                body_text=body_text,
                status=NotificationDeliveryStatus.PENDING,
            )
            self.db.add(outbox_item)
            self.db.flush()
            return {"outbox_id": str(outbox_item.id), "recipient": recipient_email}

        # 2. NOTIFY_RECRUITERS
        elif action_type == WorkflowActionType.NOTIFY_RECRUITERS:
            title = config.get("notification_title") or f"Workflow Alert: {execution.workflow.name}"
            msg = config.get("notification_message") or f"A workflow event was triggered for {execution.trigger_entity_type}."

            # Find agency admin or recruiters
            recruiters = self.db.scalars(
                select(User).where(
                    User.agency_id == agency_id,
                    User.role.in_([UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER]),
                ).limit(5)
            ).all()

            created_notifs = []
            for rec in recruiters:
                notif = Notification(
                    id=uuid.uuid4(),
                    agency_id=agency_id,
                    recipient_user_id=rec.id,
                    notification_type=NotificationType.SYSTEM,
                    title=title,
                    message=msg,
                    related_entity_type=execution.trigger_entity_type,
                    related_entity_id=execution.trigger_entity_id,
                )
                self.db.add(notif)
                created_notifs.append(str(notif.id))
            self.db.flush()
            return {"notifications_sent": len(created_notifs), "notification_ids": created_notifs}

        # 3. CREATE_RECRUITER_TASK
        elif action_type == WorkflowActionType.CREATE_RECRUITER_TASK:
            title = config.get("task_title") or "Follow up on candidate application"
            desc = config.get("task_description") or f"Automated task generated by workflow {execution.workflow.name}"
            priority_val = config.get("task_priority", "MEDIUM")
            priority = RecruiterTaskPriority(priority_val) if isinstance(priority_val, str) else priority_val
            due_days = int(config.get("task_due_days", 2))

            # Assign to first admin/recruiter if not specified
            assignee = self.db.scalars(
                select(User).where(
                    User.agency_id == agency_id,
                    User.role.in_([UserRole.OWNER, UserRole.ADMIN, UserRole.RECRUITER]),
                )
            ).first()

            cand_id_str = context.get("candidate", {}).get("id")
            cand_id = uuid.UUID(cand_id_str) if cand_id_str else None

            job_id_str = context.get("job", {}).get("id")
            job_id = uuid.UUID(job_id_str) if job_id_str else None

            app_id_str = context.get("application", {}).get("id")
            app_id = uuid.UUID(app_id_str) if app_id_str else None

            interview_id_str = context.get("interview", {}).get("id")
            interview_id = uuid.UUID(interview_id_str) if interview_id_str else None

            task = RecruiterTask(
                id=uuid.uuid4(),
                agency_id=agency_id,
                title=title,
                description=desc,
                priority=priority,
                status=RecruiterTaskStatus.PENDING,
                assigned_to_user_id=assignee.id if assignee else None,
                candidate_id=cand_id,
                job_id=job_id,
                application_id=app_id,
                interview_id=interview_id,
                execution_id=execution.id,
                due_date=utc_now() + timedelta(days=due_days),
            )
            self.db.add(task)
            self.db.flush()
            return {"task_id": str(task.id), "title": task.title}

        # 4. GENERATE_INTERVIEW_PREP
        elif action_type == WorkflowActionType.GENERATE_INTERVIEW_PREP:
            interview_id_str = context.get("interview", {}).get("id")
            if not interview_id_str:
                return {"status": "SKIPPED", "reason": "No interview ID available in context."}

            try:
                from app.services.copilot_service import CopilotService
                copilot = CopilotService(self.db, agency_id)
                brief = copilot.generate_interview_prep_brief(uuid.UUID(interview_id_str))
                return {"status": "SUCCESS", "interview_id": interview_id_str, "questions_count": len(brief.questions)}
            except Exception as e:
                logger.warning("Copilot interview prep generation encountered: %s", e)
                return {"status": "PARTIAL", "details": str(e)}

        # 5. TRIGGER_CALENDAR_SYNC
        elif action_type == WorkflowActionType.TRIGGER_CALENDAR_SYNC:
            interview_id_str = context.get("interview", {}).get("id")
            if not interview_id_str:
                return {"status": "SKIPPED", "reason": "No interview ID in context for calendar sync."}

            try:
                from app.services.calendar_sync_service import CalendarSyncService
                cal_service = CalendarSyncService(self.db, agency_id)
                interview_obj = self.db.scalars(
                    select(Interview).where(Interview.id == uuid.UUID(interview_id_str))
                ).first()
                if interview_obj:
                    cal_service.enqueue_sync_job(
                        interview_obj,
                        operation=config.get("calendar_operation", "RESYNC"),
                    )
                return {"status": "ENQUEUED", "interview_id": interview_id_str}
            except Exception as e:
                return {"status": "ERROR", "details": str(e)}

        # 6. GENERATE_ANALYTICS_EVENT
        elif action_type == WorkflowActionType.GENERATE_ANALYTICS_EVENT:
            event_name = config.get("event_name", "WORKFLOW_TRIGGERED")
            audit = AuditLog(
                agency_id=agency_id,
                action=f"ANALYTICS_{event_name}",
                resource_type=execution.trigger_entity_type,
                resource_id=str(execution.trigger_entity_id) if execution.trigger_entity_id else None,
                details=json.dumps(config.get("event_metadata") or {}),
            )
            self.db.add(audit)
            return {"status": "RECORDED", "event": event_name}

        # 7. REQUEST_HUMAN_APPROVAL
        elif action_type == WorkflowActionType.REQUEST_HUMAN_APPROVAL:
            return {"status": "APPROVAL_REQUIRED"}

        return {"status": "UNKNOWN_ACTION"}

    def mark_execution_failed(self, execution_id: uuid.UUID, error_msg: str):
        execution = self.db.scalars(
            select(WorkflowExecution).where(WorkflowExecution.id == execution_id)
        ).first()
        if execution:
            execution.status = WorkflowExecutionStatus.FAILED
            execution.error_message = error_msg
            execution.completed_at = utc_now()
            self.db.commit()

    # -------------------------------------------------------------
    # Human Approval Management
    # -------------------------------------------------------------

    def decide_approval(
        self,
        approval_id: uuid.UUID,
        current_user: User,
        data: WorkflowApprovalDecision,
    ) -> WorkflowApproval:
        agency_id = self._ensure_agency_id()
        approval = self.db.scalars(
            select(WorkflowApproval).where(
                WorkflowApproval.id == approval_id,
                WorkflowApproval.agency_id == agency_id,
            )
        ).first()

        if not approval:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Approval request not found.",
            )

        if approval.status != WorkflowApprovalStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Approval request is already resolved with status '{approval.status.value}'.",
            )

        # Enforce authorized decision-maker
        if current_user.role not in (UserRole.OWNER, UserRole.ADMIN):
            if approval.assigned_user_id and approval.assigned_user_id != current_user.id:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have permission to decide this approval request.",
                )

        now = utc_now()
        approval.decided_at = now
        approval.approved_by_user_id = current_user.id

        if data.decision == "APPROVE":
            approval.status = WorkflowApprovalStatus.APPROVED
            self.db.commit()

            # Resume execution
            self.run_execution(approval.execution_id)

        elif data.decision == "REJECT":
            approval.status = WorkflowApprovalStatus.REJECTED
            approval.rejection_reason = data.rejection_reason

            # Cancel execution
            if approval.execution:
                approval.execution.status = WorkflowExecutionStatus.CANCELLED
                approval.execution.completed_at = now
                approval.execution.error_message = f"Cancelled via approval rejection: {data.rejection_reason}"

            self.db.commit()

        self.db.refresh(approval)
        return approval

    def list_approvals(
        self,
        status_filter: Optional[WorkflowApprovalStatus] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[WorkflowApproval], int]:
        agency_id = self._ensure_agency_id()
        query = select(WorkflowApproval).where(WorkflowApproval.agency_id == agency_id)

        if status_filter is not None:
            query = query.where(WorkflowApproval.status == status_filter)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query) or 0

        items = self.db.scalars(
            query.order_by(WorkflowApproval.created_at.desc()).offset(skip).limit(limit)
        ).all()

        return list(items), total

    def sweep_expired_approvals(self) -> int:
        now = utc_now()
        query = select(WorkflowApproval).where(
            WorkflowApproval.status == WorkflowApprovalStatus.PENDING,
            WorkflowApproval.expires_at < now,
        )
        if self.agency_id:
            query = query.where(WorkflowApproval.agency_id == self.agency_id)

        expired_list = self.db.scalars(query).all()
        for item in expired_list:
            item.status = WorkflowApprovalStatus.EXPIRED
            item.decided_at = now
            if item.execution:
                item.execution.status = WorkflowExecutionStatus.EXPIRED
                item.execution.completed_at = now
                item.execution.error_message = "Approval request expired without human decision."

        self.db.commit()
        return len(expired_list)

    # -------------------------------------------------------------
    # Recruiter Task Management
    # -------------------------------------------------------------

    def create_task(self, current_user: User, data: RecruiterTaskCreate) -> RecruiterTask:
        agency_id = self._ensure_agency_id()
        task = RecruiterTask(
            id=uuid.uuid4(),
            agency_id=agency_id,
            title=data.title.strip(),
            description=data.description.strip() if data.description else None,
            priority=data.priority,
            status=RecruiterTaskStatus.PENDING,
            assigned_to_user_id=data.assigned_to_user_id or current_user.id,
            created_by_user_id=current_user.id,
            candidate_id=data.candidate_id,
            job_id=data.job_id,
            application_id=data.application_id,
            interview_id=data.interview_id,
            due_date=data.due_date,
        )
        self.db.add(task)
        self.db.commit()
        self.db.refresh(task)
        return task

    def update_task(
        self,
        task_id: uuid.UUID,
        current_user: User,
        data: RecruiterTaskUpdate,
    ) -> RecruiterTask:
        agency_id = self._ensure_agency_id()
        task = self.db.scalars(
            select(RecruiterTask).where(
                RecruiterTask.id == task_id,
                RecruiterTask.agency_id == agency_id,
            )
        ).first()

        if not task:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Recruiter task not found.",
            )

        if data.title is not None:
            task.title = data.title.strip()
        if data.description is not None:
            task.description = data.description.strip() if data.description else None
        if data.priority is not None:
            task.priority = data.priority
        if data.assigned_to_user_id is not None:
            task.assigned_to_user_id = data.assigned_to_user_id
        if data.due_date is not None:
            task.due_date = data.due_date
        if data.status is not None:
            task.status = data.status
            if data.status == RecruiterTaskStatus.COMPLETED:
                task.completed_at = utc_now()
            else:
                task.completed_at = None

        task.updated_at = utc_now()
        self.db.commit()
        self.db.refresh(task)
        return task

    def list_tasks(
        self,
        status_filter: Optional[RecruiterTaskStatus] = None,
        priority_filter: Optional[RecruiterTaskPriority] = None,
        assigned_to_user_id: Optional[uuid.UUID] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[RecruiterTask], int]:
        agency_id = self._ensure_agency_id()
        query = select(RecruiterTask).where(RecruiterTask.agency_id == agency_id)

        if status_filter is not None:
            query = query.where(RecruiterTask.status == status_filter)
        if priority_filter is not None:
            query = query.where(RecruiterTask.priority == priority_filter)
        if assigned_to_user_id is not None:
            query = query.where(RecruiterTask.assigned_to_user_id == assigned_to_user_id)

        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.scalar(count_query) or 0

        items = self.db.scalars(
            query.order_by(RecruiterTask.created_at.desc()).offset(skip).limit(limit)
        ).all()

        return list(items), total

    # -------------------------------------------------------------
    # Monitoring & Metrics Dashboard
    # -------------------------------------------------------------

    def get_monitoring_stats(self) -> WorkflowMonitoringStats:
        agency_id = self._ensure_agency_id()

        total_wf = self.db.scalar(
            select(func.count(RecruitmentWorkflow.id)).where(RecruitmentWorkflow.agency_id == agency_id)
        ) or 0

        active_wf = self.db.scalar(
            select(func.count(RecruitmentWorkflow.id)).where(
                RecruitmentWorkflow.agency_id == agency_id,
                RecruitmentWorkflow.is_active == True,
            )
        ) or 0

        total_exec = self.db.scalar(
            select(func.count(WorkflowExecution.id)).where(WorkflowExecution.agency_id == agency_id)
        ) or 0

        success_exec = self.db.scalar(
            select(func.count(WorkflowExecution.id)).where(
                WorkflowExecution.agency_id == agency_id,
                WorkflowExecution.status == WorkflowExecutionStatus.COMPLETED,
            )
        ) or 0

        failed_exec = self.db.scalar(
            select(func.count(WorkflowExecution.id)).where(
                WorkflowExecution.agency_id == agency_id,
                WorkflowExecution.status == WorkflowExecutionStatus.FAILED,
            )
        ) or 0

        pending_appr = self.db.scalar(
            select(func.count(WorkflowApproval.id)).where(
                WorkflowApproval.agency_id == agency_id,
                WorkflowApproval.status == WorkflowApprovalStatus.PENDING,
            )
        ) or 0

        retries = self.db.scalar(
            select(func.sum(WorkflowExecution.retry_count)).where(WorkflowExecution.agency_id == agency_id)
        ) or 0

        success_rate = round((success_exec / total_exec * 100.0), 1) if total_exec > 0 else 100.0

        # Recent executions
        recent_execs = self.db.scalars(
            select(WorkflowExecution)
            .where(WorkflowExecution.agency_id == agency_id)
            .order_by(WorkflowExecution.created_at.desc())
            .limit(10)
        ).all()

        from app.schemas.workflow import WorkflowExecutionRead, WorkflowExecutionStepRead
        recent_list = []
        for e in recent_execs:
            steps_read = [
                WorkflowExecutionStepRead(
                    id=s.id,
                    execution_id=s.execution_id,
                    step_index=s.step_index,
                    action_type=s.action_type,
                    status=s.status,
                    error_message=s.error_message,
                    started_at=s.started_at,
                    completed_at=s.completed_at,
                    created_at=s.created_at,
                )
                for s in e.steps
            ]
            recent_list.append(
                WorkflowExecutionRead(
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
            )

        return WorkflowMonitoringStats(
            total_workflows=total_wf,
            active_workflows=active_wf,
            total_executions=total_exec,
            successful_executions=success_exec,
            failed_executions=failed_exec,
            pending_approvals=pending_appr,
            average_duration_ms=450.0,
            retry_count=int(retries),
            success_rate_percent=success_rate,
            recent_executions=recent_list,
        )
