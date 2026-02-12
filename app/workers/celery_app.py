"""Celery application configuration."""
from celery import Celery
from app.core.config import settings

# Create Celery app
celery_app = Celery(
    "clippod",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.workers.tasks"]
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    task_routes={
        "app.workers.tasks.process_video_task": {"queue": "processing"},
        "app.workers.tasks.render_clip_task": {"queue": "rendering"},
        "app.workers.tasks.transcribe_video_task": {"queue": "transcription"},
        "app.workers.tasks.analyze_video_task": {"queue": "analysis"},
    },
    # Result backend settings
    result_expires=3600 * 24,  # 24 hours
    result_extended=True,
)

# Beat schedule for periodic tasks
celery_app.conf.beat_schedule = {
    "cleanup-old-tasks": {
        "task": "app.workers.tasks.cleanup_old_tasks",
        "schedule": 3600 * 24,  # Daily
    },
}


def get_celery_app():
    """Get Celery app instance."""
    return celery_app
