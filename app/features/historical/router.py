from datetime import date

from fastapi import APIRouter, HTTPException
from fastapi.params import Query

from ...common.validation import SymbolParam
from .models import HistoricalResponse
from .service import fetch_historical

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=HistoricalResponse,
    response_model_exclude_none=True,
    summary="Get historical data for a symbol",
    description=(
        "Returns historical market data for the given ticker symbol within the specified date "
        "range."
    ),
    operation_id="getHistoricalDataBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "prices": [
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
    symbol: SymbolParam,
    start: date | None = Query(None, description="Start date (YYYY-MM-DD)", example="2023-01-01"),
    end: date | None = Query(None, description="End date (YYYY-MM-DD)", example="2023-12-31"),
) -> HistoricalResponse:
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")
    return await fetch_historical(symbol, start, end)
