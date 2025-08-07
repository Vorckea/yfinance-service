import logging

from fastapi import FastAPI, Response
from prometheus_client import generate_latest

from app.features.health.router import router as health_router
from app.features.historical.router import router as historical_router
from app.features.info.router import router as info_router
from app.features.quote.routes import router as quote_router
from app.monitoring.logging_middleware import LoggingMiddleware
from app.monitoring.middleware import prometheus_middleware

app = FastAPI(
    title="YFinance Proxy Service",
    version="1.0.0",
    description="A FastAPI proxy for yfinance. Provides endpoints to fetch stock quotes and "
    "historical data.",
    contact={
        "name": "Vorckea",
        "email": "askelschrader@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/MIT",
    },
)

app.add_middleware(LoggingMiddleware)
app.middleware("http")(prometheus_middleware)


@app.get("/metrics")
def metrics():
    """Endpoint to expose Prometheus metrics."""
    return Response(generate_latest(), media_type="text/plain")


app.include_router(quote_router, prefix="/quote", tags=["quote"])
app.include_router(historical_router, prefix="/historical", tags=["historical"])
app.include_router(info_router, prefix="/info", tags=["info"])

# Health check endpoint
app.include_router(health_router, tags=["health"])
