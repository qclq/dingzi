from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

Role = Literal["admin", "operator"]
UserStatus = Literal["active", "disabled"]
LogLevel = Literal["INFO", "WARNING", "ERROR"]


class ManagedUser(BaseModel):
    id: int; username: str; display_name: str; email: str | None; role: Role; status: UserStatus
    last_login: datetime | None; locked_until: datetime | None; revision: int; created_at: datetime


class UserPage(BaseModel):
    items: list[ManagedUser]; total: int; page: int; page_size: int


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=20); password: str = Field(min_length=8, max_length=128)
    display_name: str = Field(min_length=1, max_length=128); email: str | None = Field(default=None, max_length=255); role: Role = "operator"


class UserUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=128)
    email: str | None = Field(default=None, max_length=255); role: Role | None = None; status: UserStatus | None = None; revision: int = Field(ge=1)


class StatusUpdate(BaseModel):
    status: UserStatus


class BatchStatusUpdate(StatusUpdate):
    user_ids: list[int] = Field(min_length=1, max_length=100)


class LogItem(BaseModel):
    id: int; level: LogLevel; source: str; message: str | None; actor_id: int | None = None
    action: str | None = None; resource: str | None = None; ip_address: str | None = None; created_at: datetime


class LogPage(BaseModel):
    items: list[LogItem]; total: int; page: int; page_size: int


class MesConfig(BaseModel):
    mes_url: HttpUrl | None = None; auto_report: bool = False; revision: int = 1; token_configured: bool = False


class MesConfigUpdate(BaseModel):
    mes_url: HttpUrl | None = None; auth_token: str | None = Field(default=None, max_length=2048)
    auto_report: bool; revision: int = Field(ge=1)


class MesTestRequest(BaseModel):
    mes_url: HttpUrl | None = None; auth_token: str | None = Field(default=None, max_length=2048)


class MesTestResult(BaseModel):
    connected: bool; http_status: int | None; response_time_ms: int; error_message: str | None = None


class MesDeliveryView(BaseModel):
    id: int; detection_id: int; status: str; attempts: int; last_status_code: int | None; last_error: str | None; created_at: datetime


class FilePolicy(BaseModel):
    retention_days: int = Field(ge=21, le=3650); quota_gb: float | None = Field(default=None, gt=0)
    warning_percent: int = Field(default=80, ge=1, le=99); revision: int = 1


class FilePolicyUpdate(FilePolicy):
    pass


class FileUsage(BaseModel):
    used_bytes: int; quota_bytes: int | None; percent: float | None; file_count: int
