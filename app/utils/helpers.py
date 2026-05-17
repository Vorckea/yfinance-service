from __future__ import annotations

from typing import Any, Awaitable, Callable, Optional

from .logger import logger


def normalize_symbol(symbol: Optional[str]) -> str:
    """Normalize a stock symbol: strip whitespace and uppercase.

    Returns an empty string for falsy inputs.
    """
    if not symbol:
        return ""
    return symbol.strip().upper()


async def fetch_with_cache(
    key: str,
    cache: object | None,
    fetcher: Callable[[], Awaitable[Any]],
    ttl: Optional[int] = None,
    on_set_failed_event: Optional[str] = None,
) -> Any:
    """Fetch a value using `fetcher` and populate `cache` on miss.

    - `cache` is expected to implement async `get(key)` and `set(key, value)`.
    - If `ttl` is provided and the cache exposes a `set_with_ttl`, it will be used.
    - Exceptions from cache operations are logged but do not fail the fetch.

    Returns the cached or fetched value.
    """
    if cache:
        try:
            cached = await cache.get(key)
            if cached is not None:
                logger.info("helpers.cache.hit", extra={"key": key})
                return cached
        except Exception:
            logger.exception("helpers.cache.get.failed", extra={"key": key})

    # Miss: call fetcher
    result = await fetcher()

    if cache:
        try:
            # Prefer a ttl-aware setter if available
            if ttl is not None and hasattr(cache, "set_with_ttl"):
                await cache.set_with_ttl(key, result, ttl)
            else:
                await cache.set(key, result)
        except Exception:
            logger.exception("helpers.cache.set.failed", extra={"key": key})
            if on_set_failed_event:
                logger.exception(on_set_failed_event, extra={"key": key})

    return result
