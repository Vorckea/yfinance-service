from fastapi import Request, Response

from ..monitoring.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY


async def prometheus_middleware(request: Request, call_next: callable) -> Response:
    """Middleware to track request metrics for Prometheus."""
    path = request.url.path
    REQUEST_COUNT.labels(endpoint=path).inc()
    with REQUEST_LATENCY.labels(endpoint=path).time():
        response = await call_next(request)
    # Track error responses (status code 400 and above)
    if response.status_code >= 400:
        ERROR_COUNT.labels(endpoint=path).inc()
    return response
