from celery import Celery
from celery.schedules import crontab
from dependencies import get_settings


settings = get_settings()

celery_app = Celery(main="online_movie", broker=settings.REDIS_URL, backend=settings.REDIS_URL)
celery_app.autodiscover_tasks(packages=["tasks"])

celery_app.conf.beat_schedule = {
    "cleanup_expired_tokens_every_24_hours": {
        "task": "src.tasks.cleanup_task.cleanup_expired_tokens",
        "schedule": crontab(minute=59, hour=23),
    }
}
