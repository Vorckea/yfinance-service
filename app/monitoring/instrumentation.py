import asyncio
import time
from contextlib import contextmanager

from fastapi import HTTPException

from .metrics import YF_LATENCY, YF_REQUESTS


@contextmanager
def observe(op: str, outcome_on_error: str = "error"):
    start = time.perf_counter()
    try:
        yield
        YF_REQUESTS.labels(operation=op, outcome="success").inc()
    except Exception:
        YF_REQUESTS.labels(operation=op, outcome=outcome_on_error).inc()
        raise
    finally:
        YF_LATENCY.labels(operation=op).observe(time.perf_counter() - start)
