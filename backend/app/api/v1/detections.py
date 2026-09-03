from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.deps import get_current_user
from app.db.session import get_db
from app.models.detection import Detection
from app.models.user import User
from app.repositories.detection import get_detection, list_detections
from app.schemas.history import (
    DetectionDetail,
    DetectionListItem,
    DetectionPage,
    MesWorkOrderUpdate,
    SignedFileResponse,
)
from app.services.files import presign_download

router = APIRouter(prefix="/detections", tags=["detections"])


def detail_response(detection: Detection) -> DetectionDetail:
    return DetectionDetail(
        id=detection.id,
        image_id=detection.image_id,
        line_id=detection.line_id,
        captured_at=detection.captured_at,
        operator=detection.operator,
        defects=[
            {
                "type": defect.type,
                "level": defect.level,
                "confidence": defect.confidence,
                "bbox": defect.bbox,
                "width_mm": defect.width_mm,
                "height_mm": defect.height_mm,
            }
            for defect in detection.defects
        ],
        result=detection.result,
        image_path=detection.image_path,
        thumbnail_path=detection.thumbnail_path,
        model_version=detection.model_version,
        config_version=detection.config_version,
        config_snapshot=detection.config_snapshot,
        inference_ms=detection.inference_ms,
        mes_status=detection.mes_status,
        mes_work_order=detection.mes_work_order,
        raw_output=detection.raw_output,
    )


@router.get("", response_model=DetectionPage)
async def detection_list(
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    result: Literal["PASS", "NG"] | None = None,
    operator: str | None = Query(default=None, max_length=64),
    image_id: str | None = Query(default=None, max_length=128),
    line_id: str | None = Query(default=None, max_length=64),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DetectionPage:
    if start_time and end_time and start_time > end_time:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start_time 不能晚于 end_time")
    if page_size not in {20, 50, 100}:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="page_size 仅支持 20、50、100")
    records, total = await list_detections(
        session,
        start_time=start_time,
        end_time=end_time,
        result=result,
        operator=operator,
        image_id=image_id,
        line_id=line_id,
        page=page,
        page_size=page_size,
    )
    return DetectionPage(
        items=[
            DetectionListItem(
                id=item.id,
                image_id=item.image_id,
                captured_at=item.captured_at,
                operator=item.operator,
                defect_count=item.defect_count,
                result=item.result,
            )
            for item in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{detection_id}", response_model=DetectionDetail)
async def detection_detail(
    detection_id: int,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DetectionDetail:
    detection = await get_detection(session, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测记录不存在")
    return detail_response(detection)


@router.patch("/{detection_id}/mes-work-order", response_model=DetectionDetail)
async def link_mes_work_order(
    detection_id: int,
    payload: MesWorkOrderUpdate,
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> DetectionDetail:
    detection = await get_detection(session, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测记录不存在")
    detection.mes_work_order = payload.mes_work_order.strip()
    await session.commit()
    return detail_response(detection)


@router.get("/{detection_id}/files/{kind}", response_model=SignedFileResponse)
async def detection_file_url(
    detection_id: int,
    kind: Literal["image", "thumbnail", "json"],
    settings: Settings = Depends(get_settings),
    _: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
) -> SignedFileResponse:
    detection = await get_detection(session, detection_id)
    if detection is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="检测记录不存在")
    if kind == "image":
        file_path = detection.image_path
    elif kind == "thumbnail":
        file_path = detection.thumbnail_path
    else:
        # Raw JSON is exported as an object by the storage adapter in production.
        file_path = f"detections/{detection.id}/inference.json"
    if not file_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="该文件不可用")
    url, expires_at = presign_download(settings, file_path)
    return SignedFileResponse(kind=kind, url=url, expires_at=expires_at)
