from fastapi import HTTPException
import pandas as pd

from ...clients.interface import YFinanceClientInterface
from ...utils.cache.interface import CacheInterface
from ...utils.logger import logger
from .models import StockSplit


async def get_splits(symbol: str, client: YFinanceClientInterface, cache: CacheInterface) -> list[StockSplit]:
    """Fetch stock splits with caching.
    
    Args:
        symbol: The stock symbol.
        client: YFinance client interface.
        cache: Cache for storing split data.
    
    Returns:
        List of StockSplit objects (empty if no splits found).
    """
    cached_data = await cache.get(symbol)
    if cached_data:
        logger.info("splits.cache.hit", extra={"symbol": symbol})
        return cached_data

    try:
        splits_series = await client.get_splits(symbol)
    except HTTPException as e:
        # Client raises 404 if no splits found - treat as empty list
        if e.status_code == 404:
            logger.info("splits.not_found", extra={"symbol": symbol})
            result = []
        else:
            # Re-raise other HTTP errors (500, 503, etc.)
            raise
    except Exception as e:
        logger.exception("splits.fetch.failed", extra={"symbol": symbol})
        raise HTTPException(status_code=500, detail="Failed to fetch split data") from e
    else:
        result = [
            StockSplit(date=str(pd.Timestamp(date).date()), ratio=float(ratio)) 
            for date, ratio in splits_series.items()
        ]

    await cache.set(symbol, result)
    return result