from datetime import datetime

from pydantic import BaseModel


class DefectResponse(BaseModel):
    type: str
    level: str
    confidence: float
    bbox: list[float]
    width_mm: float | None = None
    height_mm: float | None = None


class DetectionResponse(BaseModel):
    image_id: str
    line_id: str
    captured_at: datetime
    operator: str
    defects: list[DefectResponse]
    result: str
    image_path: str
    thumbnail_path: str | None
    model_version: str
    config_version: str
    config_snapshot: dict | None = None
    inference_ms: float
    mes_status: str


class SnapshotResponse(BaseModel):
    line_id: str
    latest: DetectionResponse | None
    events: dict
