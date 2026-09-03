from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class ConfigurationState(Base):
    """The single editable configuration draft and its published pointer."""

    __tablename__ = "configuration_state"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    draft_payload: Mapped[dict] = mapped_column(JSON, nullable=False)
    draft_revision: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    published_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    updated_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class ConfigVersion(Base):
    """Append-only, full configuration bundle published for a detection run."""

    __tablename__ = "config_versions"

    id: Mapped[int] = mapped_column(primary_key=True)
    version: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    payload_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    published_by: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)


class ConfigPublishKey(Base):
    __tablename__ = "config_publish_keys"

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    config_version: Mapped[str] = mapped_column(String(64), nullable=False)
