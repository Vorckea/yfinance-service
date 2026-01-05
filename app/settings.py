from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        validate_default=True,
        frozen=True,
    )

    log_level: LogLevel = Field(LogLevel.INFO, env="LOG_LEVEL")
    max_bulk_concurrency: int = Field(10, env="MAX_BULK_CONCURRENCY", ge=1)
    earnings_cache_ttl: int = Field(3600, env="EARNINGS_CACHE_TTL", ge=0)
    earnings_cache_maxsize: int = Field(128, env="EARNINGS_CACHE_MAXSIZE", ge=0)
    info_cache_ttl: int = Field(300, env="INFO_CACHE_TTL", ge=0)
    info_cache_maxsize: int = Field(256, env="INFO_CACHE_MAXSIZE", ge=0)
    splits_cache_ttl: int = Field(3600, env="SPLITS_CACHE_TTL", ge=0)

    # CORS (Opt-in)
    cors_enabled: bool = Field(False, env="CORS_ENABLED")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        env="CORS_ALLOWED_ORIGINS",
    )

    @field_validator("log_level", mode="before")
    def _upper(cls, v: str) -> str:
        return v.upper()
