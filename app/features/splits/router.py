from typing import Annotated
from fastapi import APIRouter, Depends
from app.clients.interface import YFinanceClientInterface
from app.utils.cache.interface import CacheInterface
from app.dependencies import get_yfinance_client, get_splits_cache
from .models import StockSplit
from .service import get_splits
from app.common.validation import SymbolParam

router = APIRouter()

@router.get("/{symbol}", response_model=list[StockSplit])
async def read_splits(
    symbol: SymbolParam,
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)],
    cache: Annotated[CacheInterface, Depends(get_splits_cache)],
):
    return await get_splits(symbol.upper(), client, cache)