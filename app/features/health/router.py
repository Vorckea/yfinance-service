"""Health & readiness endpoints.

NOTE: TODOs capture richer diagnostics and improved readiness semantics.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from ...clients.interface import YFinanceClientInterface
from ...dependencies import get_yfinance_client
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
async def get_ready(client: Annotated[YFinanceClientInterface, Depends(get_yfinance_client)]):
    """Readiness check endpoint to verify yfinance is reachable."""
    if not await client.ping():
        raise HTTPException(status_code=503, detail="Not ready")
    return Response(
        content='{"status": "ready"}',
        status_code=200,
        media_type="application/json",
    )
    # TODO(readiness): Replace ad-hoc ticker instantiation with lightweight probe
    # and short-lived cached readiness state to reduce load.
