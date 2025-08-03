from fastapi import APIRouter

router = APIRouter()


@router.get(
    "/health",
    summary="Health Check",
    description="Returns the health status of the service.",
)
async def get_health():
    """Health check endpoint to verify service is running."""
    return {"status": "ok"}
