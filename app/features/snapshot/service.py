"""Snapshot service: Composes info and quote into a single response.

If either fetch_info or fetch_quote fails, the entire request returns 502,
keeping consistent error semantics with individual endpoints.

Caching strategy:
- Info (company metadata) is cached with a 5-minute TTL; it's relatively stable.
- Quote (latest price) is always fetched fresh to ensure currency.
"""

import asyncio

from ...clients.interface import YFinanceClientInterface
from ...utils.cache import SnapshotCache
from ...utils.logger import logger
from ..info.service import fetch_info
from ..quote.service import fetch_quote
from .models import SnapshotResponse


async def fetch_snapshot(
    symbol: str, client: YFinanceClientInterface, info_cache: SnapshotCache | None = None
) -> SnapshotResponse:
    """Fetch combined info and quote for a symbol in a single response.

    Args:
        symbol (str): The stock symbol to fetch.
        client (YFinanceClientInterface): The YFinance client to use.
        info_cache (SnapshotCache, optional): Cache for info responses. If provided, info is cached.

    Returns:
        SnapshotResponse: Combined info and quote data.

    Raises:
        HTTPException: 400 for empty symbol, 502 if either info or quote fetch fails.

    """
    symbol = symbol.upper().strip()
    logger.info("snapshot.fetch.start", extra={"symbol": symbol})

    # Fetch info (possibly cached) and quote (always fresh) concurrently.
    # If either fails (raises HTTPException with 502), the exception propagates and the
    # entire endpoint returns 502, for consistent error semantics.
    if info_cache:
        info_coro = info_cache.get_or_set(symbol, fetch_info(symbol, client))
    else:
        info_coro = fetch_info(symbol, client)

    info, quote = await asyncio.gather(
        info_coro,
        fetch_quote(symbol, client),
    )

    logger.info("snapshot.fetch.success", extra={"symbol": symbol})

    # Populate convenience top-level fields for compact responses.
    current_price = getattr(quote, "current_price", None)
    currency = getattr(info, "currency", None)

    return SnapshotResponse(
        symbol=symbol,
        info=info,
        quote=quote,
        current_price=current_price,
        currency=currency,
    )
