from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.detection import DefectResponse

ExportFormat = Literal["xlsx", "pdf"]
ExportStatus = Literal["queued", "running", "completed", "failed"]


class DetectionListItem(BaseModel):
    id: int
    image_id: str
    captured_at: datetime
    operator: str
    defect_count: int
    result: Literal["PASS", "NG"]


class DetectionPage(BaseModel):
    items: list[DetectionListItem]
    total: int
    page: int
    page_size: int


class DetectionDetail(BaseModel):
    id: int
    image_id: str
    line_id: str
    captured_at: datetime
    operator: str
    defects: list[DefectResponse]
    result: Literal["PASS", "NG"]
    image_path: str
    thumbnail_path: str | None
    model_version: str
    config_version: str
    config_snapshot: dict | None
    inference_ms: float
    mes_status: str
    mes_work_order: str | None
    raw_output: dict | None


class SignedFileResponse(BaseModel):
    kind: Literal["image", "thumbnail", "json"]
    url: str
    expires_at: datetime


class ExportCreate(BaseModel):
    format: ExportFormat
    detection_ids: list[int] = Field(default_factory=list, max_length=10_000)
    start_time: datetime | None = None
    end_time: datetime | None = None
    result: Literal["PASS", "NG"] | None = None
    operator: str | None = Field(default=None, max_length=64)
    image_id: str | None = Field(default=None, max_length=128)
    line_id: str | None = Field(default=None, max_length=64)


class MesWorkOrderUpdate(BaseModel):
    mes_work_order: str = Field(min_length=1, max_length=128)


class ExportResponse(BaseModel):
    id: str
    format: ExportFormat
    status: ExportStatus
    record_count: int
    created_at: datetime
    completed_at: datetime | None
    expires_at: datetime | None
    download_url: str | None = None
    error_message: str | None = None
