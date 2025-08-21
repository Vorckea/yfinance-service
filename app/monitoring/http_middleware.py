"""Unified HTTP middleware.

Provides:
    - Low-cardinality Prometheus metrics (requests, latency, in-progress, response size)
    - Correlation ID propagation (X-Correlation-ID)
    - Structured logging for success, slow, and error paths
"""

import time
import uuid
from collections.abc import Callable

from fastapi import Request, Response
from starlette.routing import Match

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


def _extract_route_best_effort(request: Request) -> str:
    try:
        route = request.scope.get("route")
        if route is not None:
            return getattr(route, "path_format", getattr(route, "path", request.url.path))
        for r in request.app.router.routes:
            match, _ = r.matches(request.scope)
            if match is Match.FULL:
                return getattr(r, "path_format", getattr(r, "path", request.url.path))
    except Exception:
        pass
    return request.url.path


def _get_body_size(response: Response) -> int:
    try:
        body = getattr(response, "body", None)
        if isinstance(body, (bytes, bytearray)):
            return len(body)
        content_length = response.headers.get("content-length")
        if content_length:
            try:
                return int(content_length)
            except (ValueError, TypeError):
                pass
    except Exception:
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

    # Correlation ID
    cid = request.headers.get(CORRELATION_HEADER, str(uuid.uuid4()))
    request.state.correlation_id = cid

    route = _extract_route_best_effort(request)

    try:
        HTTP_INPROGRESS_TOTAL.inc()
    except Exception:
        pass

    per_route_inc = False

    try:
        try:
            HTTP_INPROGRESS.labels(route=route, method=method).inc()
            per_route_inc = True
        except Exception:
            per_route_inc = False

        response = await call_next(request)
    except Exception:
        duration = time.perf_counter() - start
        try:
            HTTP_REQUEST_DURATION.labels(route=route, method=method).observe(duration)
        except Exception:
            pass
        try:
            HTTP_REQUESTS.labels(route=route, method=method, status_class="5xx").inc()
        except Exception:
            pass
        logger.exception(
            "Unhandled exception",
            extra={"cid": cid, "route": route, "method": method, "latency": duration},
        )
        raise
    finally:
        try:
            if per_route_inc:
                HTTP_INPROGRESS.labels(route=route, method=method).dec()
        except Exception:
            pass
        try:
            HTTP_INPROGRESS_TOTAL.dec()
        except Exception:
            pass

    duration = time.perf_counter() - start
    status_class = _status_class(response.status_code)
    body_size = _get_body_size(response)

    try:
        HTTP_REQUEST_DURATION.labels(route=route, method=method).observe(duration)
    except Exception:
        pass
    try:
        HTTP_REQUESTS.labels(route=route, method=method, status_class=status_class).inc()
    except Exception:
        pass
    try:
        HTTP_RESPONSE_SIZE.labels(route=route, method=method).observe(body_size)
    except Exception:
        pass

    try:
        response.headers[CORRELATION_HEADER] = cid
    except Exception:
        pass

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
    else:
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

    return response
