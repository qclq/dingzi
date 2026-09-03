import asyncio

from sqlalchemy import delete, select
from sqlalchemy.orm import selectinload

from app.db.session import SessionLocal
from app.models.analytics import AnalyticsHeatmapHourlyBucket, AnalyticsHourlyAggregate
from app.models.detection import Detection
from app.services.analytics import record_detection_analytics
from app.tasks import celery_app


async def rebuild_analytics() -> None:
    async with SessionLocal() as session:
        await session.execute(delete(AnalyticsHeatmapHourlyBucket))
        await session.execute(delete(AnalyticsHourlyAggregate))
        detections = await session.scalars(select(Detection).options(selectinload(Detection.defects)))
        for detection in detections:
            await record_detection_analytics(session, detection)
        await session.commit()


@celery_app.task(name="analytics.rebuild")
def rebuild_analytics_task() -> None:
    asyncio.run(rebuild_analytics())
