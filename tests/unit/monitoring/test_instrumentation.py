"""Tests for yfinance instrumentation metrics."""

import asyncio

import pytest

from app.monitoring.instrumentation import observe
from app.monitoring.metrics import YF_REQUESTS, YF_UPSTREAM_ERROR_LATENCY


def _histogram_sample_value(metric, suffix: str) -> float:
    metric_family = next(iter(metric.collect()))
    target_name = f"{metric_family.name}_{suffix}"
    for sample in metric_family.samples:
        if sample.name == target_name:
            return sample.value
    raise AssertionError(f"Missing histogram sample {target_name}")


@pytest.mark.asyncio
async def test_observe_records_upstream_timeout_histogram():
    metric = YF_UPSTREAM_ERROR_LATENCY.labels(operation="info", outcome="timeout")
    counter = YF_REQUESTS.labels(operation="info", outcome="timeout")
    before_sum = _histogram_sample_value(metric, "sum")
    before_count = _histogram_sample_value(metric, "count")
    before_counter = counter._value.get()

    with pytest.raises(asyncio.TimeoutError):
        async with observe("info", attempt=0, max_attempts=1):
            raise asyncio.TimeoutError()

    assert _histogram_sample_value(metric, "count") == before_count + 1
    assert _histogram_sample_value(metric, "sum") >= before_sum
    assert counter._value.get() == before_counter + 1


@pytest.mark.asyncio
async def test_observe_records_upstream_error_histogram_with_labels():
    metric = YF_UPSTREAM_ERROR_LATENCY.labels(operation="news", outcome="error")
    counter = YF_REQUESTS.labels(operation="news", outcome="error")
    before_sum = _histogram_sample_value(metric, "sum")
    before_count = _histogram_sample_value(metric, "count")
    before_counter = counter._value.get()

    with pytest.raises(RuntimeError):
        async with observe("news"):
            raise RuntimeError("boom")

    assert _histogram_sample_value(metric, "count") == before_count + 1
    assert _histogram_sample_value(metric, "sum") >= before_sum
    assert counter._value.get() == before_counter + 1
