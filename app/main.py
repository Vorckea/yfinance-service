import asyncio
import re
from fastapi import FastAPI, HTTPException, Query
import pandas as pd
import yfinance as yf
from pydantic import BaseModel
import logging
from datetime import date

app = FastAPI(title="YFinance Proxy Service", version="1.0.0")

logging.basicConfig(level=logging.INFO)

SYMBOL_PATTERN = re.compile(r"^[A-Za-z0-9\.\-]{1,10}$")


class QuoteResponse(BaseModel):
    symbol: str
    current_price: float | None
    previous_close: float | None
    open: float | None
    high: float | None
    low: float | None
    volume: int | None


@app.get("/quote/{symbol}", response_model=QuoteResponse)
async def get_quote(symbol: str) -> QuoteResponse:
    """Get the latest quote for a given stock symbol."""
    if not SYMBOL_PATTERN.match(symbol):
        logging.warning(f"Invalid symbol format: {symbol}")
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )
    try:

        def fetch_info(symbol: str):
            ticker = yf.Ticker(symbol)
            return ticker.info

        info = await asyncio.to_thread(fetch_info, symbol)
        if not info:
            logging.info(f"No data found for symbol: {symbol}")
            raise HTTPException(status_code=404, detail=f"No data for symbol {symbol}")
        return QuoteResponse(
            symbol=symbol.upper(),
            current_price=info.get("regularMarketPrice"),
            previous_close=info.get("regularMarketPreviousClose")
            or info.get("previousClose"),
            open=info.get("regularMarketOpen") or info.get("open"),
            high=info.get("dayHigh") or info.get("regularMarketDayHigh"),
            low=info.get("dayLow") or info.get("regularMarketDayLow"),
            volume=info.get("volume") or info.get("regularMarketVolume"),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class HistoricalPrice(BaseModel):
    date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class HistoricalResponse(BaseModel):
    symbol: str
    prices: list[HistoricalPrice]


@app.get("/historical/{symbol}", response_model=HistoricalResponse)
async def get_historical(
    symbol: str,
    start: date | None = Query(None, description="Start date in YYYY-MM-DD format"),
    end: date | None = Query(None, description="End date in YYYY-MM-DD format"),
) -> HistoricalResponse:
    """Fetch historical prices for a given stock symbol."""
    if not SYMBOL_PATTERN.match(symbol):
        logging.warning(f"Invalid symbol format: {symbol}")
        raise HTTPException(
            status_code=400,
            detail="Symbol must be 1-10 chars, alphanumeric, dot or dash.",
        )
    try:

        def fetch_historical(
            symbol: str, start: date | None, end: date | None
        ) -> pd.DataFrame:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(start=start, end=end)
            return hist

        df = await asyncio.to_thread(fetch_historical, symbol, start, end)
        if df.empty:
            logging.info(f"No historical data found for symbol: {symbol}")
            raise HTTPException(
                status_code=404, detail=f"No historical data for symbol {symbol}"
            )

        return HistoricalResponse(
            symbol=symbol.upper(),
            prices=[
                HistoricalPrice(
                    date=index.date(),
                    open=row["Open"],
                    high=row["High"],
                    low=row["Low"],
                    close=row["Close"],
                    volume=int(row["Volume"]) if not pd.isna(row["Volume"]) else 0,
                )
                for index, row in df.iterrows()
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "service": app.title, "version": app.version}
