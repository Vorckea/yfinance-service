import asyncio
from functools import lru_cache

import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from .models import QuoteResponse


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    ticker = yf.Ticker(symbol)
    return ticker


def _map_info(symbol: str, info: dict) -> QuoteResponse:
    return QuoteResponse(
        symbol=symbol,
        current_price=info.get("regularMarketPrice"),
        previous_close=info.get("regularMarketPreviousClose") or info.get("previousClose"),
        open=info.get("regularMarketOpen") or info.get("open"),
        high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
        low=info.get("dayLow") or info.get("regularMarketDayLow"),
        volume=info.get("volume") or info.get("regularMarketVolume"),
    )


async def fetch_quote(symbol: str) -> QuoteResponse:
    logger.info("Quote request received", extra={"symbol": symbol})

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
    return _map_info(symbol, info)
