"""Main application entry point for the YFinance Proxy Service."""

import sys
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from app.features.earnings.router import router as earnings_router
from app.features.health.router import router as health_router
from app.features.historical.router import router as historical_router
from app.features.info.router import router as info_router
from app.features.quote.router import router as quote_router
from app.features.snapshot.router import router as snapshot_router
from app.monitoring.http_middleware import http_metrics_middleware
from app.monitoring.metrics import BUILD_INFO, SERVICE_UPTIME


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager to initialize application state."""
    app.state.start_time = time.time()
    contact_name = None
    contact_email = None
    if isinstance(app.contact, dict):  # FastAPI stores contact metadata
        contact_name = app.contact.get("name")
        contact_email = app.contact.get("email")
    BUILD_INFO.info(
        {
            "version": "0.0.20",
            "python_version": sys.version.split()[0],
            "contact_name": contact_name or "unknown",
            "contact_email": contact_email or "unknown",
        }
    )
    yield


app = FastAPI(
    title="YFinance Proxy Service",
    version="0.0.18",
    description=(
        "A FastAPI proxy for yfinance. Provides endpoints to fetch stock quotes and "
        "historical data."
    ),
    contact={
        "name": "Vorckea",
        "email": "akselschrader@gmail.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/license/MIT",
    },
    lifespan=lifespan,
)

# Unified logging + metrics middleware
app.middleware("http")(http_metrics_middleware)


@app.get("/metrics")
def metrics():
    """Endpoint to expose Prometheus metrics."""
    SERVICE_UPTIME.set(time.time() - app.state.start_time)
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


app.include_router(quote_router, prefix="/quote", tags=["quote"])
app.include_router(historical_router, prefix="/historical", tags=["historical"])
app.include_router(info_router, prefix="/info", tags=["info"])
app.include_router(snapshot_router, prefix="/snapshot", tags=["snapshot"])
app.include_router(earnings_router, prefix="/earnings", tags=["earnings"])

# Health check endpoint
app.include_router(health_router, tags=["health"])
