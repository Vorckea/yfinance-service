import asyncio
from datetime import date
from functools import lru_cache

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from .models import HistoricalPrice, HistoricalResponse


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


async def fetch_historical(symbol: str, start: date | None, end: date | None) -> HistoricalResponse:
    """Fetch historical stock data for a given symbol."""
    logger.info("Historical request received", extra={"symbol": symbol, "start": start, "end": end})

    def get_history(symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
        ticker = _get_ticker(symbol)
        df = ticker.history(start=start, end=end)
        if getattr(df.index, "tz", None) is not None:
            df = df.tz_convert(None)
        cols = ["Open", "High", "Low", "Close", "Volume"]
        return df.reindex(columns=cols) if not df.empty else df

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
            open=float(open_),
            high=float(high_),
            low=float(low_),
            close=float(close_),
            volume=int(volume_) if pd.notna(volume_) else 0,
        )
        for ts, open_, high_, low_, close_, volume_ in df.itertuples(index=True, name=None)
    ]

    return HistoricalResponse(symbol=symbol.upper(), prices=prices)
