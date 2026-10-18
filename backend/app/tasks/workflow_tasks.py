import uuid
import logging
from typing import Optional
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.base import utc_now

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.workflow_tasks.execute_workflow_task",
    max_retries=3,
    default_retry_delay=10,
)
def execute_workflow_task(self, execution_id_str: str, agency_id_str: str):
    """
    Background worker task to execute an active workflow run or resume steps.
    """
    execution_id = uuid.UUID(execution_id_str)
    agency_id = uuid.UUID(agency_id_str)

    db = SessionLocal()
    try:
        from app.services.workflow_service import WorkflowService
        service = WorkflowService(db, agency_id)
        result = service.run_execution(execution_id)
        return {"status": result.get("status"), "execution_id": execution_id_str}
    except Exception as exc:
        logger.error(
            "Workflow execution task failed for execution %s (agency %s): %s",
            execution_id_str,
            agency_id_str,
            str(exc),
            exc_info=True,
        )
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Mark execution as permanently failed in DB if max retries exceeded
            try:
                from app.services.workflow_service import WorkflowService
                WorkflowService(db, agency_id).mark_execution_failed(execution_id, f"Max retries exceeded: {str(exc)}")
            except Exception:
                pass
            raise exc
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.workflow_tasks.sweep_expired_approvals_task",
)
def sweep_expired_approvals_task(agency_id_str: Optional[str] = None):
    """
    Periodic task to expire stale pending approvals past their deadline.
    """
    db = SessionLocal()
    try:
        from app.services.workflow_service import WorkflowService
        agency_id = uuid.UUID(agency_id_str) if agency_id_str else None
        service = WorkflowService(db, agency_id=agency_id)
        count = service.sweep_expired_approvals()
        return {"status": "SUCCESS", "expired_count": count}
    except Exception as exc:
        logger.error("Error sweeping expired workflow approvals: %s", exc, exc_info=True)
        return {"status": "ERROR", "error": str(exc)}
    finally:
        db.close()
