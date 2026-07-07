from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SRM_", env_file=".env", extra="ignore")

    environment: Literal["local", "test", "production"] = "local"
    log_level: str = "INFO"
    log_json: bool = True
    api_v1_prefix: str = "/api/v1"
    database_url: str = "postgresql+asyncpg://srm:srm@localhost:5432/srm_credit"
    db_echo: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
