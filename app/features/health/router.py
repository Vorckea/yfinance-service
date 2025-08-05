import yfinance as yf
from fastapi import APIRouter, Response

from ...utils.logger import logger

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description="Returns the health status of the service.",
    operation_id="getHealthStatus",
    responses={
        200: {
            "description": "Service is running",
            "content": {"application/json": {"example": {"status": "ok"}}},
        }
    },
)
async def get_health():
    """Health check endpoint to verify service is running."""
    return {"status": "ok"}


@router.get(
    "/ready",
    summary="Readiness Check",
    description="Checks if the service can reach yfinance.",
    operation_id="getReadinessStatus",
    responses={
        200: {
            "description": "Service is ready",
            "content": {"application/json": {"example": {"status": "ready"}}},
        },
        503: {
            "description": "Service is not ready",
            "content": {"application/json": {"example": {"status": "not ready"}}},
        },
    },
)
async def get_ready():
    """Readiness check endpoint to verify yfinance is reachable."""
    try:
        ticker = yf.Ticker("AAPL")
        info = ticker.info
        if not info:
            return Response(
                content='{"status": "not ready"}',
                status_code=503,
                media_type="application/json",
            )
    except Exception as e:
        logger.error(
            f"YFinance is not reachable ({type(e).__name__}): {e}",
            exc_info=True,
            extra={"ticker": "AAPL"},
        )
        return Response(
            content='{"status": "not ready"}',
            status_code=503,
            media_type="application/json",
        )
    return Response(
        content='{"status": "ready"}',
        status_code=200,
        media_type="application/json",
    )
