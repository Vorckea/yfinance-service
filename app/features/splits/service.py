import os
import time
from functools import wraps
from app.clients.yfinance_client import YFinanceClient
from .models import StockSplit

# Environment-controlled TTL (Defaults to 1 hour)
SPLITS_CACHE_TTL = int(os.getenv("SPLITS_CACHE_TTL", 3600))

def local_ttl_cache(ttl: int):
    _cache = {}
    def decorator(func):
        @wraps(func)
        async def wrapper(symbol: str, *args, **kwargs):
            now = time.time()
            if symbol in _cache:
                result, timestamp = _cache[symbol]
                if now - timestamp < ttl:
                    return result
            result = await func(symbol, *args, **kwargs)
            _cache[symbol] = (result, now)
            return result
        return wrapper
    return decorator

_client = YFinanceClient()

@local_ttl_cache(ttl=SPLITS_CACHE_TTL)
async def get_splits(symbol: str) -> list[StockSplit]:
    splits_series = await _client.get_splits(symbol)
    if splits_series is None or splits_series.empty:
        return []

    return [
        StockSplit(date=str(date.date()), ratio=float(ratio)) 
        for date, ratio in splits_series.items()
    ]