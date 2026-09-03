from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.detection import Detection


def filtered_detections(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    result: str | None = None,
    operator: str | None = None,
    image_id: str | None = None,
    line_id: str | None = None,
) -> Select[tuple[Detection]]:
    statement = select(Detection)
    if start_time is not None:
        statement = statement.where(Detection.captured_at >= start_time)
    if end_time is not None:
        statement = statement.where(Detection.captured_at <= end_time)
    if result is not None:
        statement = statement.where(Detection.result == result)
    if operator is not None:
        statement = statement.where(Detection.operator == operator)
    if image_id is not None:
        statement = statement.where(Detection.image_id == image_id)
    if line_id is not None:
        statement = statement.where(Detection.line_id == line_id)
    return statement


async def list_detections(
    session: AsyncSession,
    *,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    result: str | None = None,
    operator: str | None = None,
    image_id: str | None = None,
    line_id: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Detection], int]:
    filtered = filtered_detections(start_time, end_time, result, operator, image_id, line_id)
    total = await session.scalar(select(func.count()).select_from(filtered.subquery()))
    records = await session.scalars(
        filtered.order_by(Detection.captured_at.desc(), Detection.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(records), int(total or 0)


async def get_detection(session: AsyncSession, detection_id: int) -> Detection | None:
    result = await session.scalars(
        select(Detection)
        .options(selectinload(Detection.defects))
        .where(Detection.id == detection_id)
    )
    return result.one_or_none()
