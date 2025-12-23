from functools import lru_cache

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=True,
        validate_default=True,
        frozen=True,
    )

    log_level: str = Field("INFO", env="LOG_LEVEL")
    max_bulk_concurrency: int = Field(10, env="MAX_BULK_CONCURRENCY")
    earnings_cache_ttl: int = Field(3600, env="EARNINGS_CACHE_TTL")
    earnings_cache_maxsize: int = Field(128, env="EARNINGS_CACHE_MAXSIZE")
    info_cache_ttl: int = Field(300, env="INFO_CACHE_TTL")
    info_cache_maxsize: int = Field(256, env="INFO_CACHE_MAXSIZE")

    @field_validator("log_level", mode="before")
    def _upper(cls, v: str) -> str:
        return v.upper()

    @field_validator("max_bulk_concurrency", mode="before")
    def _positive(cls, v: int) -> int:
        return max(1, v)

    @field_validator("log_level")
    def validate_log_level(cls, v: str) -> str:
        valid_levels = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}
        if v not in valid_levels:
            raise ValueError(f"Invalid LOG_LEVEL: {v}. Must be one of {valid_levels}.")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
