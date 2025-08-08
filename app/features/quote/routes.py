from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Path

from .models import QuoteResponse
from .service import fetch_quote

router = APIRouter()

SymbolParam = Annotated[
    str,
    Path(
        ...,
        description="Ticker symbol",
        example="AAPL",
        pattern=r"^[A-Za-z0-9\.\-]{1,10}$",
    ),
]


@router.get(
    "/{symbol}",
    response_model=QuoteResponse,
    response_model_exclude_none=True,
    summary="Get latest quote for a symbol",
    description="Returns the latest market quote for the given ticker symbol.",
    operation_id="getQuoteBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "current_price": 150.0,
                        "previous_close": 148.0,
                        "open": 149.0,
                        "high": 151.0,
                        "low": 147.5,
                        "volume": 1000000,
                    }
                }
            },
        },
        400: {"description": "Invalid symbol"},
        404: {"description": "Symbol not found"},
        422: {"description": "Unprocessable Entity"},
    },
)
async def get_quote(
    symbol: SymbolParam,
) -> QuoteResponse:
    """Get the latest market quote for a given ticker symbol."""
    return await fetch_quote(symbol)
