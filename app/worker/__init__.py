"""Celery application configuration.

This module configures the Celery app for async task processing.
Tasks include OMR processing, file uploads, and other background jobs.

Usage:
    # Start worker
    celery -A app.worker.celery_app worker --loglevel=info

    # Start with beat scheduler (if periodic tasks needed)
    celery -A app.worker.celery_app worker --beat --loglevel=info
"""

from celery import Celery

from app.settings import settings

# Create Celery app
celery_app = Celery(
    "sound_first",
    broker=settings.effective_celery_broker,
    backend=settings.effective_celery_backend,
    include=["app.worker.tasks"],
)

# Configure Celery
celery_app.conf.update(
    # Task settings
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,

    # Time limits
    task_time_limit=settings.celery_task_time_limit,
    task_soft_time_limit=settings.celery_task_soft_time_limit,

    # Results
    result_expires=3600,  # Results expire after 1 hour
    result_extended=True,  # Include more info in results

    # Worker settings
    worker_prefetch_multiplier=1,  # Only prefetch 1 task at a time (OMR is heavy)
    worker_max_tasks_per_child=10,  # Restart worker after 10 tasks (prevent memory leaks)

    # Task tracking
    task_track_started=True,  # Track when tasks start
    task_acks_late=True,  # Only ack after task completes (prevents lost tasks)

    # Routing (optional, for future task separation)
    task_routes={
        "app.worker.tasks.process_omr_job": {"queue": "omr"},
        "app.worker.tasks.*": {"queue": "default"},
    },

    # Rate limiting
    task_annotations={
        "app.worker.tasks.process_omr_job": {
            "rate_limit": "10/m",  # Max 10 OMR jobs per minute
        },
    },
)


# Optional: Configure task failure handling
@celery_app.task(bind=True)
def debug_task(self):
    """Debug task for testing Celery connectivity."""
    return f"Request: {self.request!r}"
