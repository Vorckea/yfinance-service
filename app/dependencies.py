"""Shared application dependencies."""

from functools import lru_cache

from .clients.yfinance_client import YFinanceClient
from .settings import get_settings
from .utils.cache import SnapshotCache, TTLCache

settings = get_settings()


@lru_cache
def get_yfinance_client() -> YFinanceClient:
    """Get a cached instance of the YFinance client."""
    return YFinanceClient()


@lru_cache
def get_info_cache() -> TTLCache:
    """Get a shared TTL cache for info responses (company metadata is relatively stable)."""
    # 5-minute TTL for info; quote data is fetched fresh each time.
    return TTLCache(
        size=settings.info_cache_maxsize,
        ttl=settings.info_cache_ttl,
        cache_name="ttl_cache",
        resource="info",
    )


@lru_cache
def get_earnings_cache() -> SnapshotCache:
    """Get a shared TTL cache for earnings responses (earnings statements change infrequently)."""
    if settings.earnings_cache_ttl <= 0:
        # Return a cache with 0 TTL (cache disabled)
        return SnapshotCache(maxsize=0, ttl=0)
    return SnapshotCache(
        maxsize=settings.earnings_cache_maxsize,
        ttl=settings.earnings_cache_ttl,
    )
