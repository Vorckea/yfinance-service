# YFinance Proxy Service

A FastAPI-based service that acts as a proxy for the [yfinance](https://github.com/ranaroussi/yfinance) Python library, enabling non-Python projects to access financial market data via HTTP endpoints.

## Features

- **Quote API**: Fetch latest market quotes for ticker symbols.
- **Historical API**: Retrieve historical market data for symbols over a date range.
- **Health Check**: Simple endpoint to verify service status.
- **Prometheus Metrics**: `/metrics` endpoint for monitoring request count, errors, and latency.

## API Endpoints

### Quote
- `GET /quote/{symbol}`: Get the latest quote for a symbol.

### Historical
- `GET /historical/{symbol}?start=YYYY-MM-DD&end=YYYY-MM-DD`: Get historical data for a symbol within a date range.

### Health
- `GET /health`: Service health check.

### Metrics
- `GET /metrics`: Prometheus metrics endpoint (request count, error count, latency).

## Monitoring with Prometheus

This service exposes metrics at `/metrics` in Prometheus format.  
To use with Prometheus, see the provided `docker-compose.yml` and `prometheus.yml` for a quick setup.

**Example Prometheus Query for Latency:**
```
rate(request_latency_seconds_sum[5m]) / rate(request_latency_seconds_count[5m])
```

## Setup & Installation

### Using Poetry
```sh
poetry install
poetry run uvicorn app.main:app --reload
```

### Using Docker
```sh
docker build -t yfinance-service .
docker run -p 8000:8000 yfinance-service
```

### Using Docker Compose (with Prometheus)
```sh
docker compose up --build
```
- Access the API at [http://localhost:8000](http://localhost:8000)
- Access Prometheus at [http://localhost:9090](http://localhost:9090)

## Usage Example
Fetch the latest quote for Apple:
```sh
curl http://localhost:8000/quote/AAPL
```

## License
MIT License. See [LICENSE](LICENSE) for details.

## Author
Aksel Heggland Schrader (@Vorckea)