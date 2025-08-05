import asyncio
import re
from datetime import date

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from .models import HistoricalPrice, HistoricalResponse

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


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
        ticker = yf.Ticker(symbol)
        return ticker.history(start=start, end=end)

    try:
        df = await asyncio.to_thread(get_history, symbol, start, end)
    except Exception:
        logger.exception(
            "Exception fetching historical data",
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
            date=row.name.date(),
            open=row["Open"],
            high=row["High"],
            low=row["Low"],
            close=row["Close"],
            volume=int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
        )
        for index, row in df.iterrows()
    ]
    return HistoricalResponse(
        symbol=symbol.upper(),
        prices=prices,
    )
