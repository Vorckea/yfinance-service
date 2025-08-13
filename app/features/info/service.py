"""Info service: fetches company metadata via yfinance with instrumentation.

Backlog TODOs inline mark potential improvements (caching, resiliency, data quality).
"""

from typing import Any

from ...clients.yfinance_client import YFinanceClient
from ...utils.logger import logger
from .models import InfoResponse


def _map_info(symbol: str, info: dict[str, Any]) -> InfoResponse:
    return InfoResponse(
        symbol=symbol.upper(),
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
    )


async def fetch_info(symbol: str, client: YFinanceClient) -> InfoResponse:
    """Fetch information for a given symbol.

    Args:
        symbol (str): The stock symbol to fetch information for.
        client (YFinanceClient): The YFinance client to use for fetching data.

    Returns:
        InfoResponse: The information response for the given symbol.

    """
    symbol = symbol.upper().strip()
    logger.info("info.fetch.start", extra={"symbol": symbol})

    info = await client.get_info(symbol)

    logger.info("info.fetch.success", extra={"symbol": symbol})
    return _map_info(symbol, info)
