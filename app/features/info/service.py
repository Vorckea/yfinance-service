"""Info service: fetches company metadata via yfinance with instrumentation.

Backlog TODOs inline mark potential improvements (caching, resiliency, data quality).
"""

from typing import Any, Mapping

from fastapi import HTTPException

from ...clients.interface import YFinanceClientInterface
from ...utils.cache.interface import CacheInterface
from ...utils.logger import logger
from .models import InfoResponse


def _map_info(symbol: str, info: Mapping[str, Any]) -> InfoResponse:
    return InfoResponse(
        symbol=symbol,
        short_name=info.get("shortName"),
        long_name=info.get("longName"),
        exchange=info.get("exchange"),
        sector=info.get("sector"),
        industry=info.get("industry"),
        country=info.get("country"),
        website=info.get("website"),
        description=info.get("longBusinessSummary"),
        market_cap=info.get("marketCap"),
        shares_outstanding=info.get("sharesOutstanding"),
        dividend_yield=info.get("dividendYield"),
        fifty_two_week_high=info.get("fiftyTwoWeekHigh"),
        fifty_two_week_low=info.get("fiftyTwoWeekLow"),
        current_price=info.get("currentPrice"),
        trailing_pe=info.get("trailingPE"),
        beta=info.get("beta"),
        address=info.get("address1"),
        currency=info.get("currency"),
    )


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
            logger.info(msg="info.fetch.cache.hit", extra={"symbol": symbol})
            return cached

    info: Mapping[str, Any] | None = await client.get_info(symbol)

    if not info:
        logger.error("info.fetch.no_data", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail="No info data found for symbol")

    logger.info("info.fetch.success", extra={"symbol": symbol})
    result = _map_info(symbol, info)

    if info_cache:
        try:
            await info_cache.set(symbol, result)
        except Exception:
            logger.exception("info.set.cache.failed", extra={"symbol": symbol})

    return result
