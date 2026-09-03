from celery import Celery
from celery.schedules import crontab

from app.core.config import get_settings

celery_app = Celery("dingzi", broker=get_settings().redis_url, backend=get_settings().redis_url)
celery_app.conf.update(
    imports=("app.tasks.analytics", "app.tasks.exports", "app.tasks.mes", "app.tasks.maintenance"),
    task_publish_retry=False,
    broker_connection_timeout=1,
    broker_transport_options={"max_retries": 0, "socket_connect_timeout": 1},
)
celery_app.conf.beat_schedule = {
    "phase7-file-cleanup": {"task": "maintenance.cleanup_files", "schedule": crontab(hour=2, minute=0)},
    "phase7-log-cleanup": {"task": "maintenance.cleanup_logs", "schedule": crontab(hour=2, minute=0)},
}
celery_app.conf.timezone = "Asia/Shanghai"
