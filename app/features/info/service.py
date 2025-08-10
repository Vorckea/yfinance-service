import asyncio
import time
from functools import lru_cache
from typing import Any

import yfinance as yf
from fastapi import HTTPException

from ...monitoring.metrics import YF_LATENCY, YF_REQUESTS
from ...utils.logger import logger
from .models import InfoResponse


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    ticker = yf.Ticker(symbol)
    return ticker


def _fetch_info(symbol: str) -> dict[str, Any]:
    ticker = _get_ticker(symbol)
    return ticker.info


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


async def fetch_info(symbol: str) -> InfoResponse:
    """Fetch information for a given symbol.

    Args:
        symbol (str): The stock symbol to fetch information for.

    Raises:
        HTTPException: If the symbol is invalid or not found.
        HTTPException: If there is a timeout or connection error.
        HTTPException: If the data is not found.
        HTTPException: If there is an internal error.

    Returns:
        InfoResponse: The information response for the given symbol.

    """
    symbol = symbol.upper().strip()
    logger.info("info.fetch.start", extra={"symbol": symbol})

    op = "info_detail"
    t0 = time.perf_counter()
    try:
        info = await asyncio.wait_for(asyncio.to_thread(_fetch_info, symbol), timeout=30)
        YF_REQUESTS.labels(operation=op, outcome="success").inc()
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        YF_REQUESTS.labels(operation=op, outcome="timeout").inc()
        logger.warning("info.fetch.timeout", extra={"symbol": symbol, "error": str(e)})
        raise HTTPException(status_code=503, detail="Upstream timeout")
    except asyncio.CancelledError:
        YF_REQUESTS.labels(operation=op, outcome="cancelled").inc()
        logger.warning("info.fetch.cancelled", extra={"symbol": symbol})
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception:
        YF_REQUESTS.labels(operation=op, outcome="error").inc()
        logger.exception("info.fetch.unexpected", extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail="Unexpected error fetching info data")
    finally:
        YF_LATENCY.labels(operation=op).observe(time.perf_counter() - t0)
    if not info:
        logger.info("info.fetch.no_data", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    logger.info("info.fetch.success", extra={"symbol": symbol})
    return _map_info(symbol, info)
