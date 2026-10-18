import uuid
import logging
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.notification_tasks.dispatch_outbox_email_task",
    max_retries=2,
    default_retry_delay=5,
)
def dispatch_outbox_email_task(self, outbox_id_str: str, agency_id_str: str):
    """
    Background worker task to dispatch a single transactional outbox email.
    """
    outbox_id = uuid.UUID(outbox_id_str)
    agency_id = uuid.UUID(agency_id_str)

    db = SessionLocal()
    try:
        from app.services.notification_service import NotificationService
        service = NotificationService(db, agency_id)
        success = service.dispatch_outbox_item(outbox_id)
        return {"status": "SUCCESS" if success else "FAILED", "outbox_id": outbox_id_str}
    except Exception as exc:
        logger.error(
            "Task dispatch_outbox_email_task failed for outbox %s (agency %s): %s",
            outbox_id_str,
            agency_id_str,
            str(exc),
            exc_info=True,
        )
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            raise exc
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.notification_tasks.process_outbox_batch_task",
)
def process_outbox_batch_task(agency_id_str: str, limit: int = 25):
    """
    Periodic or background task to sweep and process pending/retryable outbox items.
    """
    agency_id = uuid.UUID(agency_id_str)
    db = SessionLocal()
    try:
        from app.services.notification_service import NotificationService
        service = NotificationService(db, agency_id)
        processed = service.process_pending_outbox(limit=limit)
        return {"status": "SUCCESS", "processed_count": processed}
    except Exception as exc:
        logger.error("Error processing outbox batch for agency %s: %s", agency_id_str, exc, exc_info=True)
        return {"status": "ERROR", "error": str(exc)}
    finally:
        db.close()
