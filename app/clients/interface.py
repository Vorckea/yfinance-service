from abc import ABC, abstractmethod
from collections.abc import Mapping
from datetime import date
from typing import Any

import pandas as pd


class YFinanceClientInterface(ABC):
    @abstractmethod
    async def get_info(self, symbol: str) -> Mapping[str, Any] | None:
        """Fetch information about a specific stock."""
        pass

    @abstractmethod
    async def get_history(self, symbol: str, start: date | None, end: date | None) -> pd.DataFrame | None:
        """Fetch historical market data for a specific stock."""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Check if the client is working."""
        pass