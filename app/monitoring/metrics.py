from prometheus_client import Counter, Histogram

REQUEST_COUNT = Counter(
    "request_count",
    "Total HTTP requests",
    ["endpoint"],
)
ERROR_COUNT = Counter(
    "error_count",
    "Total errors",
    ["endpoint"],
)
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["endpoint"],
)
