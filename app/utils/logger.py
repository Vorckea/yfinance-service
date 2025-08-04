import logging


logger = logging.getLogger("yfinance-service")
logger.setLevel(logging.INFO)

if not logger.hasHandlers():
    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s %(message)s [%(pathname)s:%(lineno)d]"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)
