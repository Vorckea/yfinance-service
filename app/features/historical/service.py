import asyncio
import re
from datetime import date
from functools import lru_cache

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from .models import HistoricalPrice, HistoricalResponse

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    # Lightweight cache to avoid recreating Ticker objects repeatedly
    return yf.Ticker(symbol)


async def fetch_historical(symbol: str, start: date | None, end: date | None) -> HistoricalResponse:
    """Fetch historical stock data for a given symbol."""
    logger.info("Historical request received", extra={"symbol": symbol, "start": start, "end": end})
    if not SYMBOL_PATTERN.match(symbol):
        logger.warning("Invalid symbol format", extra={"symbol": symbol})
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )

    def get_history(symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
        ticker = _get_ticker(symbol)
        df = ticker.history(start=start, end=end)
        if getattr(df.index, "tz", None) is not None:
            df = df.tz_convert(None)
        cols = ["Open", "High", "Low", "Close", "Volume"]
        return df[cols] if not df.empty else df

    try:
        df = await asyncio.to_thread(get_history, symbol, start, end)
    except Exception as e:
        logger.exception(
            f"Exception fetching historical data ({type(e).__name__})",
            extra={"symbol": symbol, "start": start, "end": end},
        )
        raise HTTPException(status_code=500, detail="Internal error fetching historical data")

    if df.empty:
        logger.info(
            "No historical data found", extra={"symbol": symbol, "start": start, "end": end}
        )
        raise HTTPException(status_code=404, detail=f"No historical data for {symbol}")

    logger.info("Historical data fetched", extra={"symbol": symbol, "rows": len(df)})

    prices = [
        HistoricalPrice(
            date=ts.date(),
            open=float(o),
            high=float(h),
            low=float(l),
            close=float(c),
            volume=int(v) if pd.notna(v) else 0,
        )
        for ts, o, h, l, c, v in df.itertuples(index=True, name=None)
    ]

    return HistoricalResponse(symbol=symbol.upper(), prices=prices)
