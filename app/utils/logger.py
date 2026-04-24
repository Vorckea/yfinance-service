"""Logger configuration for the yfinance-service application."""

import contextvars
import json
import logging.config
from datetime import datetime, timezone

from ..settings import LogFormat, Settings

logger = logging.getLogger("yfinance-service")
_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "correlation_id", default=None
)
_STANDARD_RECORD_FIELDS = set(logging.makeLogRecord({}).__dict__) | {"message", "asctime"}


class RequestContextFilter(logging.Filter):
    """Attach request-scoped context to each log record."""

    def filter(self, record: logging.LogRecord) -> bool:
        correlation_id = _correlation_id.get()
        if not hasattr(record, "correlation_id"):
            record.correlation_id = correlation_id or "-"
        if not hasattr(record, "cid"):
            record.cid = record.correlation_id
        return True


class JsonFormatter(logging.Formatter):
    """Render logs as one-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        message = record.getMessage()
        payload = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": message,
            "correlation_id": getattr(record, "correlation_id", "-"),
            "module": record.module,
            "pathname": record.pathname,
            "lineno": record.lineno,
        }

        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_FIELDS and key not in payload:
                payload[key] = value

        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        if record.stack_info:
            payload["stack"] = self.formatStack(record.stack_info)

        return json.dumps(payload, default=str, ensure_ascii=True)


def set_correlation_id(correlation_id: str) -> contextvars.Token:
    """Store the active correlation ID for the current request context."""
    return _correlation_id.set(correlation_id)


def reset_correlation_id(token: contextvars.Token) -> None:
    """Restore the previous correlation ID for the current request context."""
    _correlation_id.reset(token)


def configure_logging(settings: Settings) -> None:
    """Configure root service logger using runtime settings."""
    level = settings.log_level.value
    formatter_name = "json" if settings.log_format == LogFormat.JSON else "default"

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": {
            "request_context": {
                "()": "app.utils.logger.RequestContextFilter",
            },
        },
        "formatters": {
            "default": {
                "format": (
                    "%(asctime)s %(levelname)s %(name)s %(message)s "
                    "[cid=%(correlation_id)s] [%(pathname)s:%(lineno)d]"
                ),
            },
            "json": {
                "()": "app.utils.logger.JsonFormatter",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "filters": ["request_context"],
                "formatter": formatter_name,
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
    }
    logging.config.dictConfig(cfg)
