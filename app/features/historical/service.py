import asyncio
from datetime import date
from functools import lru_cache

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from ...monitoring.instrumentation import observe
from ...utils.logger import logger
from .models import HistoricalPrice, HistoricalResponse


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def _fetch_history(symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
    ticker = _get_ticker(symbol)
    # TODO(perf): Pass interval param and allow client control (e.g., 1d/1h) to reduce payload size.
    # TODO(resilience): Add retry with backoff for transient network failures.
    df = ticker.history(start=start, end=end)
    if getattr(df.index, "tz", None) is not None:
        # TODO(data): Confirm timezone correctness for markets outside US (multi-exchange support).
        df = df.tz_convert(None)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    # for certain asset classes (e.g., some funds / indices).
    return df.reindex(columns=cols) if not df.empty else df


def _map_history(df: pd.DataFrame) -> list[HistoricalPrice]:
    return [
        HistoricalPrice(
            date=ts.date(),
            open=float(open_),
            high=float(high_),
            low=float(low_),
            close=float(close_),
            volume=int(volume_) if pd.notna(volume_) else None,
        )
        for ts, open_, high_, low_, close_, volume_ in df.itertuples(index=True, name=None)
    ]


async def fetch_historical(symbol: str, start: date | None, end: date | None) -> HistoricalResponse:
    """Fetch historical stock data for a given symbol."""
    logger.info("historical.fetch.request", extra={"symbol": symbol, "start": start, "end": end})

    op = "history"
    try:
        with observe(op):
            df = await asyncio.wait_for(
                asyncio.to_thread(_fetch_history, symbol, start, end), timeout=120
            )
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        logger.warning(
            "historical.fetch.timeout",
            extra={"symbol": symbol, "start": start, "end": end, "error": str(e)},
        )
        raise HTTPException(status_code=503, detail="Upstream timeout")
    except asyncio.CancelledError:
        logger.warning(
            "historical.fetch.cancelled", extra={"symbol": symbol, "start": start, "end": end}
        )
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception:
        logger.exception(
            "historical.fetch.unexpected",
            extra={"symbol": symbol, "start": start, "end": end},
        )
        raise HTTPException(status_code=500, detail="Unexpected error fetching historical data")

    if df.empty:
        logger.info(
            "historical.fetch.no_data", extra={"symbol": symbol, "start": start, "end": end}
        )
        # Align 404 detail message with other feature services (quote/info) and tests which
        # assert substring "No data for".
        raise HTTPException(status_code=404, detail=f"No data for {symbol}")

    logger.info("historical.fetch.success", extra={"symbol": symbol, "rows": len(df)})

    prices = _map_history(df)

    return HistoricalResponse(symbol=symbol.upper(), prices=prices)
