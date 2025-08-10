from prometheus_client import Counter, Gauge, Histogram

REQUEST_COUNT = Counter(
    "request_count_total",
    "Total HTTP requests",
    ["endpoint", "method"],
)
ERROR_COUNT = Counter(
    "error_count_total",
    "Total errors",
    ["endpoint", "method", "status"],
)
REQUEST_LATENCY = Histogram(
    "request_latency_seconds",
    "Request latency in seconds",
    ["endpoint", "method"],
)

SERVICE_UPTIME = Gauge(
    "service_uptime_seconds",
    "Service uptime in seconds since start",
)
