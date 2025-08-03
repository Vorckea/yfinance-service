import asyncio
import re

import yfinance as yf
from fastapi import HTTPException

from .models import QuoteResponse

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


async def fetch_quote(symbol: str) -> QuoteResponse:
    if not SYMBOL_PATTERN.match(symbol):
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )

    def fetch_info(symbol: str):
        ticker = yf.Ticker(symbol)
        return ticker.info

    info = await asyncio.to_thread(fetch_info, symbol)
    if not info:
        raise HTTPException(status_code=404, detail=f"No data for symbol {symbol}")
    return QuoteResponse(
        symbol=symbol.upper(),
        current_price=info.get("regularMarketPrice"),
        previous_close=info.get("regularMarketPreviousClose") or info.get("previousClose"),
        open=info.get("regularMarketOpen") or info.get("open"),
        high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
        low=info.get("dayLow") or info.get("regularMarketDayLow"),
        volume=info.get("volume") or info.get("regularMarketVolume"),
    )
