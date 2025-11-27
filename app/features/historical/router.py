"""Historical data endpoint definitions.

Backlog TODOs inline track pagination, validation, and rate limiting improvements.
"""

from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query

from ...clients.interface import YFinanceClientInterface
from ...common.validation import SymbolParam
from ...dependencies import get_yfinance_client
from .models import HistoricalResponse
from .service import fetch_historical

router = APIRouter()

ALLOWED_INTERVALS = ("1h", "1d", "1wk", "1mo")


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
        400: {"description": "Invalid date range (start > end)"},
        404: {"description": "No historical data found for symbol"},
        422: {"description": "Validation error (invalid symbol format)"},
        500: {"description": "Internal server error"},
    },
)
async def get_historical(
    symbol: SymbolParam,
    client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)],
    start: date | None = Query(
        None,
        description="Start date (YYYY-MM-DD)",
        examples={"default": {"summary": "Start date", "value": "2023-01-01"}},
    ),
    end: date | None = Query(
        None,
        description="End date (YYYY-MM-DD)",
        examples={"default": {"summary": "End date", "value": "2023-12-31"}},
    ),
    interval: Literal["1h", "1d", "1wk", "1mo"] = Query(
        "1d",
        description='Data aggregation interval ("1h", "1d", "1wk", "1mo")',
        examples={"default": {"summary": "Interval", "value": "1d"}},
    ),
) -> HistoricalResponse:
    """Return historical OHLCV data for the symbol in the optional date range.

    TODO(perf): Add optional interval parameter (1d,1h, etc.).
    """
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")

    if interval not in ALLOWED_INTERVALS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported interval '{interval}'. Allowed: {', '.join(ALLOWED_INTERVALS)}",
        )
    return await fetch_historical(symbol, start, end, client, interval=interval)
