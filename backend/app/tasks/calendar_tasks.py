import uuid
import logging
from datetime import datetime, timezone
from sqlalchemy import select
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.calendar_tasks.dispatch_calendar_sync_job_task",
    max_retries=3,
    default_retry_delay=10,
)
def dispatch_calendar_sync_job_task(self, job_id_str: str, agency_id_str: str, db_override=None):
    """
    Background worker task to dispatch a single calendar synchronization job.
    """
    job_id = uuid.UUID(job_id_str)
    agency_id = uuid.UUID(agency_id_str)

    db = db_override or SessionLocal()
    close_db = db_override is None
    try:
        from app.services.calendar_sync_service import CalendarSyncService
        service = CalendarSyncService(db, agency_id)
        success = service.process_sync_job(job_id)
        return {"status": "SUCCESS" if success else "FAILED", "job_id": job_id_str}
    except Exception as exc:
        logger.error(
            "Task dispatch_calendar_sync_job_task failed for job %s (agency %s): %s",
            job_id_str,
            agency_id_str,
            str(exc),
            exc_info=True,
        )
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            raise exc
    finally:
        if close_db:
            db.close()


@celery_app.task(
    name="app.tasks.calendar_tasks.process_calendar_sync_batch_task",
)
def process_calendar_sync_batch_task(agency_id_str: str, limit: int = 25, db_override=None):
    """
    Periodic background task to sweep and process pending/retryable calendar sync jobs.
    """
    agency_id = uuid.UUID(agency_id_str)
    db = db_override or SessionLocal()
    close_db = db_override is None
    try:
        from app.models.calendar import CalendarSyncJob
        from app.services.calendar_sync_service import CalendarSyncService

        now = datetime.now(timezone.utc)
        stmt = (
            select(CalendarSyncJob.id)
            .where(
                CalendarSyncJob.agency_id == agency_id,
                CalendarSyncJob.status == "PENDING",
                CalendarSyncJob.scheduled_at <= now,
            )
            .order_by(CalendarSyncJob.scheduled_at.asc())
            .limit(limit)
        )
        job_ids = list(db.scalars(stmt).all())
        service = CalendarSyncService(db, agency_id)

        processed = 0
        for jid in job_ids:
            if service.process_sync_job(jid):
                processed += 1

        return {"status": "SUCCESS", "processed_count": processed, "total_found": len(job_ids)}
    except Exception as exc:
        logger.error("Error processing calendar sync batch for agency %s: %s", agency_id_str, exc, exc_info=True)
        return {"status": "ERROR", "error": str(exc)}
    finally:
        if close_db:
            db.close()
