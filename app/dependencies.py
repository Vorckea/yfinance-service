"""Shared application dependencies."""

from functools import lru_cache

from .clients.interface import YFinanceClientInterface
from .clients.yfinance_client import YFinanceClient
from .utils.cache import TTLCache

@lru_cache
def get_yfinance_client() -> YFinanceClientInterface:
    """Get a cached instance of the YFinance client."""
    return YFinanceClient()


@lru_cache
def get_info_cache() -> TTLCache:
    """Get a shared TTL cache for info responses (company metadata is relatively stable)."""
    # 5-minute TTL for info; quote data is fetched fresh each time.
    return TTLCache(size=256, ttl=300, cache_name="tll_cache", resource="snapshot")
