import logging
from datetime import datetime, timezone, timedelta
from sqlalchemy import select, and_, or_
from app.core.celery_app import celery_app
from app.db.session import SessionLocal
from app.models.base import utc_now
from app.models.enums import SubscriptionStatus, SubscriptionTier
from app.models.billing import AgencySubscription, SubscriptionPlan, SubscriptionHistory
from app.services.billing_service import BillingService

logger = logging.getLogger(__name__)


@celery_app.task(name="billing.check_subscription_renewals")
def check_subscription_renewals_task():
    """
    Daily scheduled job evaluating expiring subscriptions.
    Renews active subscriptions or transitions failed renewals to PAST_DUE.
    """
    db = SessionLocal()
    try:
        now = utc_now()
        expiring_subs = db.scalars(
            select(AgencySubscription).where(
                and_(
                    AgencySubscription.status == SubscriptionStatus.ACTIVE,
                    AgencySubscription.current_period_end <= now,
                )
            )
        ).all()

        logger.info(f"Checking subscription renewals: found {len(expiring_subs)} due.")
        renewed_count = 0
        past_due_count = 0

        for sub in expiring_subs:
            plan = db.get(SubscriptionPlan, sub.plan_id)
            if not plan:
                continue

            if sub.cancel_at_period_end:
                # Downgrade to FREE
                free_plan = db.scalar(
                    select(SubscriptionPlan).where(SubscriptionPlan.tier == SubscriptionTier.FREE)
                )
                if free_plan:
                    sub.plan_id = free_plan.id
                    sub.status = SubscriptionStatus.ACTIVE
                    sub.cancel_at_period_end = False
                    sub.current_period_start = now
                    sub.current_period_end = now + timedelta(days=3650)
                    past_due_count += 1
            else:
                # Auto-renew
                sub.current_period_start = now
                sub.current_period_end = now + timedelta(days=30)
                renewed_count += 1

        db.commit()
        logger.info(f"Renewals complete: {renewed_count} renewed, {past_due_count} reverted to Free.")
        return {"renewed": renewed_count, "reverted": past_due_count}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in check_subscription_renewals_task: {e}")
        raise
    finally:
        db.close()


@celery_app.task(name="billing.check_trial_expirations")
def check_trial_expirations_task():
    """
    Checks trialing subscriptions and downgrades or sets past_due if trial has expired.
    """
    db = SessionLocal()
    try:
        now = utc_now()
        expired_trials = db.scalars(
            select(AgencySubscription).where(
                and_(
                    AgencySubscription.status == SubscriptionStatus.TRIALING,
                    AgencySubscription.trial_end.is_not(None),
                    AgencySubscription.trial_end <= now,
                )
            )
        ).all()

        free_plan = db.scalar(
            select(SubscriptionPlan).where(SubscriptionPlan.tier == SubscriptionTier.FREE)
        )

        for sub in expired_trials:
            if free_plan:
                sub.plan_id = free_plan.id
                sub.status = SubscriptionStatus.ACTIVE
                sub.trial_end = None

        db.commit()
        return {"expired_trials_processed": len(expired_trials)}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in check_trial_expirations_task: {e}")
        raise
    finally:
        db.close()
