"""Metrics endpoint integration test.

Ensures hitting quote, info, and historical endpoints produces labeled Prometheus
samples (http_requests_total and yfinance_requests_total) using templated route
paths instead of raw URIs.
"""

import re

import pandas as pd


def _find_metric_line(metrics_text: str, pattern: str) -> str | None:
    regex = re.compile(pattern)
    for line in metrics_text.splitlines():
        if regex.search(line):
            return line
    return None


def test_metrics_for_quote_info_historical(client, mocker):
    """Hit core endpoints and verify Prometheus metrics contain expected labeled samples."""
    # Mock yfinance.Ticker behaviour used by endpoints
    mock_ticker = mocker.patch("yfinance.Ticker")
    mock_instance = mock_ticker.return_value
    # quote/info use .info
    mock_instance.info = {
        "regularMarketPrice": 123.45,
        "regularMarketPreviousClose": 120.0,
        "regularMarketOpen": 121.0,
        "regularMarketDayHigh": 124.0,
        "regularMarketDayLow": 119.5,
        "regularMarketVolume": 1000,
        "shortName": "Apple Inc.",
        "longName": "Apple Inc.",
        "exchange": "NASDAQ",
        "sector": "Technology",
        "industry": "Hardware",
        "country": "US",
        "website": "https://example.com",
        "longBusinessSummary": "Summary",
        "marketCap": 1,
        "sharesOutstanding": 1,
        "currentPrice": 123.45,
        "trailingPE": 10.0,
        "beta": 1.0,
        "address1": "Addr",
    }
    # historical uses .history
    mock_instance.history.return_value = pd.DataFrame(
        {
            "Open": [1.0],
            "High": [2.0],
            "Low": [0.5],
            "Close": [1.5],
            "Volume": [10],
        },
        index=pd.to_datetime(["2024-08-01"]),
    )

    # Exercise endpoints
    assert client.get("/quote/AAPL").status_code == 200
    assert client.get("/info/AAPL").status_code == 200
    assert client.get("/historical/AAPL").status_code == 200

    # Fetch metrics
    metrics_resp = client.get("/metrics")
    assert metrics_resp.status_code == 200
    text = metrics_resp.text

    # HTTP request counters (route label should use templated path)
    assert _find_metric_line(
        text,
        r'http_requests_total\{route="/quote/\{symbol\}",method="GET",status_class="2xx"}\s+\d+',
    ), "Missing quote route metric"
    assert _find_metric_line(
        text,
        r'http_requests_total\{route="/info/\{symbol\}",method="GET",status_class="2xx"}\s+\d+',
    ), "Missing info route metric"
    assert _find_metric_line(
        text,
        r'http_requests_total\{route="/historical/\{symbol\}",method="GET",status_class="2xx"}\s+\d+',
    ), "Missing historical route metric"

    # yfinance counters (operations)
    assert _find_metric_line(
        text, r'yfinance_requests_total\{operation="quote_info",outcome="success"}\s+\d+'
    ), "Missing quote_info yfinance metric"
    assert _find_metric_line(
        text, r'yfinance_requests_total\{operation="info_detail",outcome="success"}\s+\d+'
    ), "Missing info_detail yfinance metric"
    assert _find_metric_line(
        text, r'yfinance_requests_total\{operation="history",outcome="success"}\s+\d+'
    ), "Missing history yfinance metric"
