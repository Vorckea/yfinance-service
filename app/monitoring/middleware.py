import time

from fastapi import Request, Response

from ..monitoring.metrics import ERROR_COUNT, REQUEST_COUNT, REQUEST_LATENCY


async def prometheus_middleware(request: Request, call_next: callable) -> Response:
    """Track request metrics with low-cardinality labels using route templates.

    - Use the Starlette route template (e.g., "/quote/{symbol}") for the endpoint label.
    - Add method label for all metrics and status for error counter only.
    - Avoid high-cardinality labels by never using the raw request URL path.
    """
    if request.url.path == "/metrics":
        return await call_next(request)

    method = request.method
    start = time.perf_counter()
    status_code: int | None = None
    try:
        response = await call_next(request)
        status_code = response.status_code
        return response
    except Exception:
        status_code = 500
        raise
    finally:
        duration = time.perf_counter() - start
        route = request.scope.get("route")
        if route is None:
            endpoint = "__unmatched__"
        else:
            endpoint = getattr(route, "path_format", getattr(route, "path", request.url.path))

        REQUEST_COUNT.labels(endpoint=endpoint, method=method).inc()
        REQUEST_LATENCY.labels(endpoint=endpoint, method=method).observe(duration)

        if status_code is not None and status_code >= 400:
            ERROR_COUNT.labels(endpoint=endpoint, method=method, status=str(status_code)).inc()
