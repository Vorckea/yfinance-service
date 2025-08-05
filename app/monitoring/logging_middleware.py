"""Logging middleware for Starlette/FastAPI applications."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from ..utils.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware to log requests and responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        """Log the request and response details.

        Exceptions during request processing are logged before being re-raised.
        """
        start_time = time.time()
        logger.info(
            f"Request: {request.method} {request.url.path}",
            extra={"method": request.method, "path": request.url.path},
        )
        try:
            response: Response = await call_next(request)
        except Exception as e:
            logger.exception(
                "Unhandled exception occurred during request",
                extra={"method": request.method, "path": request.url.path},
            )
            raise
        process_time = time.time() - start_time
        logger.info(
            f"Response: {request.method} {request.url.path} {response.status_code} ({process_time:.3f}s)",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "process_time": process_time,
            },
        )
        return response
