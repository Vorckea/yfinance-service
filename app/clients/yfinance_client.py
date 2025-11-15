"""Client for interacting with the Yahoo Finance API."""

import asyncio
from asyncio import Semaphore
from collections.abc import Callable
from datetime import date
from functools import lru_cache
from typing import Any, TypeVar

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from app.clients.interface import YFinanceClientInterface
from app.utils.cache import SnapshotCache

from ..monitoring.instrumentation import observe
from ..utils.logger import logger

YFinanceData = dict[str, Any]
T = TypeVar("T")


class YFinanceClient(YFinanceClientInterface):
    """Client for interacting with the Yahoo Finance API."""

    _snapshot_cache = SnapshotCache(maxsize=64, ttl=120)
    _semaphore = Semaphore(5)  # limit concurrent upstream calls

    async def get_snapshot(self, symbol: str):
        """Get current snapshot, using cache and concurrency control."""
        async def _fetch():
            async with self._semaphore:
                return await self._real_fetch_snapshot(symbol)

        # Cache layer
        return await self._snapshot_cache.get_or_set(symbol, _fetch())

    def __init__(self, timeout: int = 30, ticker_cache_size: int = 512):
        """Initialize the YFinanceClient.

        Args:
            timeout (int, optional): The maximum time to wait for a response. Defaults to 30.
            ticker_cache_size (int, optional): The maximum number of cached ticker objects. Defaults
                to 512.

        """
        self._timeout = timeout
        self._get_ticker = lru_cache(maxsize=ticker_cache_size)(self._ticker_factory)

    def _ticker_factory(self, symbol: str) -> yf.Ticker:
        return yf.Ticker(symbol)

    async def _fetch_data(
        self, op: str, fetch_func: Callable[..., T], symbol: str, *args, **kwargs
    ) -> T:
        try:
            async with observe(op):
                return await asyncio.wait_for(
                    asyncio.to_thread(fetch_func, *args, **kwargs), self._timeout
                )
        except (ConnectionError, TimeoutError, asyncio.TimeoutError) as e:
            logger.warning(
                "yfinance.client.timeout", extra={"symbol": symbol, "op": op, "error": str(e)}
            )
            raise HTTPException(status_code=503, detail="Upstream timeout") from e
        except asyncio.CancelledError as e:
            logger.warning("yfinance.client.cancelled", extra={"symbol": symbol, "op": op})
            raise HTTPException(status_code=499, detail="Request cancelled") from e
        except HTTPException:
            # Re-raise HTTPExceptions produced by callers/other layers unchanged.
            raise
        except Exception as e:
            logger.exception(
                "yfinance.client.unexpected", extra={"symbol": symbol, "op": op, "error": str(e)}
            )
            raise HTTPException(status_code=500, detail="Unexpected error fetching data") from e

    def _normalize(self, symbol: str) -> str:
        return (symbol or "").upper().strip()

    async def get_info(self, symbol: str) -> YFinanceData | None:
        """Fetch information about a specific stock.

        Args:
            symbol (str): The stock symbol to fetch information for.

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            YFinanceData: The information about the stock.

        """
        symbol = self._normalize(symbol)
        ticker = self._get_ticker(symbol)
        info = await self._fetch_data("info", ticker.get_info, symbol)
        if not info:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "info"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        if not isinstance(info, dict):
            logger.warning(
                "yfinance.client.invalid_info_type", extra={"symbol": symbol, "type": type(info)}
            )
            raise HTTPException(status_code=502, detail="Malformed data from upstream")
        return info

    async def get_history(
        self, symbol: str, start: date | None, end: date | None
    ) -> pd.DataFrame | None:
        """Fetch historical market data for a specific stock.

        Args:
            symbol (str): The stock symbol to fetch historical data for.
            start (date | None): The start date for the historical data.
            end (date | None): The end date for the historical data.

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            pd.DataFrame: The historical market data for the stock.

        """
        symbol = self._normalize(symbol)
        ticker = self._get_ticker(symbol)
        history = await self._fetch_data("history", ticker.history, symbol, start=start, end=end)
        if history is None:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "history"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        if not isinstance(history, pd.DataFrame):
            logger.warning(
                "yfinance.client.invalid_history_type",
                extra={"symbol": symbol, "type": type(history)},
            )
            raise HTTPException(status_code=502, detail="Malformed data from upstream")
        if history.empty:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "history"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        return history

    async def ping(self) -> bool:
        """Check if the YFinance API is reachable.

        Returns:
            bool: True if the API is reachable, False otherwise.

        """
        probe_symbol = "AAPL"
        try:
            await self._fetch_data("ping", self._get_ticker(probe_symbol).get_info, probe_symbol)
            return True
        except HTTPException:
            return False
