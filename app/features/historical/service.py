import asyncio
import time
from datetime import date
from functools import lru_cache

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from ...utils.logger import logger
from ...monitoring.metrics import YF_LATENCY, YF_REQUESTS
from .models import HistoricalPrice, HistoricalResponse


@lru_cache(maxsize=512)
def _get_ticker(symbol: str) -> yf.Ticker:
    return yf.Ticker(symbol)


def _fetch_history(symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
    ticker = _get_ticker(symbol)
    df = ticker.history(start=start, end=end)
    if getattr(df.index, "tz", None) is not None:
        df = df.tz_convert(None)
    cols = ["Open", "High", "Low", "Close", "Volume"]
    return df.reindex(columns=cols) if not df.empty else df


def _map_history(df: pd.DataFrame) -> list[HistoricalPrice]:
    return [
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


async def fetch_historical(symbol: str, start: date | None, end: date | None) -> HistoricalResponse:
    """Fetch historical stock data for a given symbol."""
    logger.info("historical.fetch.request", extra={"symbol": symbol, "start": start, "end": end})

    op = "history"
    t0 = time.perf_counter()
    try:
        df = await asyncio.wait_for(
            asyncio.to_thread(_fetch_history, symbol, start, end), timeout=120
        )
        YF_REQUESTS.labels(operation=op, outcome="success").inc()
    except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
        YF_REQUESTS.labels(operation=op, outcome="timeout").inc()
        logger.warning(
            "historical.fetch.timeout",
            extra={"symbol": symbol, "start": start, "end": end, "error": str(e)},
        )
        raise HTTPException(status_code=503, detail="Upstream timeout")
    except asyncio.CancelledError:
        YF_REQUESTS.labels(operation=op, outcome="cancelled").inc()
        logger.warning(
            "historical.fetch.cancelled", extra={"symbol": symbol, "start": start, "end": end}
        )
        raise HTTPException(status_code=499, detail="Request cancelled")
    except Exception:
        YF_REQUESTS.labels(operation=op, outcome="error").inc()
        logger.exception(
            "historical.fetch.unexpected",
            extra={"symbol": symbol, "start": start, "end": end},
        )
        raise HTTPException(status_code=500, detail="Unexpected error fetching historical data")
    finally:
        YF_LATENCY.labels(operation=op).observe(time.perf_counter() - t0)

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
