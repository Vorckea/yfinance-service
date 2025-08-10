import asyncio
import time
from functools import lru_cache
from typing import Any

import yfinance as yf
from fastapi import HTTPException

from ...monitoring.metrics import YF_LATENCY, YF_REQUESTS
from ...utils.logger import logger
from .models import QuoteResponse


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    ticker = yf.Ticker(symbol)
    return ticker


def _fetch_info(symbol: str) -> dict[str, Any]:
    ticker = _get_ticker(symbol)
    return ticker.info


def _map_info(symbol: str, info: dict[str, Any]) -> QuoteResponse:
    return QuoteResponse(
        symbol=symbol.upper(),
        current_price=info.get("regularMarketPrice"),
        previous_close=info.get("regularMarketPreviousClose") or info.get("previousClose"),
        open=info.get("regularMarketOpen") or info.get("open"),
        high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
        low=info.get("dayLow") or info.get("regularMarketDayLow"),
        volume=info.get("volume") or info.get("regularMarketVolume"),
    )


async def fetch_quote(symbol: str) -> QuoteResponse:
    """Fetch stock quote information.

    Args:
        symbol (str): The stock symbol to fetch.

    Raises:
        HTTPException: If the symbol is invalid or not found.
        HTTPException: If there is a timeout or connection error.
        HTTPException: If the request is cancelled.
        HTTPException: If there is an unexpected error.

    Returns:
        QuoteResponse: The stock quote information.

    """
    symbol = symbol.upper().strip()
    logger.info("quote.fetch.start", extra={"symbol": symbol})

    op = "quote_info"
    t0 = time.perf_counter()
    try:
        info = await asyncio.wait_for(asyncio.to_thread(_fetch_info, symbol), timeout=30)
        YF_REQUESTS.labels(operation=op, outcome="success").inc()
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        YF_REQUESTS.labels(operation=op, outcome="timeout").inc()
        logger.warning("quote.fetch.timeout", extra={"symbol": symbol, "error": str(e)})
        raise HTTPException(status_code=503, detail="Upstream timeout")
    except asyncio.CancelledError:
        YF_REQUESTS.labels(operation=op, outcome="cancelled").inc()
        logger.warning("quote.fetch.cancelled", extra={"symbol": symbol})
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception:
        YF_REQUESTS.labels(operation=op, outcome="error").inc()
        logger.exception("quote.fetch.unexpected", extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail="Unexpected error fetching quote data")
    finally:
        YF_LATENCY.labels(operation=op).observe(time.perf_counter() - t0)
    if not info:
        logger.info("quote.fetch.no_data", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return _map_info(symbol, info)
