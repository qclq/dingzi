import json
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from redis.asyncio import Redis
from redis.exceptions import RedisError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.health import get_redis
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.user import User
from app.repositories.analytics import distribution_rows, heatmap_rows, overview_rows
from app.schemas.analytics import (
    AnalyticsDistribution,
    AnalyticsDistributionItem,
    AnalyticsHeatmap,
    AnalyticsHeatmapCell,
    AnalyticsOverview,
    AnalyticsTrends,
)
from app.services.analytics import aggregate_range, safe_rate, trend_rows

router = APIRouter(prefix="/analytics", tags=["analytics"])
Period = Literal["today", "7d", "30d", "90d", "custom"]


def resolve_range(period: Period, start_time: datetime | None, end_time: datetime | None) -> tuple[datetime, datetime]:
    now = datetime.now(UTC)
    if period == "custom":
        if start_time is None or end_time is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="自定义范围需要 start_time 和 end_time")
        start, end = start_time, end_time
    elif period == "today":
        start, end = now.replace(hour=0, minute=0, second=0, microsecond=0), now
    else:
        days = int(period.removesuffix("d"))
        start, end = (now - timedelta(days=days - 1)).replace(hour=0, minute=0, second=0, microsecond=0), now
    if start.tzinfo is None:
        start = start.replace(tzinfo=UTC)
    if end.tzinfo is None:
        end = end.replace(tzinfo=UTC)
    if start > end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time 不能晚于 end_time")
    return start.astimezone(UTC), end.astimezone(UTC)


async def cached_response(redis: Redis, key: str, build):
    try:
        cached = await redis.get(key)
        if cached:
            return json.loads(cached)
        result = await build()
        await redis.set(key, json.dumps(result, ensure_ascii=False, default=str), ex=60)
        return result
    except RedisError:
        return await build()
    finally:
        await redis.aclose()


def cache_key(name: str, start: datetime, end: datetime, line_id: str | None) -> str:
    cached_start = start.replace(second=0, microsecond=0)
    cached_end = end.replace(second=0, microsecond=0)
    return f"analytics:{name}:{cached_start.isoformat()}:{cached_end.isoformat()}:{line_id or '*'}"


@router.get("/overview", response_model=AnalyticsOverview)
async def overview(
    period: Period = Query(default="today"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    line_id: str | None = Query(default=None, max_length=64),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AnalyticsOverview:
    start, end = resolve_range(period, start_time, end_time)

    async def build() -> dict:
        total, ng = await overview_rows(session, start, end, line_id)
        return AnalyticsOverview(total_detections=total, ng_detections=ng, defect_rate=safe_rate(ng, total), start=start, end=end).model_dump(mode="json")

    return AnalyticsOverview.model_validate(await cached_response(redis, cache_key("overview", start, end, line_id), build))


@router.get("/trends", response_model=AnalyticsTrends)
async def trends(
    period: Period = Query(default="7d"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    line_id: str | None = Query(default=None, max_length=64),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AnalyticsTrends:
    start, end = resolve_range(period, start_time, end_time)

    async def build() -> dict:
        rows = await aggregate_range(session, start, end, line_id)
        return AnalyticsTrends(granularity="day", start=start, end=end, items=trend_rows(rows, start, end)).model_dump(mode="json")

    return AnalyticsTrends.model_validate(await cached_response(redis, cache_key("trends", start, end, line_id), build))


@router.get("/defect-trend", response_model=AnalyticsTrends, deprecated=True)
async def defect_trend(
    period: Period = Query(default="7d"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    line_id: str | None = Query(default=None, max_length=64),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AnalyticsTrends:
    start, end = resolve_range(period, start_time, end_time)

    async def build() -> dict:
        rows = await aggregate_range(session, start, end, line_id)
        return AnalyticsTrends(granularity="day", start=start, end=end, items=trend_rows(rows, start, end)).model_dump(mode="json")

    return AnalyticsTrends.model_validate(await cached_response(redis, cache_key("trends", start, end, line_id), build))


@router.get("/defect-distribution", response_model=AnalyticsDistribution)
async def defect_distribution(
    period: Period = Query(default="7d"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    line_id: str | None = Query(default=None, max_length=64),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AnalyticsDistribution:
    start, end = resolve_range(period, start_time, end_time)

    async def build() -> dict:
        rows = await distribution_rows(session, start, end, line_id)
        total = sum(int(row["count"]) for row in rows)
        items = [AnalyticsDistributionItem(**row, percentage=safe_rate(int(row["count"]), total)) for row in rows]
        return AnalyticsDistribution(start=start, end=end, total_defects=total, items=items).model_dump(mode="json")

    return AnalyticsDistribution.model_validate(await cached_response(redis, cache_key("distribution", start, end, line_id), build))


@router.get("/heatmap", response_model=AnalyticsHeatmap)
async def heatmap(
    period: Period = Query(default="7d"),
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    line_id: str | None = Query(default=None, max_length=64),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> AnalyticsHeatmap:
    start, end = resolve_range(period, start_time, end_time)

    async def build() -> dict:
        cells = [AnalyticsHeatmapCell(angle_bucket=angle, axial_bucket=axial, count=count) for angle, axial, count in await heatmap_rows(session, start, end, line_id)]
        return AnalyticsHeatmap(start=start, end=end, items=cells).model_dump(mode="json")

    return AnalyticsHeatmap.model_validate(await cached_response(redis, cache_key("heatmap", start, end, line_id), build))
