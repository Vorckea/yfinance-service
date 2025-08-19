import logging
import os

logger = logging.getLogger("yfinance-service")
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logger.setLevel(getattr(logging, log_level, logging.INFO))

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s [%(pathname)s:%(lineno)d]"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
