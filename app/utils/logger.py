"""Logger configuration for the yfinance-service application."""

import logging

from ..settings import get_settings

settings = get_settings()

logger = logging.getLogger("yfinance-service")
log_level = settings.log_level
logger.setLevel(getattr(logging, log_level, logging.INFO))

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s [%(pathname)s:%(lineno)d]"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
