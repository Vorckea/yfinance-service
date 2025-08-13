import asyncio
from datetime import date
from functools import lru_cache
from typing import Any

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from ..monitoring.instrumentation import observe
from ..utils.logger import logger

YFinanceData = dict[str, Any]


class YFinanceClient:
    def __init__(self, timeout: int = 30, ticker_cache_size: int = 512):
        self._timeout = timeout
        self._get_ticker = lru_cache(maxsize=ticker_cache_size)(self._ticker_factory)

    def _ticker_factory(self, symbol: str) -> yf.Ticker:
        return yf.Ticker(symbol)

    async def _fetch_data(self, op: str, fetch_func, *args, **kwargs) -> Any:
        symbol = args[0] if args else "N/A"
        try:
            with observe(op):
                return await asyncio.wait_for(
                    asyncio.to_thread(fetch_func, *args, **kwargs), self._timeout
                )
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            logger.warning(
                "yfinance.client.timeout", extra={"symbol": symbol, "op": op, "error": str(e)}
            )
            raise HTTPException(status_code=503, detail="Upstream timeout")
        except asyncio.CancelledError:
            logger.warning("yfinance.client.cancelled", extra={"symbol": symbol, "op": op})
            raise HTTPException(status_code=499, detail="Request cancelled")
        except Exception:
            logger.exception("yfinance.client.unexpected", extra={"symbol": symbol, "op": op})
            raise HTTPException(status_code=500, detail="Unexpected error fetching data")

    async def get_info(self, symbol: str) -> YFinanceData:
        ticker = self._get_ticker(symbol)
        info = await self._fetch_data("info", ticker.get_info)
        if not info:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "info"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        return info

    async def get_history(self, symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
        ticker = self._get_ticker(symbol)
        history = await self._fetch_data("history", ticker.history, start=start, end=end)
        if history.empty:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "history"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        return history

    async def ping(self) -> bool:
        try:
            self._get_ticker("AAPL")
            return True
        except HTTPException as e:
            logger.warning(
                "yfinance.client.ping_failed",
                extra={"error": str(e), "ticker": "AAPL"},
                exc_info=True,
            )
            return False
