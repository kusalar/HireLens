from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "hirelens_tasks",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=False,
    broker_connection_timeout=0.1,
    broker_connection_max_retries=0,
)

# Autodiscover tasks
celery_app.autodiscover_tasks([
    "app.tasks.resume_tasks",
    "app.tasks.notification_tasks",
    "app.tasks.calendar_tasks",
    "app.tasks.workflow_tasks",
    "app.tasks.predictive_tasks",
    "app.tasks.governance_tasks",
    "app.tasks.billing_tasks",
])

# Celery Beat Periodic Task Schedules
from celery.schedules import crontab

celery_app.conf.beat_schedule = {
    "daily-subscription-renewal-check": {
        "task": "app.tasks.billing_tasks.check_subscription_renewals_task",
        "schedule": crontab(minute=0, hour=0),  # Midnight UTC
    },
    "hourly-trial-expiration-check": {
        "task": "app.tasks.billing_tasks.check_trial_expirations_task",
        "schedule": crontab(minute=0, hour="*"),  # Every hour
    },
    "daily-data-retention-sweep": {
        "task": "app.tasks.governance_tasks.execute_retention_sweep_task",
        "schedule": crontab(minute=0, hour=2),  # 02:00 UTC
    },
}



