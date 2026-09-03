from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from kombu.exceptions import OperationalError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.export import ExportJob
from app.models.user import User
from app.schemas.history import ExportCreate, ExportResponse
from app.services.exports import (
    create_export_job,
    job_download_url,
    mark_export_dispatch_failed_sync,
)
from app.tasks.exports import generate_detection_export

router = APIRouter(prefix="/exports", tags=["exports"])


def dispatch_export(export_id: str) -> None:
    try:
        generate_detection_export.delay(export_id)
    except OperationalError:
        mark_export_dispatch_failed_sync(export_id)


def response(job: ExportJob) -> ExportResponse:
    return ExportResponse(
        id=job.id,
        format=job.format,
        status=job.status,
        record_count=job.record_count,
        created_at=job.created_at,
        completed_at=job.completed_at,
        expires_at=job.expires_at,
        download_url=job_download_url(job),
        error_message=job.error_message,
    )


@router.post("", response_model=ExportResponse, status_code=status.HTTP_202_ACCEPTED)
async def create_export(
    payload: ExportCreate,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExportResponse:
    if payload.start_time and payload.end_time and payload.start_time > payload.end_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time 不能晚于 end_time")
    job = create_export_job(session, user_id=user.id, payload=payload.model_dump())
    await session.commit()
    await session.refresh(job)
    background_tasks.add_task(dispatch_export, job.id)
    return response(job)


@router.get("/{export_id}", response_model=ExportResponse)
async def export_status(
    export_id: str,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> ExportResponse:
    job = await session.get(ExportJob, export_id)
    if job is None or (job.created_by_id != user.id and user.role != "admin"):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="导出任务不存在")
    return response(job)
