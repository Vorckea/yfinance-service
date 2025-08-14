"""Client for interacting with the Yahoo Finance API."""

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
    """Client for interacting with the Yahoo Finance API."""

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
        except Exception as e:
            logger.exception(
                "yfinance.client.unexpected", extra={"symbol": symbol, "op": op, "error": str(e)}
            )
            raise HTTPException(status_code=500, detail="Unexpected error fetching data")

    async def get_info(self, symbol: str) -> YFinanceData:
        """Fetch information about a specific stock.

        Args:
            symbol (str): The stock symbol to fetch information for.

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            YFinanceData: The information about the stock.

        """
        ticker = self._get_ticker(symbol)
        info = await self._fetch_data("info", ticker.get_info)
        if not info:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "info"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        return info

    async def get_history(self, symbol: str, start: date | None, end: date | None) -> pd.DataFrame:
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
        ticker = self._get_ticker(symbol)
        history = await self._fetch_data("history", ticker.history, start=start, end=end)
        if history.empty:
            logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "history"})
            raise HTTPException(status_code=404, detail=f"No data for {symbol}")
        return history

    async def ping(self) -> bool:
        """Check if the YFinance API is reachable.

        Returns:
            bool: True if the API is reachable, False otherwise.

        """
        try:
            self._get_ticker("AAPL")
            return True
        except Exception as e:
            logger.warning(
                "yfinance.client.ping_failed",
                extra={"error": str(e), "ticker": "AAPL"},
                exc_info=True,
            )
            return False
