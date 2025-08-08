import asyncio
import re
from functools import lru_cache

import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from .models import QuoteResponse

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    ticker = yf.Ticker(symbol)
    return ticker


async def fetch_quote(symbol: str) -> QuoteResponse:
    logger.info("Quote request received", extra={"symbol": symbol})
    if not SYMBOL_PATTERN.match(symbol):
        logger.warning("Invalid symbol format", extra={"symbol": symbol})
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )

    def fetch_info(symbol: str):
        ticker = _get_ticker(symbol)
        return ticker.info

    try:
        info = await asyncio.to_thread(fetch_info, symbol)
    except Exception as e:
        logger.exception(
            f"Exception fetching quote data. ({type(e).__name__}): {e}", extra={"symbol": symbol}
        )
        raise HTTPException(status_code=500, detail="Internal error fetching quote data")

    if not info:
        logger.error("No data found", extra={"symbol": symbol})
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")
    logger.info("Quote data fetched", extra={"symbol": symbol})
    return QuoteResponse(
        symbol=symbol.upper(),
        current_price=info.get("regularMarketPrice"),
        previous_close=info.get("regularMarketPreviousClose") or info.get("previousClose"),
        open=info.get("regularMarketOpen") or info.get("open"),
        high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
        low=info.get("dayLow") or info.get("regularMarketDayLow"),
        volume=info.get("volume") or info.get("regularMarketVolume"),
    )
