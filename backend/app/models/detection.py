from datetime import datetime

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Detection(Base):
    __tablename__ = "detections"

    id: Mapped[int] = mapped_column(primary_key=True)
    image_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    line_id: Mapped[str] = mapped_column(String(64), index=True, default="line-1")
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    operator: Mapped[str] = mapped_column(String(64), default="mock-operator")
    result: Mapped[str] = mapped_column(String(8), index=True)
    image_path: Mapped[str] = mapped_column(String(512))
    thumbnail_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    model_version: Mapped[str] = mapped_column(String(64), default="mock-v1")
    config_version: Mapped[str] = mapped_column(String(64), default="default-v1")
    config_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    inference_ms: Mapped[float] = mapped_column(Float, default=0)
    mes_status: Mapped[str] = mapped_column(String(32), default="not_sent")
    mes_work_order: Mapped[str | None] = mapped_column(String(128), nullable=True)
    defect_count: Mapped[int] = mapped_column(Integer, default=0)
    raw_output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    defects: Mapped[list["Defect"]] = relationship(back_populates="detection", cascade="all, delete-orphan")


class Defect(Base):
    __tablename__ = "defects"

    id: Mapped[int] = mapped_column(primary_key=True)
    detection_id: Mapped[int] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), index=True)
    type: Mapped[str] = mapped_column(String(32))
    level: Mapped[str] = mapped_column(String(16))
    confidence: Mapped[float] = mapped_column(Float)
    bbox: Mapped[list[float]] = mapped_column(JSON)
    width_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    height_mm: Mapped[float | None] = mapped_column(Float, nullable=True)
    detection: Mapped[Detection] = relationship(back_populates="defects")
