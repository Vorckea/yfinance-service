"""Snapshot service: Composes info and quote into a single response.

If either fetch_info or fetch_quote fails, the entire request returns 502,
keeping consistent error semantics with individual endpoints.
"""

import asyncio

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from ..info.service import fetch_info
from ..quote.service import fetch_quote
from .models import SnapshotResponse


async def fetch_snapshot(symbol: str, client: YFinanceClientInterface) -> SnapshotResponse:
    """Fetch combined info and quote for a symbol in a single response.

    Args:
        symbol (str): The stock symbol to fetch.
        client (YFinanceClientInterface): The YFinance client to use.

    Returns:
        SnapshotResponse: Combined info and quote data.

    Raises:
        HTTPException: 400 for empty symbol, 502 if either info or quote fetch fails.

    """
    symbol = symbol.upper().strip()
    logger.info("snapshot.fetch.start", extra={"symbol": symbol})

    # Fetching both info and quote concurrently to minimize latency.
    # If either fails (raise HTTPException with 502), the exception propagates and the
    # entire endpoint returns 502, for consistent error semantics.
    info, quote = await asyncio.gather(
        fetch_info(symbol, client),
        fetch_quote(symbol, client),
    )

    logger.info("snapshot.fetch.success", extra={"symbol": symbol})
    return SnapshotResponse(symbol=symbol, info=info, quote=quote)
