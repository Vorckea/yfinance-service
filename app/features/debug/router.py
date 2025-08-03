from fastapi import APIRouter
from log_store import log_store

router = APIRouter()


@router.get("/logs", summary="Get service logs", response_model=list[dict])
async def get_logs():
    return log_store.get_all()


@router.get("/logs/errors", summary="Get error logs", response_model=list[dict])
async def get_error_logs():
    return log_store.get_errors()


@router.get("/health", summary="Check service health", response_model=dict)
async def health():
    return {"status": "healthy", "uptime": "2 hours", "last_error": log_store.last_error()}


@router.get("/metrics", summary="Get service metrics", response_model=dict)
async def get_metrics():
    return {
        "total_requests": 1234,
        "error_count": log_store.error_count,
    }
