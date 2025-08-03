from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.params import Query

from .models import HistoricalResponse
from .service import fetch_historical

router = APIRouter()


@router.get("/{symbol}", response_model=HistoricalResponse)
async def get_historical(
    symbol: str,
    start: date | None = Query(None, description="Start date in YYYY-MM-DD format"),
    end: date | None = Query(None, description="End date in YYYY-MM-DD format"),
) -> HistoricalResponse:
    try:
        return await fetch_historical(symbol, start, end)
    except HTTPException as e:
        raise e
