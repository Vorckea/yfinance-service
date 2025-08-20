"""Shared application dependencies"""

from functools import lru_cache

from .clients.interface import YFinanceClientInterface
from .clients.yfinance_client import YFinanceClient


@lru_cache
def get_yfinance_client() -> YFinanceClientInterface:
    return YFinanceClient()
