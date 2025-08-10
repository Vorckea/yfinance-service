from fastapi import APIRouter

from ...common.validation import SymbolParam
from .models import InfoResponse
from .service import fetch_info

router = APIRouter()


@router.get(
    "/{symbol}",
    response_model=InfoResponse,
    summary="Get information for a symbol",
    description="Returns detailed information about the company for the given ticker symbol.",
    operation_id="getInfoBySymbol",
    responses={
        200: {
            "description": "Successful Response",
            "content": {
                "application/json": {
                    "example": {
                        "symbol": "AAPL",
                        "short_name": "Apple Inc.",
                        "long_name": "Apple Inc.",
                        "exchange": "NASDAQ",
                        "sector": "Technology",
                        "industry": "Consumer Electronics",
                        "country": "United States",
                        "website": "https://www.apple.com",
                        "description": (
                            "Apple Inc. designs, manufactures, and markets consumer electronics, "
                            "software, and services."
                        ),
                        "market_cap": 2500000000000,
                        "shares_outstanding": 16000000000,
                        "dividend_yield": 0.006,
                        "fifty_two_week_high": 175.0,
                        "fifty_two_week_low": 120.0,
                        "current_price": 150.0,
                        "trailing_pe": 28.0,
                        "beta": 1.2,
                        "ceo": "Tim Cook",
                        "address": "1 Apple Park Way, Cupertino, CA 95014, USA",
                    }
                }
            },
        },
        404: {"description": "No info data found for symbol"},
        422: {"description": "Validation error (invalid symbol format)"},
        499: {"description": "Request cancelled by client"},
        500: {"description": "Internal server error"},
        503: {"description": "Upstream timeout"},
    },
)
async def get_info(symbol: SymbolParam) -> InfoResponse:
    """Get detailed information about a company for a given ticker symbol."""
    return await fetch_info(symbol)
