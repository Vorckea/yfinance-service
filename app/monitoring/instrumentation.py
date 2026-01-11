"""Instrumentation utilities for monitoring yfinance operations."""

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Optional

from .metrics import YF_LATENCY, YF_REQUESTS


@asynccontextmanager
async def observe(
    op: str,
    outcome_on_error: str = "error",
    attempt: Optional[int] = None,
    max_attempts: Optional[int] = None,
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
        try:
            YF_REQUESTS.labels(operation=op, outcome="cancelled").inc()
        except Exception:
            pass
        raise
    except (asyncio.TimeoutError, TimeoutError):
        try:
            # only supported outcomes are:
            # success|error|timeout|cancelled (retry would create invalid cardinality)
            YF_REQUESTS.labels(operation=op, outcome="timeout").inc()
        except Exception:
            pass
        raise
    except Exception:
        try:
            YF_REQUESTS.labels(operation=op, outcome=outcome_on_error).inc()
        except Exception:
            pass
        raise
    else:
        try:
            YF_REQUESTS.labels(operation=op, outcome="success").inc()
        except Exception:
            pass
    finally:
        elapsed = time.monotonic() - start
        try:
            YF_LATENCY.labels(operation=op).observe(elapsed)
        except Exception:
            # never raise from metrics collection
            pass
