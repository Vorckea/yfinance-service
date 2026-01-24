"""Application settings module."""

from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class LogLevel(str, Enum):
    """Logging levels."""

    CRITICAL = "CRITICAL"
    ERROR = "ERROR"
    WARNING = "WARNING"
    INFO = "INFO"
    DEBUG = "DEBUG"
    NOTSET = "NOTSET"


class Settings(BaseSettings):
    """Application settings loaded from environment variables or a .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        validate_default=True,
        validate_by_name=True,
        frozen=True,
    )

    log_level: LogLevel = Field(LogLevel.INFO, validation_alias="LOG_LEVEL")
    max_bulk_concurrency: int = Field(10, ge=1, validation_alias="MAX_BULK_CONCURRENCY")

    # Request timeout
    request_timeout: int = Field(30, ge=1, validation_alias="REQUEST_TIMEOUT")

    # Retry settings for yfinance fetch operations
    max_retries: int = Field(3, ge=0, validation_alias="MAX_RETRIES")
    retry_backoff_base: float = Field(1.0, gt=0, validation_alias="RETRY_BACKOFF_BASE")
    retry_backoff_max: float = Field(32.0, gt=0, validation_alias="RETRY_BACKOFF_MAX")

    # Earnings cache settings
    earnings_cache_ttl: int = Field(3600, ge=0, validation_alias="EARNINGS_CACHE_TTL")
    earnings_cache_maxsize: int = Field(128, ge=0, validation_alias="EARNINGS_CACHE_MAXSIZE")

    # Info cache settings
    info_cache_ttl: int = Field(300, ge=0, validation_alias="INFO_CACHE_TTL")
    info_cache_maxsize: int = Field(256, ge=0, validation_alias="INFO_CACHE_MAXSIZE")

    # Ticker cache settings
    ticker_cache_ttl: int = Field(60, ge=0, validation_alias="TICKER_CACHE_TTL")
    ticker_cache_maxsize: int = Field(512, ge=0, validation_alias="TICKER_CACHE_MAXSIZE")
    splits_cache_ttl: int = Field(3600, ge=0, validation_alias="SPLITS_CACHE_TTL")
    splits_cache_maxsize: int = Field(256, ge=0, validation_alias="SPLITS_CACHE_MAXSIZE")

    # News endpoint settings
    news_max_items: int = Field(100, ge=1, validation_alias="NEWS_MAX_ITEMS")

    # CORS (Opt-in)
    cors_enabled: bool = Field(False, validation_alias="CORS_ENABLED")
    cors_allowed_origins: list[str] = Field(
        default_factory=lambda: ["*"],
        validation_alias="CORS_ALLOWED_ORIGINS",
    )

    # API Key Authentication (Opt-in)
    api_key_enabled: bool = Field(False, validation_alias="API_KEY_ENABLED")
    api_key: str = Field("", validation_alias="API_KEY")

    @field_validator("log_level", mode="before")
    @classmethod
    def _upper(cls, v: str) -> str:
        return v.upper()
