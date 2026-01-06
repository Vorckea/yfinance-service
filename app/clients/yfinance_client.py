"""Client for interacting with the Yahoo Finance API."""

import asyncio
from collections.abc import Callable
from datetime import date
from typing import Any, Dict, TypeVar

import pandas as pd
import yfinance as yf
from fastapi import HTTPException

from app.clients.interface import YFinanceClientInterface
from app.utils.cache import TTLCache

from ..monitoring.instrumentation import observe
from ..utils.logger import logger

YFinanceData = dict[str, Any]
T = TypeVar("T")


class YFinanceClient(YFinanceClientInterface):
    """Client for interacting with the Yahoo Finance API."""

    def __init__(
        self, 
        timeout: int = 30, 
        ticker_cache_size: int = 512,
        ticker_cache_ttl: int = 60):
        """Initialize the YFinanceClient.

        Args:
            timeout (int, optional): The maximum time to wait for a response. Defaults to 30.
            ticker_cache_size (int, optional): The maximum number of cached ticker objects. Defaults
                to 256.

        """
        self._timeout = timeout
        self._ticker_cache = TTLCache(
            size=ticker_cache_size,
            ttl=ticker_cache_ttl,
            cache_name="ticker_cache",
            resource="ticker"
        )

    def _ticker_factory(self, symbol: str) -> yf.Ticker:
        return yf.Ticker(symbol)
    
    async def _get_ticker(self, symbol: str) -> yf.Ticker:
        """Get a ticker from cache or create a new one."""
        cached = await self._ticker_cache.get(symbol)
        if cached is not None:
            return cached
        
        ticker = self._ticker_factory(symbol)
        await self._ticker_cache.set(symbol, ticker)
        return ticker

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

    async def get_info(self, symbol: str) -> YFinanceData:
        """Fetch information about a specific stock.

        Args:
            symbol (str): The stock symbol to fetch information for.

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            YFinanceData: The information about the stock.

        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker(symbol)
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
        self, symbol: str, start: date | None, end: date | None, interval: str = "1d"
    ) -> pd.DataFrame | None:
        """Fetch historical market data for a specific stock.

        Args:
            symbol (str): The stock symbol to fetch historical data for.
            start (date | None): The start date for the historical data.
            end (date | None): The end date for the historical data.
            interval (str): The data interval (e.g., "1d", "1h", "1wk"). Defaults to "1d".

        Raises:
            HTTPException: If the symbol is not found or if there is an error fetching data.

        Returns:
            pd.DataFrame: The historical market data for the stock.

        """
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker(symbol)
        history = await self._fetch_data(
            "history", ticker.history, symbol, start=start, end=end, interval=interval
        )
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

    async def get_earnings(self, symbol: str, frequency: str = "quarterly") -> pd.DataFrame | None:
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker(symbol)

        try:
            if hasattr(ticker, "get_earnings"):
                df = await self._fetch_data(
                    "get_earnings",
                    lambda: ticker.get_earnings(
                        freq=frequency if frequency == "quarterly" else "annual"
                    ),
                    symbol,
                )
                if df is not None and (isinstance(df, pd.DataFrame) and not df.empty):
                    return df

            if hasattr(ticker, "earnings_dates"):
                df2 = await self._fetch_data(
                    "earnings_dates", lambda: ticker.earnings_dates, symbol
                )
                if df2 is not None and not df2.empty:
                    df2 = df2.reset_index().rename(columns={"index": "earnings_date"})

                    df2 = df2.set_index("earnings_date")
                    return df2

            if hasattr(ticker, "quarterly_earnings"):
                q = await self._fetch_data(
                    "quarterly_earnings", lambda: ticker.quarterly_earnings, symbol
                )
                if q is not None and isinstance(q, pd.DataFrame) and not q.empty:
                    return q
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "yfinance.client.earnings_try_failed", extra={"symbol": symbol, "error": str(e)}
            )

        try:
            if frequency == "annual":
                stmt = await self._fetch_data("income_stmt", lambda: ticker.income_stmt, symbol)
            else:
                stmt = await self._fetch_data(
                    "quarterly_income_stmt", lambda: ticker.quarterly_income_stmt, symbol
                )

            if stmt is None or stmt.empty:
                return None

            df_stmt = stmt.T.copy()
            df_stmt.index.name = "earnings_date"

            return df_stmt
        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "yfinance.client.income_stmt_failed", extra={"symbol": symbol, "error": str(e)}
            )
            return None

    async def get_income_statement(self, symbol: str, frequency: str) -> pd.DataFrame | None:
        return await self.get_earnings(symbol, frequency)

    async def get_calendar(self, symbol: str) -> Dict[str, Any]:
        symbol = self._normalize(symbol)
        ticker = await self._get_ticker(symbol)

        try:
            calendar_data = await self._fetch_data(
                op="calendar",
                fetch_func=lambda: ticker.calendar,
                symbol=symbol,
            )

            if calendar_data is None:
                logger.info("yfinance.client.no_data", extra={"symbol": symbol, "op": "calendar"})
                raise HTTPException(status_code=404, detail=f"No calendar data for {symbol}")

            if not isinstance(calendar_data, dict):
                logger.warning(
                    "yfinance.client.invalid_calendar_type",
                    extra={"symbol": symbol, "type": type(calendar_data)},
                )
                raise HTTPException(status_code=502, detail="Malformed data from upstream")

            return calendar_data

        except HTTPException:
            raise
        except Exception as e:
            logger.warning(
                "yfinance.client.calendar_failed", extra={"symbol": symbol, "error": str(e)}
            )
            raise HTTPException(status_code=500, detail="Failed to fetch calendar data") from e

    async def ping(self) -> bool:
        """Check if the YFinance API is reachable.

        Returns:
            bool: True if the API is reachable, False otherwise.

        """
        probe_symbol = "AAPL"
        try:
            ticker = await self._get_ticker(probe_symbol) 
            await self._fetch_data("ping", ticker.get_info, probe_symbol)
            return True
        except HTTPException:
            return False
