from abc import ABC, abstractmethod
from datetime import date

import pandas as pd


class YFinanceClientInterface(ABC):
    @abstractmethod
    async def get_info(self, symbol: str) -> dict[str, object]:
        """Fetch information about a specific stock."""
        pass

    @abstractmethod
    async def get_history(self, symbol: str, start: date, end: date) -> pd.DataFrame:
        """Fetch historical market data for a specific stock."""
        pass

    @abstractmethod
    async def ping(self) -> bool:
        """Check if the client is working."""
        pass
