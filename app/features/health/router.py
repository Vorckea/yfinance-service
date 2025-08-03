from fastapi import APIRouter

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
