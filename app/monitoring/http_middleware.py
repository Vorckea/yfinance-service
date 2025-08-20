"""Unified HTTP middleware.

Provides:
    - Low-cardinality Prometheus metrics (requests, latency, in-progress, response size)
    - Correlation ID propagation (X-Correlation-ID)
    - Structured logging for success, slow, and error paths
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
SKIP_PATHS = ["/metrics", "/health", "/ready", "/openapi.json", "/docs", "/redoc"]


def _status_class(code: int) -> str:
    return f"{code // 100}xx"


def _extract_route(request: Request) -> str:
    route_obj = request.scope.get("route")
    return getattr(route_obj, "path_format", getattr(route_obj, "path", "__unmatched__"))


def _get_body_size(response: Response) -> int:
    if getattr(response, "body", None) is not None:
        return len(response.body)
    content_length = response.headers.get("content-length")
    if content_length:
        try:
            return int(content_length)
        except ValueError:
            pass
    return 0


async def http_metrics_middleware(request: Request, call_next: Callable) -> Response:
    """Middleware to collect metrics & structured logs.

    Increments global in-progress immediately so concurrency is visible, then after
    processing resolves the templated route path for labeled metrics.
    Skips /metrics and /health endpoints to avoid recursion/noise.
    """
    if request.url.path in SKIP_PATHS:
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

    route = _extract_route(request)
    duration = time.perf_counter() - start
    status_class = _status_class(response.status_code)
    body_size = _get_body_size(response)

    HTTP_INPROGRESS.labels(route=route, method=method).inc()
    HTTP_REQUEST_DURATION.labels(route=route, method=method).observe(duration)
    HTTP_REQUESTS.labels(route=route, method=method, status_class=status_class).inc()
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
