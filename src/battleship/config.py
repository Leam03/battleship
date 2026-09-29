from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://battleship:local-development-only@localhost/battleship"
    )
    log_level: str = "INFO"
    db_pool_size: int = Field(default=20, ge=1)
    db_max_overflow: int = Field(default=10, ge=0)
    db_pool_timeout: float = Field(default=0.2, gt=0)
    db_connect_timeout: float = Field(default=0.5, gt=0)
    db_statement_timeout_ms: int = Field(default=500, gt=0)
    db_lock_timeout_ms: int = Field(default=200, gt=0)


@lru_cache
def get_settings() -> Settings:
    return Settings()
