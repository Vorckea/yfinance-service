import asyncio
from functools import lru_cache
from typing import Any

import yfinance as yf
from fastapi import HTTPException

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

    try:
        info = await asyncio.wait_for(asyncio.to_thread(_fetch_info, symbol), timeout=30)
    except (ConnectionError, TimeoutError) as e:
        logger.warning("quote.fetch.timeout", extra={"symbol": symbol, "error": str(e)})
        raise HTTPException(status_code=503, detail="Upstream timeout")
    except asyncio.CancelledError:
        logger.error("quote.fetch.cancelled", extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail="Internal error fetching quote data")
    except Exception:
        logger.exception("quote.fetch.unexpected", extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail="Internal error fetching quote data")
    if not info:
        logger.error("quote.fetch.no_data", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    logger.info("quote.fetch.success", extra={"symbol": symbol})
    return _map_info(symbol, info)
