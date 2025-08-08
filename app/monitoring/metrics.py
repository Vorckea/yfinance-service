from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "request_count",
    "Total HTTP requests",
    ["endpoint", "method"],
)
ERROR_COUNT = Counter(
    "error_count",
    "Total errors",
    ["endpoint", "method", "status"],
)
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
)
