"""Prometheus metric definitions for the service.

Includes HTTP request/latency/size gauges and yfinance-specific metrics. Also exposes
global and per-route in-progress gauges to observe concurrency.
"""

from prometheus_client import Counter, Gauge, Histogram, Info

HTTP_REQUESTS = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ("route", "method", "status_class"),
)

HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "Request latency (seconds)",
    ("route", "method"),
    buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2, 5),
)

HTTP_INPROGRESS = Gauge(
    "http_inprogress_requests",
    "Number of in-progress HTTP requests",
    ("route", "method"),
)

# Global in-progress (no labels) to show real-time concurrency even before
# route resolution occurs.
HTTP_INPROGRESS_TOTAL = Gauge(
    "http_inprogress_total",
    "Total number of in-progress HTTP requests (all routes)",
)

HTTP_RESPONSE_SIZE = Histogram(
    "http_response_size_bytes",
    "Response size (bytes)",
    ("route", "method"),
    buckets=(200, 500, 1_000, 5_000, 10_000, 50_000, 100_000, 500_000, 1_000_000),
)

SERVICE_UPTIME = Gauge(
    "process_uptime_seconds",
    "Service uptime in seconds since start",
)

BUILD_INFO = Info(
    "build_info",
    "Build information",
)

YF_REQUESTS = Counter(
    "yfinance_requests_total",
    "Total yfinance fetch attempts",
    ("operation", "outcome"),  # outcome: success|error|timeout|circuit_open
)

YF_LATENCY = Histogram(
    "yfinance_request_duration_seconds",
    "Latency of yfinance operations",
    ("operation",),
    buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10),
)

CACHE_HITS = Counter(
    "cache_hits_total",
    "Cache hits",
    ("cache", "resource"),
)
CACHE_MISSES = Counter(
    "cache_misses_total",
    "Cache misses",
    ("cache", "resource"),
)
