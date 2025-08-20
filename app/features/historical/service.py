import asyncio
from datetime import date

import pandas as pd

from ...clients.interface import YFinanceClientInterface
from ...utils.logger import logger
from .models import HistoricalPrice, HistoricalResponse


def _map_history(df: pd.DataFrame) -> list[HistoricalPrice]:
    if getattr(df.index, "tz", None) is not None:
        df = df.tz_convert(None)
    df_selected = df[["Open", "High", "Low", "Close", "Volume"]]
    return [
        HistoricalPrice(
            date=ts.date(),
            open=float(open_),
            high=float(high_),
            low=float(low_),
            close=float(close_),
            volume=int(volume_) if pd.notna(volume_) else None,
        )
        for ts, open_, high_, low_, close_, volume_ in df_selected.itertuples(index=True, name=None)
    ]


async def fetch_historical(
    symbol: str, start: date | None, end: date | None, client: YFinanceClientInterface
) -> HistoricalResponse:
    """Fetch historical stock data for a given symbol."""
    logger.info("historical.fetch.request", extra={"symbol": symbol, "start": start, "end": end})

    df = await client.get_history(symbol, start, end)

    logger.info("historical.fetch.success", extra={"symbol": symbol, "rows": len(df)})

    prices = await asyncio.to_thread(_map_history, df)

    return HistoricalResponse(symbol=symbol.upper(), prices=prices)
