from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsHeatmapHourlyBucket
from app.services.analytics import aggregate_range


async def overview_rows(
    session: AsyncSession, start: datetime, end: datetime, line_id: str | None = None
) -> tuple[int, int]:
    rows = await aggregate_range(session, start, end, line_id)
    return sum(item.total_detections for item in rows), sum(item.ng_detections for item in rows)


async def distribution_rows(
    session: AsyncSession, start: datetime, end: datetime, line_id: str | None = None
) -> list[dict[str, int | str]]:
    rows = await aggregate_range(session, start, end, line_id)
    fields = (
        ("scratch", "minor", "scratch_minor_count"),
        ("scratch", "severe", "scratch_severe_count"),
        ("pitted_surface", "minor", "pitted_surface_minor_count"),
        ("pitted_surface", "severe", "pitted_surface_severe_count"),
    )
    return [{"type": kind, "level": level, "count": sum(getattr(row, field) for row in rows)} for kind, level, field in fields]


async def heatmap_rows(
    session: AsyncSession, start: datetime, end: datetime, line_id: str | None = None
) -> list[tuple[int, int, int]]:
    statement = select(
        AnalyticsHeatmapHourlyBucket.angle_bucket,
        AnalyticsHeatmapHourlyBucket.axial_bucket,
        func.sum(AnalyticsHeatmapHourlyBucket.defect_count),
    ).where(
        AnalyticsHeatmapHourlyBucket.bucket_start >= start,
        AnalyticsHeatmapHourlyBucket.bucket_start <= end,
    )
    if line_id:
        statement = statement.where(AnalyticsHeatmapHourlyBucket.line_id == line_id)
    statement = statement.group_by(
        AnalyticsHeatmapHourlyBucket.angle_bucket, AnalyticsHeatmapHourlyBucket.axial_bucket
    )
    return [(int(angle), int(axial), int(count)) for angle, axial, count in (await session.execute(statement)).all()]
