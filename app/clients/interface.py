"""Interface for a client that interacts with the Yahoo Finance API."""

from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd


class YFinanceClientInterface(ABC):
    """Interface for a client that interacts with the Yahoo Finance API."""

    @abstractmethod
    async def get_info(self, symbol: str) -> Mapping[str, Any]:
        """Fetch information about a specific stock."""
        pass

    @abstractmethod
    async def get_history(
        self, symbol: str, start: date | None, end: date | None, interval: str = "1d"
    ) -> pd.DataFrame | None:
        """Fetch historical market data for a specific stock."""
        pass

    @abstractmethod
    async def get_earnings(self, symbol: str, frequency: str = "quarterly") -> Any:
        """Fetch earnings-like data for a specific stock.

        Should return either:
         - a pandas.DataFrame (index = dates) with columns like:
            ['EPS Actual','EPS Estimate','Surprise','Surprise %','Revenue', ...]
         - or another Mapping that fetch_earnings() knows how to parse.
        """
        pass

    @abstractmethod
    async def get_income_statement(self, symbol: str, frequency: str) -> pd.DataFrame | None:
        """Fetch earnings data for a specific stock.

        Args:
            symbol: The stock symbol.
            frequency: 'quarterly' or 'annual'.

        Returns:
            A DataFrame or Mapping with earnings rows.

        """
        pass

    @abstractmethod
    async def get_calendar(self, symbol: str) -> Any:
        """Return ticker.calendar (may include Earnings Date)."""
        return {}

    @abstractmethod
    async def ping(self) -> bool:
        """Check if the client is working."""
        pass

    @abstractmethod
    async def get_splits(self, symbol: str) -> pd.Series:
        """Fetch historical stock splits for a specific stock."""
        pass