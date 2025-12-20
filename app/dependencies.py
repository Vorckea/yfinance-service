"""Shared application dependencies."""

import os
from functools import lru_cache

from .clients.interface import YFinanceClientInterface
from .clients.yfinance_client import YFinanceClient
from .utils.cache import TTLCache, SnapshotCache

# Configuration for bulk quote endpoint concurrency
MAX_BULK_CONCURRENCY = int(os.getenv("MAX_BULK_CONCURRENCY", "10"))

# Configuration for earnings cache TTL (in seconds; 0 = disable caching)
EARNINGS_CACHE_TTL = int(os.getenv("EARNINGS_CACHE_TTL", "3600"))  # Default 1 hour

@lru_cache
def get_yfinance_client() -> YFinanceClient:
    """Get a cached instance of the YFinance client."""
    return YFinanceClient()


@lru_cache
def get_info_cache() -> TTLCache:
    """Get a shared TTL cache for info responses (company metadata is relatively stable)."""
    # 5-minute TTL for info; quote data is fetched fresh each time.
    return TTLCache(size=256, ttl=300, cache_name="ttl_cache", resource="snapshot")

@lru_cache
def get_earnings_cache() -> SnapshotCache:
    """Get a shared TTL cache for earnings responses (earnings statements change infrequently)."""
    if EARNINGS_CACHE_TTL <= 0:
        # Return a cache with 0 TTL (cache disabled)
        return SnapshotCache(maxsize=0, ttl=0)
    return SnapshotCache(maxsize=128, ttl=EARNINGS_CACHE_TTL)
