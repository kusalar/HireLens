import uuid
import logging
from typing import Optional
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    name="app.tasks.predictive_tasks.refresh_predictive_intelligence_task",
    max_retries=3,
    default_retry_delay=15,
)
def refresh_predictive_intelligence_task(self, agency_id_str: str, user_id_str: Optional[str] = None):
    """
    Background Celery worker task to re-calculate forecasts, re-evaluate bottlenecks,
    scan recruitment risks, and update recruiter capacity snapshots.
    """
    agency_id = uuid.UUID(agency_id_str)
    user_id = uuid.UUID(user_id_str) if user_id_str else None

    db = SessionLocal()
    try:
        from app.services.predictive_service import PredictiveService
        service = PredictiveService(db, agency_id)
        result = service.refresh_predictive_intelligence(user_id=user_id)
        logger.info(
            "Predictive intelligence successfully refreshed for agency %s: %s forecasts, %s risks.",
            agency_id_str,
            result.forecasts_generated,
            result.risks_detected,
        )
        return {
            "status": result.status,
            "forecasts_generated": result.forecasts_generated,
            "risks_detected": result.risks_detected,
            "timestamp": result.timestamp,
        }
    except Exception as exc:
        logger.error(
            "Failed to refresh predictive intelligence for agency %s: %s",
            agency_id_str,
            str(exc),
            exc_info=True,
        )
        try:
            self.retry(exc=exc)
        except self.MaxRetriesExceededError:
            logger.error("Max retries exceeded for predictive intelligence refresh: %s", str(exc))
            raise exc
    finally:
        db.close()
