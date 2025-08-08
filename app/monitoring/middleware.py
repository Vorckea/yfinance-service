from fastapi import Request, Response

from ..monitoring.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY


async def prometheus_middleware(request: Request, call_next: callable) -> Response:
    """Middleware to track request metrics for Prometheus using route templates and low-cardinality labels."""
    route = request.scope.get("route")
    endpoint = getattr(route, "path_format", getattr(route, "path", request.url.path))
    method = request.method
    REQUEST_COUNT.labels(endpoint=endpoint, method=method).inc()
    with REQUEST_LATENCY.labels(endpoint=endpoint, method=method).time():
        response = await call_next(request)
    status = str(response.status_code)
    if response.status_code >= 400:
        ERROR_COUNT.labels(endpoint=endpoint, method=method, status=status).inc()
    return response
