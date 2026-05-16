"""Instrumentation utilities for monitoring yfinance operations."""

import asyncio
import time
from contextlib import asynccontextmanager

from .metrics import YF_LATENCY, YF_REQUESTS, YF_UPSTREAM_ERROR_LATENCY, safe_metric_call


@asynccontextmanager
async def observe(
    op: str,
    outcome_on_error: str = "error",
    attempt: int | None = None,
    max_attempts: int | None = None,
):
    """Observe a yfinance operation for metrics.

    Args:
        op (str): Operation name (e.g., 'quote', 'info')
        outcome_on_error (str, optional): Outcome label for errors. Defaults to "error".
        attempt (int, optional): Current attempt number (0-indexed) for retry tracking.
        max_attempts (int, optional): Total number of attempts for this operation.

    """
    start = time.monotonic()
    try:
        yield
    except asyncio.CancelledError:
        # cancelled should propagate after recording
        safe_metric_call(YF_REQUESTS.labels(operation=op, outcome="cancelled").inc)
        raise
    except (asyncio.TimeoutError, TimeoutError):
        elapsed = time.monotonic() - start
        # Label as 'retry' if not the last attempt, otherwise 'timeout'
        if attempt is not None and max_attempts is not None and attempt < max_attempts - 1:
            outcome = "retry"
        else:
            outcome = "timeout"

        safe_metric_call(YF_REQUESTS.labels(operation=op, outcome=outcome).inc)
        safe_metric_call(YF_UPSTREAM_ERROR_LATENCY.labels(operation=op, outcome=outcome).observe, elapsed)
        raise
    except Exception:
        elapsed = time.monotonic() - start
        safe_metric_call(YF_REQUESTS.labels(operation=op, outcome=outcome_on_error).inc)
        safe_metric_call(
            YF_UPSTREAM_ERROR_LATENCY.labels(operation=op, outcome=outcome_on_error).observe,
            elapsed,
        )
        raise
    else:
        safe_metric_call(YF_REQUESTS.labels(operation=op, outcome="success").inc)
    finally:
        elapsed = time.monotonic() - start
        safe_metric_call(YF_LATENCY.labels(operation=op).observe, elapsed)
