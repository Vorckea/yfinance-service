import time

from fastapi import APIRouter

from ...state import service_start_time
from .log_store import log_store

router = APIRouter()


@router.get("/logs", summary="Get service logs", response_model=list[dict])
async def get_logs():
    return log_store.get_all()


@router.get("/logs/errors", summary="Get error logs", response_model=list[dict])
async def get_error_logs():
    return log_store.get_errors()


@router.get("/health", summary="Check service health", response_model=dict)
async def health():
    uptime_seconds = int(time.time() - service_start_time)
    hours, remainder = divmod(uptime_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    uptime = f"{int(hours)}h {int(minutes)}m {int(seconds)}s"
    return {"status": "healthy", "uptime": uptime, "last_error": log_store.last_error()}


@router.get("/metrics", summary="Get service metrics", response_model=dict)
async def get_metrics():
    return {
        "total_requests": 0,
        "error_count": log_store.error_count,
    }
