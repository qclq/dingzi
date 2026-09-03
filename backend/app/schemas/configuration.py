from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class ConfigTypeUpdate(BaseModel):
    value: dict[str, Any]
    draft_revision: int = Field(ge=1)


class PublishRequest(BaseModel):
    draft_revision: int = Field(ge=1)


class ConfigDraftResponse(BaseModel):
    config_type: str
    value: dict[str, Any]
    draft_revision: int
    published_version: str | None


class ConfigValidationResponse(BaseModel):
    valid: bool
    errors: list[str]
    draft_revision: int


class ConfigVersionResponse(BaseModel):
    version: str
    payload: dict[str, Any]
    published_at: datetime
    published_by: int | None


class ConfigSummaryResponse(BaseModel):
    draft_revision: int
    published_version: str | None
    config_types: list[str]
