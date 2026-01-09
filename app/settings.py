from enum import Enum

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

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

    log_level: LogLevel = Field(LogLevel.INFO, validation_alias="LOG_LEVEL")
    max_bulk_concurrency: int = Field(10, validation_alias="MAX_BULK_CONCURRENCY", ge=1)

    # Request timeout
    request_timeout: int = Field(30, validation_alias="REQUEST_TIMEOUT", ge=1)
    
    # Retry settings for yfinance fetch operations
    max_retries: int = Field(3, validation_alias="MAX_RETRIES", ge=0)
    retry_backoff_base: float = Field(1.0, validation_alias="RETRY_BACKOFF_BASE", gt=0)
    retry_backoff_max: float = Field(32.0, validation_alias="RETRY_BACKOFF_MAX", gt=0)
    
    # Earnings cache settings
    earnings_cache_ttl: int = Field(3600, validation_alias="EARNINGS_CACHE_TTL", ge=0)
    earnings_cache_maxsize: int = Field(128, validation_alias="EARNINGS_CACHE_MAXSIZE", ge=0)
    
    # Info cache settings
    info_cache_ttl: int = Field(300, validation_alias="INFO_CACHE_TTL", ge=0)
    info_cache_maxsize: int = Field(256, validation_alias="INFO_CACHE_MAXSIZE", ge=0)
    
    # Ticker cache settings
    ticker_cache_ttl: int = Field(60, validation_alias="TICKER_CACHE_TTL", ge=0)
    ticker_cache_maxsize: int = Field(512, validation_alias="TICKER_CACHE_MAXSIZE", ge=0)
    splits_cache_ttl: int = Field(3600, validation_alias="SPLITS_CACHE_TTL", ge=0)
    splits_cache_maxsize: int = Field(256, validation_alias="SPLITS_CACHE_MAXSIZE", ge=0)
    
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
    def _upper(cls, v: str) -> str:
        return v.upper()

@lru_cache
def get_settings() -> Settings:
    return Settings()