from app.clients.interface import YFinanceClientInterface
from app.utils.cache.interface import CacheInterface
from .models import StockSplit

async def get_splits(symbol: str, client: YFinanceClientInterface, cache: CacheInterface) -> list[StockSplit]:
    
    cached_data = await cache.get(symbol)
    if cached_data:
        return cached_data

    splits_series = await client.get_splits(symbol)

    result = [
        StockSplit(date=str(date.date()), ratio=float(ratio)) 
        for date, ratio in splits_series.items()
    ]

    await cache.set(symbol, result)
    return result