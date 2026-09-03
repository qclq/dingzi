from app.services.exports import run_export_sync
from app.tasks import celery_app


@celery_app.task(name="exports.generate")
def generate_detection_export(export_id: str) -> None:
    run_export_sync(export_id)
