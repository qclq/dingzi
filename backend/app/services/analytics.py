from collections import defaultdict
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.analytics import AnalyticsHeatmapHourlyBucket, AnalyticsHourlyAggregate
from app.models.detection import Detection

ANGLE_BUCKETS = 36
AXIAL_BUCKETS = 10


def hour_start(value: datetime) -> datetime:
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.astimezone(UTC).replace(minute=0, second=0, microsecond=0)


def safe_rate(numerator: int, denominator: int) -> float:
    return round(numerator * 100 / denominator, 2) if denominator else 0.0


def heatmap_cell(bbox: list[float]) -> tuple[int, int]:
    x, y, width, height = (float(value) for value in bbox[:4])
    center_x = min(max(x + width / 2, 0.0), 0.999999)
    center_y = min(max(y + height / 2, 0.0), 0.999999)
    return int(center_x * ANGLE_BUCKETS), int(center_y * AXIAL_BUCKETS)


async def record_detection_analytics(session: AsyncSession, detection: Detection) -> None:
    bucket = hour_start(detection.captured_at)
    aggregate = await session.scalar(
        select(AnalyticsHourlyAggregate)
        .where(AnalyticsHourlyAggregate.bucket_start == bucket, AnalyticsHourlyAggregate.line_id == detection.line_id)
        .with_for_update()
    )
    if aggregate is None:
        aggregate = AnalyticsHourlyAggregate(bucket_start=bucket, line_id=detection.line_id)
        session.add(aggregate)
    aggregate.total_detections = (aggregate.total_detections or 0) + 1
    aggregate.ng_detections = (aggregate.ng_detections or 0) + int(detection.result == "NG")
    for defect in detection.defects:
        if defect.type == "scratch":
            aggregate.scratch_count = (aggregate.scratch_count or 0) + 1
            if defect.level == "minor":
                aggregate.scratch_minor_count = (aggregate.scratch_minor_count or 0) + 1
            else:
                aggregate.scratch_severe_count = (aggregate.scratch_severe_count or 0) + 1
        elif defect.type == "pitted_surface":
            aggregate.pitted_surface_count = (aggregate.pitted_surface_count or 0) + 1
            if defect.level == "minor":
                aggregate.pitted_surface_minor_count = (aggregate.pitted_surface_minor_count or 0) + 1
            else:
                aggregate.pitted_surface_severe_count = (aggregate.pitted_surface_severe_count or 0) + 1
        angle_bucket, axial_bucket = heatmap_cell(defect.bbox)
        cell = await session.scalar(
            select(AnalyticsHeatmapHourlyBucket)
            .where(
                AnalyticsHeatmapHourlyBucket.bucket_start == bucket,
                AnalyticsHeatmapHourlyBucket.line_id == detection.line_id,
                AnalyticsHeatmapHourlyBucket.angle_bucket == angle_bucket,
                AnalyticsHeatmapHourlyBucket.axial_bucket == axial_bucket,
            )
            .with_for_update()
        )
        if cell is None:
            cell = AnalyticsHeatmapHourlyBucket(
                bucket_start=bucket,
                line_id=detection.line_id,
                angle_bucket=angle_bucket,
                axial_bucket=axial_bucket,
            )
            session.add(cell)
        cell.defect_count = (cell.defect_count or 0) + 1


async def aggregate_range(
    session: AsyncSession, start: datetime, end: datetime, line_id: str | None = None
) -> list[AnalyticsHourlyAggregate]:
    statement = select(AnalyticsHourlyAggregate).where(
        AnalyticsHourlyAggregate.bucket_start >= hour_start(start),
        AnalyticsHourlyAggregate.bucket_start <= hour_start(end),
    )
    if line_id:
        statement = statement.where(AnalyticsHourlyAggregate.line_id == line_id)
    return list((await session.scalars(statement)).all())


def trend_rows(rows: list[AnalyticsHourlyAggregate], start: datetime, end: datetime) -> list[dict]:
    buckets: dict[datetime, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        item = buckets[hour_start(row.bucket_start).replace(hour=0)]
        for field in (
            "total_detections", "ng_detections", "scratch_count", "pitted_surface_count",
        ):
            item[field] += getattr(row, field)
    result = []
    cursor = hour_start(start).replace(hour=0)
    last = hour_start(end).replace(hour=0)
    while cursor <= last:
        item = buckets[cursor]
        values = {
            "total_detections": item["total_detections"],
            "ng_detections": item["ng_detections"],
            "scratch_count": item["scratch_count"],
            "pitted_surface_count": item["pitted_surface_count"],
        }
        result.append(
            {
                "bucket_start": cursor,
                **values,
                "defect_rate": safe_rate(values["ng_detections"], values["total_detections"]),
            }
        )
        cursor += timedelta(days=1)
    return result
