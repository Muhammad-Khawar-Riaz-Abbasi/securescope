from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "TrustLedger"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./trustledger.db"
    cors_origins: str = "http://localhost:5173"
    api_key: str | None = None
    max_upload_bytes: int = 2_000_000
    request_id_header: str = "X-Request-ID"
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def allowed_origins(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
