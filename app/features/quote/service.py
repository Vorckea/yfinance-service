"""Quote service: fetches latest market data via yfinance."""

import asyncio
from functools import lru_cache
from typing import Any

import yfinance as yf
from fastapi import HTTPException

from ...monitoring.instrumentation import observe
from ...utils.logger import logger
from .models import QuoteResponse

TIMEOUT_SECONDS = 30
TICKER_CACHE_SIZE = 512

QuoteDict = dict[str, Any]


@lru_cache(maxsize=TICKER_CACHE_SIZE)
def _get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def _fetch_info(symbol: str) -> QuoteDict:
    ticker = _get_ticker(symbol)
    return ticker.info


def _map_info(symbol: str, info: QuoteDict) -> QuoteResponse:
    try:
        return QuoteResponse(
            symbol=symbol.upper(),
            current_price=float(info.get("regularMarketPrice")),
            previous_close=float(
                info.get("regularMarketPreviousClose") or info.get("previousClose")
            ),
            open=float(info.get("regularMarketOpen") or info.get("open")),
            high=float(info.get("regularMarketDayHigh") or info.get("dayHigh")),
            low=float(info.get("regularMarketDayLow") or info.get("dayLow")),
            volume=int(info.get("regularMarketVolume") or info.get("volume"))
            if info.get("regularMarketVolume") or info.get("volume")
            else None,
        )
    except (TypeError, ValueError) as e:
        logger.warning("quote.fetch.malformed_data", extra={"symbol": symbol, "error": str(e)})
        raise HTTPException(status_code=502, detail="Malformed data from upstream")


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
    try:
        with observe(op):
            info = await asyncio.wait_for(
                asyncio.to_thread(_fetch_info, symbol),
                timeout=TIMEOUT_SECONDS,
            )
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        logger.warning("quote.fetch.timeout", extra={"symbol": symbol, "error": str(e)})
        raise HTTPException(status_code=503, detail="Upstream timeout")
    except HTTPException:
        raise
    except asyncio.CancelledError:
        logger.warning("quote.fetch.cancelled", extra={"symbol": symbol})
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception:
        logger.exception("quote.fetch.unexpected", extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail="Unexpected error fetching quote data")

    if not info:
        logger.info("quote.fetch.no_data", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    result = _map_info(symbol, info)
    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return result
