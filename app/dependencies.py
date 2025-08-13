"""Shared application dependencies"""

from functools import lru_cache

from .clients.yfinance_client import YFinanceClient


@lru_cache
def get_yfinance_client() -> YFinanceClient:
    return YFinanceClient()
