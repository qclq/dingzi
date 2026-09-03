from datetime import datetime

from pydantic import BaseModel, Field


class AnalyticsOverview(BaseModel):
    total_detections: int
    ng_detections: int
    defect_rate: float = Field(description="NG detection count divided by total detection count, as a percentage")
    rate_definition: str = "NG 检测记录数 / 检测总数 × 100"
    start: datetime
    end: datetime


class AnalyticsTrendItem(BaseModel):
    bucket_start: datetime
    total_detections: int
    ng_detections: int
    defect_rate: float
    scratch_count: int
    pitted_surface_count: int


class AnalyticsTrends(BaseModel):
    granularity: str
    start: datetime
    end: datetime
    items: list[AnalyticsTrendItem]


class AnalyticsDistributionItem(BaseModel):
    type: str
    level: str
    count: int
    percentage: float


class AnalyticsDistribution(BaseModel):
    start: datetime
    end: datetime
    total_defects: int
    items: list[AnalyticsDistributionItem]


class AnalyticsHeatmapCell(BaseModel):
    angle_bucket: int
    axial_bucket: int
    count: int


class AnalyticsHeatmap(BaseModel):
    start: datetime
    end: datetime
    angle_bin_degrees: int = 10
    axial_bin_count: int = 10
    coordinate_basis: str = "normalized_bbox_center"
    items: list[AnalyticsHeatmapCell]
