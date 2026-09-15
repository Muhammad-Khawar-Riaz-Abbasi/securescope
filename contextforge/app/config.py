from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "development"
    database_url: str = "sqlite+aiosqlite:///./contextforge.db"
    redis_url: str = "redis://localhost:6379/0"
    api_key: str | None = None
    auth_required: bool = False
    cors_origins: list[str] = ["http://localhost:3000"]
    max_document_bytes: int = 1_048_576

    model_config = SettingsConfigDict(env_file=".env", env_prefix="", extra="ignore")

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("max_document_bytes")
    @classmethod
    def validate_document_limit(cls, value: int) -> int:
        if not 1 <= value <= 50 * 1024 * 1024:
            raise ValueError("max_document_bytes must be between 1 and 52428800")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
