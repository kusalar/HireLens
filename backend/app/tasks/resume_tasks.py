import uuid
import logging
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.resume_tasks.process_resume_pipeline_task",
    max_retries=2,
    default_retry_delay=10,
)
def process_resume_pipeline_task(self, resume_id_str: str, agency_id_str: str):
    """
    Background worker task to extract text and structured profile for a resume.
    """
    resume_id = uuid.UUID(resume_id_str)
    agency_id = uuid.UUID(agency_id_str)

    db = SessionLocal()
    try:
        from app.services.resume_service import ResumeService

        service = ResumeService(db, agency_id)
        service.process_pipeline(resume_id)
        return {"status": "SUCCESS", "resume_id": resume_id_str}
    except Exception as exc:
        logger.error(
            "Task failed for resume %s (agency %s): %s",
            resume_id_str,
            agency_id_str,
            str(exc),
            exc_info=True,
        )
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            # Leave safe failed status
            try:
                from app.models.resume import Resume
                from app.models.enums import ResumeProcessingStatus
                r = db.query(Resume).filter(Resume.id == resume_id, Resume.agency_id == agency_id).first()
                if r:
                    r.processing_status = ResumeProcessingStatus.FAILED
                    r.error_message = f"Background processing failed after retries: {str(exc)}"
                    db.commit()
            except Exception:
                db.rollback()
            raise exc
    finally:
        db.close()
