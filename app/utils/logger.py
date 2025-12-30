"""Logger configuration for the yfinance-service application."""

import logging
from typing import Any

from ..settings import Settings

logger = logging.getLogger("yfinance-service")


def configure_logging(settings: Settings | Any) -> None:
    """Configure root service logger using runtime settings."""
    log_level = getattr(settings, "log_level", "INFO")
    logger.setLevel(getattr(logging, log_level, logging.INFO))

    if not logger.hasHandlers():
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s [%(pathname)s:%(lineno)d]"
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
