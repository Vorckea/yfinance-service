from typing import Annotated

from fastapi import APIRouter, Depends

from app.clients.interface import YFinanceClientInterface
from app.common.validation import SymbolParam
from app.dependencies import get_splits_cache, get_yfinance_client
from app.utils.cache.interface import CacheInterface

from ...auth import check_api_key
from .models import StockSplit
from .service import get_splits

router = APIRouter(dependencies=[Depends(check_api_key)])


@router.get("/{symbol}", response_model=list[StockSplit])
async def read_splits(
    symbol: SymbolParam,
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)] = None,
    cache: Annotated[CacheInterface, Depends(get_splits_cache)] = None,
):
    return await get_splits(symbol.upper(), client, cache)
