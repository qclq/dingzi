from datetime import datetime

from sqlalchemy import DateTime, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AnalyticsHourlyAggregate(Base):
    __tablename__ = "analytics_hourly_aggregates"
    __table_args__ = (UniqueConstraint("bucket_start", "line_id", name="uq_analytics_hour_line"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    line_id: Mapped[str] = mapped_column(String(64), index=True)
    total_detections: Mapped[int] = mapped_column(Integer, default=0)
    ng_detections: Mapped[int] = mapped_column(Integer, default=0)
    scratch_count: Mapped[int] = mapped_column(Integer, default=0)
    pitted_surface_count: Mapped[int] = mapped_column(Integer, default=0)
    scratch_minor_count: Mapped[int] = mapped_column(Integer, default=0)
    scratch_severe_count: Mapped[int] = mapped_column(Integer, default=0)
    pitted_surface_minor_count: Mapped[int] = mapped_column(Integer, default=0)
    pitted_surface_severe_count: Mapped[int] = mapped_column(Integer, default=0)


class AnalyticsHeatmapHourlyBucket(Base):
    __tablename__ = "analytics_heatmap_hourly_buckets"
    __table_args__ = (
        UniqueConstraint("bucket_start", "line_id", "angle_bucket", "axial_bucket", name="uq_heatmap_hour_cell"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    line_id: Mapped[str] = mapped_column(String(64), index=True)
    angle_bucket: Mapped[int] = mapped_column(Integer)
    axial_bucket: Mapped[int] = mapped_column(Integer)
    defect_count: Mapped[int] = mapped_column(Integer, default=0)
