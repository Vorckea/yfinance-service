from fastapi import Request

from ..monitoring.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY


async def prometheus_middleware(request: Request, call_next):
    endpoint = request.url.path
    REQUEST_COUNT.labels(endpoint=endpoint).inc()
    with REQUEST_LATENCY.labels(endpoint=endpoint).time():
        response = await call_next(request)
    if response.status_code >= 400:
        ERROR_COUNT.labels(endpoint=endpoint).inc()
    return response
