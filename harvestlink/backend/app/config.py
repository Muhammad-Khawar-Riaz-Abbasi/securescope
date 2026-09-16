from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_name: str = "HarvestLink API"
    environment: str = "development"
    database_url: str = "sqlite+aiosqlite:///./harvestlink.db"
    cors_origins: str = "http://localhost:5173,http://localhost:4173"
    api_key: str | None = None
    seed_demo: bool = True
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

@lru_cache
def get_settings() -> Settings:
    return Settings()
