import asyncio
import time
from contextlib import asynccontextmanager

from .metrics import YF_LATENCY, YF_REQUESTS


@asynccontextmanager
async def observe(op: str, outcome_on_error: str = "error"):
    """Observe a yfinance operation for metrics.

    Args:
        op (str): Operation name (e.g., 'quote', 'info')
        outcome_on_error (str, optional): Outcome label for errors. Defaults to "error".

    """
    start = time.monotonic()
    try:
        yield
    except asyncio.CancelledError as exc:
        # cancelled should propagate after recording
        try:
            YF_REQUESTS.labels(operation=op, outcome="cancelled").inc()
        except Exception:
            pass
        raise
    except (asyncio.TimeoutError, TimeoutError):
        try:
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
