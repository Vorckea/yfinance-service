"""Logger configuration for the yfinance-service application."""

import logging.config

from ..settings import Settings

logger = logging.getLogger("yfinance-service")


def configure_logging(settings: Settings) -> None:
    """Configure root service logger using runtime settings."""
    level = settings.log_level

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "default": {
                "format": "%(asctime)s %(levelname)s %(name)s %(message)s [%(pathname)s:%(lineno)d]",
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "formatter": "default",
                "level": level,
            },
        },
        "root": {
            "handlers": ["console"],
            "level": level,
        },
    }
    logging.config.dictConfig(cfg)
