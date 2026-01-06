"""Historical data endpoint definitions.

Backlog TODOs inline track pagination, validation, and rate limiting improvements.
"""

from datetime import date
from typing import Annotated, Literal, get_args

from fastapi import APIRouter, Depends, HTTPException
from fastapi.params import Query

from ...auth import check_api_key
from ...clients.interface import YFinanceClientInterface
from ...common.validation import SymbolParam
from ...dependencies import get_yfinance_client
from .models import HistoricalResponse
from .service import fetch_historical

router = APIRouter(dependencies=[Depends(check_api_key)])

ALLOWED_INTERVALS = Literal[
    "1m",
    "2m",
    "5m",
    "15m",
    "30m",
    "60m",
    "90m",
    "1h",
    "1d",
    "1wk",
    "1mo",
    "3mo",
]


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
                                "timestamp": "2023-01-01T14:30:00Z",
                                "open": 150.0,
                                "high": 155.0,
                                "low": 148.0,
                                "close": 154.0,
                                "volume": 1000000,
                            },
                            {
                                "date": "2023-01-02",
                                "timestamp": "2023-01-02T15:30:00Z",
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
    interval: ALLOWED_INTERVALS = Query(
        "1d",
        description=f"Data aggregation interval. Allowed: {', '.join(get_args(ALLOWED_INTERVALS))}",
        examples={"default": {"summary": "Interval", "value": "1d"}},
    ),
) -> HistoricalResponse:
    """Return historical OHLCV data for the symbol in the optional date range.

    TODO(perf): Add optional interval parameter (1d,1h, etc.).
    """
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start must be before or equal to end")

    # `interval` is validated by Pydantic/FastAPI via the `ALLOWED_INTERVALS_LITERAL` type alias.
    return await fetch_historical(symbol, start, end, client, interval=interval)
