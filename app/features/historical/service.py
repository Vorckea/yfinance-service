import asyncio
import re
from datetime import date

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from .models import HistoricalPrice, HistoricalResponse

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


async def fetch_historical(symbol: str, start: date | None, end: date | None) -> HistoricalResponse:
    if not SYMBOL_PATTERN.match(symbol):
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )

    def get_history(symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
        ticker = yf.Ticker(symbol)
        return ticker.history(start=start, end=end)

    df = await asyncio.to_thread(get_history, symbol, start, end)
    if df.empty:
        raise HTTPException(status_code=404, detail=f"No historical data for symbol {symbol}")

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
