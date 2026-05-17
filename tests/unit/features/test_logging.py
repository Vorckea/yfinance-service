"""Tests for request logging and correlation propagation."""

import io
import logging

from app.utils.logger import RequestContextFilter


def test_request_correlation_id_echoed_and_logged(client, mock_yfinance_client):
    """Requests should echo the correlation ID header and attach it to request logs."""
    correlation_id = "cid-test-123"
    mock_yfinance_client.get_info.return_value = {
        "symbol": "AAPL",
        "regularMarketPrice": 150.0,
        "regularMarketPreviousClose": 148.0,
        "regularMarketOpen": 149.0,
        "regularMarketDayHigh": 151.0,
        "regularMarketDayLow": 147.5,
        "regularMarketVolume": 1000000,
    }

    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.addFilter(RequestContextFilter())
    handler.setFormatter(logging.Formatter("%(message)s [cid=%(correlation_id)s]"))
    root_logger = logging.getLogger()
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)

    try:
        response = client.get("/quote/AAPL", headers={"X-Correlation-ID": correlation_id})
    finally:
        root_logger.removeHandler(handler)

    assert response.status_code == 200
    assert response.headers["X-Correlation-ID"] == correlation_id
    log_output = stream.getvalue()
    assert f"Request started [cid={correlation_id}]" in log_output
    assert f"quote.fetch.start [cid={correlation_id}]" in log_output
    assert f"Request completed [cid={correlation_id}]" in log_output
