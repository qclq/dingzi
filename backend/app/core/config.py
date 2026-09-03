from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "dingzi-web-api"
    app_env: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    database_url: str = "mysql+aiomysql://dingzi:dingzi@localhost:3306/dingzi"
    redis_url: str = "redis://localhost:6379/0"
    export_directory: str = "/data/exports"
    file_download_base_url: str = "http://localhost:9000/dingzi-files"
    download_url_ttl_seconds: int = 300
    jwt_secret_key: str = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 480
    refresh_token_expire_days: int = 7
    backend_cors_origins: str = "http://localhost:5173"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    @field_validator("jwt_secret_key")
    @classmethod
    def validate_jwt_secret_key(cls, value: str) -> str:
        normalized = value.strip().lower()
        if len(value.encode("utf-8")) < 32:
            raise ValueError("JWT_SECRET_KEY must contain at least 32 bytes")
        if any(marker in normalized for marker in ("change-me", "replace-with", "your-secret")):
            raise ValueError("JWT_SECRET_KEY must not use a placeholder value")
        return value

    @property
    def cors_origins(self) -> list[str]:
        return [origin.strip() for origin in self.backend_cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
