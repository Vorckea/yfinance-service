from typing import Annotated

from fastapi import APIRouter, Depends, Request

from app.clients.interface import YFinanceClientInterface
from app.common.validation import SymbolParam
from app.dependencies import get_splits_cache, get_yfinance_client
from app.utils.cache.interface import CacheInterface
from app.utils.helpers import normalize_symbol

from .models import StockSplit
from .service import get_splits

router = APIRouter()


@router.get("/{symbol}", response_model=list[StockSplit])
async def read_splits(
    request: Request,
    symbol: SymbolParam,
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)] = None,
    cache: Annotated[CacheInterface, Depends(get_splits_cache)] = None,
):
    no_cache = request.headers.get("Cache-Control") == "no-cache"
    symbol = normalize_symbol(symbol)
    if no_cache:
        return await get_splits(symbol, client, None)
    return await get_splits(symbol, client, cache)
