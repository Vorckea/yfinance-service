"""Info service: fetches company metadata via yfinance with instrumentation.

Backlog TODOs inline mark potential improvements (caching, resiliency, data quality).
"""

from typing import Any, Mapping

from ...clients.interface import YFinanceClientInterface
from ...utils.cache.interface import CacheInterface
from ...utils.logger import logger
from .models import InfoResponse


async def fetch_info(
    symbol: str, client: YFinanceClientInterface, info_cache: CacheInterface | None = None
) -> InfoResponse:
    """Fetch information for a given symbol.

    Args:
        symbol (str): The stock symbol to fetch information for.
        client (YFinanceClientInterface): The YFinance client to use for fetching data.
        info_cache (CacheInterface | None): Optional cache for info responses. If provided, info is cached.

    Returns:
        InfoResponse: The information response for the given symbol.

    """
    symbol = symbol.strip().upper()
    logger.info("info.fetch.start", extra={"symbol": symbol})

    if info_cache:
        cached = await info_cache.get(symbol)
        if cached is not None:
            logger.info("info.fetch.cache.hit", extra={"symbol": symbol})
            return cached

    info: Mapping[str, Any] = await client.get_info(symbol)

    logger.info("info.fetch.success", extra={"symbol": symbol})

    result = InfoResponse.model_validate({"symbol": symbol, **info})

    if info_cache:
        try:
            await info_cache.set(symbol, result)
        except Exception:
            logger.exception("info.set.cache.failed", extra={"symbol": symbol})

    return result
