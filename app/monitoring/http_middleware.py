"""Unified HTTP middleware.

Provides:
    - Low-cardinality Prometheus metrics (requests, latency, in-progress, response size)
    - Correlation ID propagation (X-Correlation-ID)
    - Structured logging for success, slow, and error paths

Supersedes the separate `LoggingMiddleware` and `prometheus_middleware`.
"""

from __future__ import annotations

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response

from ..utils.logger import logger
from .metrics import (
    HTTP_INPROGRESS,
    HTTP_INPROGRESS_TOTAL,
    HTTP_REQUEST_DURATION,
    HTTP_REQUESTS,
    HTTP_RESPONSE_SIZE,
)

SLOW_THRESHOLD_SECONDS = 10
CORRELATION_HEADER = "X-Correlation-ID"


def _status_class(code: int) -> str:
    return f"{code // 100}xx"


async def http_metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to collect metrics & structured logs.

    Increments global in-progress immediately so concurrency is visible, then after
    processing resolves the templated route path for labeled metrics.
    Skips /metrics and /health endpoints to avoid recursion/noise.
    """
    if request.url.path == "/metrics" or request.url.path == "/health":
        return await call_next(request)

    start = time.perf_counter()
    method = request.method
    # Route will be resolved after routing (post call_next) to avoid '__unmatched__'.

    # Correlation ID
    cid = request.headers.get(CORRELATION_HEADER, str(uuid.uuid4()))
    request.state.correlation_id = cid

    # Increment total in-progress immediately (route unknown yet)
    HTTP_INPROGRESS_TOTAL.inc()
    try:
        response = await call_next(request)
    except Exception:
        route_obj = request.scope.get("route")
        route = getattr(route_obj, "path_format", getattr(route_obj, "path", "__unmatched__"))
        duration = time.perf_counter() - start
        # Per-route in-progress is very brief for error path but recorded for consistency
        HTTP_INPROGRESS.labels(route=route, method=method).inc()
        HTTP_INPROGRESS.labels(route=route, method=method).dec()
        HTTP_REQUEST_DURATION.labels(route=route, method=method).observe(duration)
        HTTP_REQUESTS.labels(route=route, method=method, status_class="5xx").inc()
        logger.exception(
            "Unhandled exception",
            extra={"cid": cid, "route": route, "method": method, "latency": duration},
        )
        raise
    finally:
        HTTP_INPROGRESS_TOTAL.dec()

    route_obj = request.scope.get("route")
    route = getattr(route_obj, "path_format", getattr(route_obj, "path", "__unmatched__"))

    duration = time.perf_counter() - start
    HTTP_INPROGRESS.labels(route=route, method=method).inc()
    status_class = _status_class(response.status_code)
    HTTP_REQUEST_DURATION.labels(route=route, method=method).observe(duration)
    HTTP_REQUESTS.labels(route=route, method=method, status_class=status_class).inc()

    body_size = 0
    if hasattr(response, "body") and response.body is not None:
        body_size = len(response.body)
    elif "content-length" in response.headers:
        try:
            body_size = int(response.headers["content-length"])
        except ValueError:
            pass
    HTTP_RESPONSE_SIZE.labels(route=route, method=method).observe(body_size)

    response.headers[CORRELATION_HEADER] = cid
    if duration >= SLOW_THRESHOLD_SECONDS:
        logger.warning(
            "Slow request",
            extra={
                "cid": cid,
                "route": route,
                "method": method,
                "status_code": response.status_code,
                "latency": duration,
                "threshold": SLOW_THRESHOLD_SECONDS,
            },
        )
    logger.info(
        "Request completed",
        extra={
            "cid": cid,
            "route": route,
            "method": method,
            "status_code": response.status_code,
            "latency": duration,
            "response_size": body_size,
        },
    )
    HTTP_INPROGRESS.labels(route=route, method=method).dec()
    return response
