from fastapi import APIRouter, Path
from .models import StockSplit
from .service import get_splits

router = APIRouter()

@router.get("/{symbol}", response_model=list[StockSplit])
async def read_splits(
    symbol: str = Path(..., min_length=1, max_length=10, pattern=r"^[A-Z0-9.-]+$")
):
    return await get_splits(symbol.upper())