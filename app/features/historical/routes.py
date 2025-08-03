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
    operation_id="getHistoricalDataBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "historical_data": [
                            {
                                "date": "2023-01-01",
                                "open": 150.0,
                                "high": 155.0,
                                "low": 148.0,
                                "close": 154.0,
                                "volume": 1000000,
                            },
                            {
                                "date": "2023-01-02",
                                "open": 154.0,
                                "high": 156.0,
                                "low": 152.0,
                                "close": 155.0,
                                "volume": 1200000,
                            },
                        ],
                    }
                }
            },
        },
        400: {"description": "Invalid symbol or date range"},
        404: {"description": "Symbol not found"},
    },
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
