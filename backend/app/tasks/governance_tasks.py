import uuid
import logging
from typing import Optional
from app.core.celery_app import celery_app
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@celery_app.task(
    name="app.tasks.governance_tasks.evaluate_retention_policies_task",
)
def evaluate_retention_policies_task(agency_id_str: Optional[str] = None):
    """
    Periodic task to evaluate and execute enabled data retention policies.
    """
    db = SessionLocal()
    try:
        from app.models.entities import Agency
        from app.models.governance import DataRetentionPolicy
        from app.services.governance_service import GovernanceService
        from sqlalchemy import select

        agency_ids = []
        if agency_id_str:
            agency_ids.append(uuid.UUID(agency_id_str))
        else:
            agencies = db.scalars(select(Agency).where(Agency.is_active == True)).all()
            agency_ids = [a.id for a in agencies]

        total_policies_executed = 0
        for aid in agency_ids:
            service = GovernanceService(db, aid)
            enabled_policies = db.scalars(
                select(DataRetentionPolicy).where(
                    DataRetentionPolicy.agency_id == aid,
                    DataRetentionPolicy.is_enabled == True,
                )
            ).all()

            for p in enabled_policies:
                try:
                    service.execute_retention_policy(p.id, is_dry_run=False)
                    total_policies_executed += 1
                except Exception as e:
                    logger.error("Failed to execute retention policy %s for agency %s: %s", p.id, aid, e)

        return {"status": "SUCCESS", "policies_executed": total_policies_executed}
    finally:
        db.close()


@celery_app.task(
    name="app.tasks.governance_tasks.cleanup_expired_sessions_task",
)
def cleanup_expired_sessions_task():
    """
    Periodic task to sweep and invalidate stale sessions past 30 days of inactivity.
    """
    db = SessionLocal()
    try:
        from app.models.governance import UserSession
        from app.models.base import utc_now
        from datetime import timedelta
        from sqlalchemy import select

        cutoff = utc_now() - timedelta(days=30)
        stale_sessions = db.scalars(
            select(UserSession).where(
                UserSession.is_active == True,
                UserSession.last_activity_at <= cutoff,
            )
        ).all()

        for s in stale_sessions:
            s.is_active = False
            s.revoked_at = utc_now()
            s.revocation_reason = "Inactivity expiration (30 days)"

        db.commit()
        return {"status": "SUCCESS", "expired_sessions_count": len(stale_sessions)}
    finally:
        db.close()
