from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.params import Path, Query

from .models import HistoricalResponse
from .service import fetch_historical

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=HistoricalResponse,
    summary="Get historical data for a symbol",
    description="Returns historical market data for the given ticker symbol within the specified "
    "date range.",
)
async def get_historical(
    symbol: str = Path(..., description="Ticker symbol", example="AAPL"),
    start: date | None = Query(
        None, description="Start date in YYYY-MM-DD format", example="2023-01-01"
    ),
    end: date | None = Query(
        None, description="End date in YYYY-MM-DD format", example="2023-12-31"
    ),
) -> HistoricalResponse:
    try:
        return await fetch_historical(symbol, start, end)
    except HTTPException as e:
        raise e
