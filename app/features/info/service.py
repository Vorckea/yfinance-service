"""Info service: fetches company metadata via yfinance with instrumentation.

Backlog TODOs inline mark potential improvements (caching, resiliency, data quality).
"""

from typing import Any, Mapping

from ...clients.interface import YFinanceClientInterface
from ...utils.cache.interface import CacheInterface
from ...utils.helpers import fetch_with_cache, normalize_symbol
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
    symbol = normalize_symbol(symbol)
    logger.info("info.fetch.start", extra={"symbol": symbol})

    async def _fetch_and_validate():
        info: Mapping[str, Any] = await client.get_info(symbol)
        logger.info("info.fetch.success", extra={"symbol": symbol})
        return InfoResponse.model_validate({"symbol": symbol, **info})

    if info_cache:
        result = await fetch_with_cache(
            symbol, info_cache, _fetch_and_validate, on_set_failed_event="info.set.cache.failed"
        )
    else:
        result = await _fetch_and_validate()

    return result
