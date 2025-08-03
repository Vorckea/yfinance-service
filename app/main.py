import logging

from fastapi import FastAPI

from app.features.debug.router import router as debug_router
from app.features.health.router import router as health_router
from app.features.historical.routes import router as historical_router
from app.features.quote.routes import router as quote_router

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
app.include_router(quote_router, prefix="/quote", tags=["quote"])
app.include_router(historical_router, prefix="/historical", tags=["historical"])

# Health check endpoint
app.include_router(health_router, tags=["health"])
app.include_router(debug_router, prefix="/debug", tags=["debug"])

logging.basicConfig(level=logging.INFO)
