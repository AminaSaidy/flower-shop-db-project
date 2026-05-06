from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "flower_shop",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=["app.worker.tasks"],
)

celery_app.conf.beat_schedule = {
    "daily-sales-report": {
        "task": "app.worker.tasks.daily_sales_report",
        "schedule": crontab(hour=23, minute=0),
    },
    "low-stock-alert": {
        "task": "app.worker.tasks.low_stock_alert",
        "schedule": crontab(minute="*/30"),
    },
}
celery_app.conf.timezone = "Asia/Tashkent"