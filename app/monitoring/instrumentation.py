import time
from contextlib import contextmanager

from .metrics import YF_LATENCY, YF_REQUESTS


@contextmanager
def observe(op: str, outcome_on_error: str = "error"):
    """Observe a yfinance operation for metrics.

    Args:
        op (str): Operation name (e.g., 'quote', 'info')
        outcome_on_error (str, optional): Outcome label for errors. Defaults to "error".

    """
    start = time.perf_counter()
    try:
        yield
        YF_REQUESTS.labels(operation=op, outcome="success").inc()
    except Exception:
        YF_REQUESTS.labels(operation=op, outcome=outcome_on_error).inc()
        raise
    finally:
        YF_LATENCY.labels(operation=op).observe(time.perf_counter() - start)
