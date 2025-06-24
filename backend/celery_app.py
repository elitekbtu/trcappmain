from celery import Celery

from app.core.config import get_settings

settings = get_settings()

celery = Celery(
    "trcapp",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.REDIS_URL,
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
)
