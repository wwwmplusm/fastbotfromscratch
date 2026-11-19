from functools import lru_cache
from zoneinfo import ZoneInfo

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    bot_token: str = ""
    database_url: str = "postgresql+asyncpg://fastbot:fastbot@localhost:5432/fastbot"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    openai_json_mode: bool = True
    openai_timeout_seconds: float = 45
    default_timezone: str = "Europe/Moscow"
    log_level: str = "INFO"
    max_image_bytes: int = 8 * 1024 * 1024
    health_host: str = "0.0.0.0"
    health_port: int = 8080

    @field_validator("default_timezone")
    @classmethod
    def timezone_must_exist(cls, value: str) -> str:
        ZoneInfo(value)
        return value

    @field_validator("openai_base_url")
    @classmethod
    def strip_base_url(cls, value: str) -> str:
        return value.rstrip("/")


@lru_cache
def get_settings() -> Settings:
    return Settings()
