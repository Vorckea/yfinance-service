from typing import Annotated
from fastapi import APIRouter, Path, Depends
from app.clients.interface import YFinanceClientInterface
from app.utils.cache.interface import CacheInterface
from app.dependencies import get_yfinance_client, get_splits_cache
from .models import StockSplit
from .service import get_splits

router = APIRouter()

@router.get("/{symbol}", response_model=list[StockSplit])
async def read_splits(
    symbol: str = Path(..., min_length=1, max_length=10, pattern=r"^[A-Za-z0-9.-]+$"),
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)] = None,
    cache: Annotated[CacheInterface, Depends(get_splits_cache)] = None,
):
    return await get_splits(symbol.upper(), client, cache)