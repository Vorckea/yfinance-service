# YFinance Service — Stock Market API | yfinance REST API | Yahoo Finance Docker Container

[![Build Status](https://img.shields.io/github/actions/workflow/status/Vorckea/yfinance-service/ci.yml?branch=main)](https://github.com/Vorckea/yfinance-service/actions)
[![Coverage](https://img.shields.io/badge/coverage-83%25-brightgreen)](https://github.com/Vorckea/yfinance-service)
[![Python](https://img.shields.io/badge/python-3.13%2B-blue?logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.124%2B-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/github/license/Vorckea/yfinance-service)](LICENSE)
[![Docker](https://img.shields.io/badge/docker-ghcr.io/vorckea/yfinance--service-2496ED?logo=docker)](https://ghcr.io/vorckea/yfinance-service)
[![Stars](https://img.shields.io/github/stars/Vorckea/yfinance-service?style=social)](https://github.com/Vorckea/yfinance-service)
[![Release](https://img.shields.io/github/v/release/Vorckea/yfinance-service)](https://github.com/Vorckea/yfinance-service/releases)


> *A lightweight* ***FastAPI*** microservice that wraps [yfinance](https://github.com/ranaroussi/yfinance), exposing **RESTful finance API** endpoints and a ready-to-run **yfinance Docker container** for production deployments. Ideal for **non-Python projects**, **microservice architectures**, and **monitorable deployments**.

## Why Use This?
- **Language-agnostic HTTP API**: Expose Yahoo Finance data to any platform without embedding Python.
- **Containerized deployment**: Ready Docker image and compose stack for Prometheus + Grafana.
- **Extendable FastAPI app**: Easy to add routes, middleware, or auth.
- **Caching & instrumentation**: Includes a TTL in-memory cache with async locks and Prometheus metrics.
- **Robust yfinance wrapper**: Calls are wrapped with timeouts, `lru_cache` ticker caching, and async-to-thread execution to reduce upstream variability.
- **Observability**: `/metrics` endpoint and sample Grafana dashboards for latency, cache, and error monitoring.

## Features
| Feature                | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| **Quote API**          | Fetch latest market quotes (OHLCV) for ticker symbols.  |
| **Historical API**     | Retrieve historical data with flexible intervals (1h, 1d, 1wk, 1mo). |
| **Info API**           | Get company fundamentals (sector, market cap, etc.).    |
| **Earnings API**       | Retrieve normalized earnings history with EPS, revenue, and surprise data.    |
| **Snapshot API**       | Combined info + quote in a single request with caching. |
| **Health Check**       | `/health` and `/ready` endpoints for liveness & readiness probes. |
| **Prometheus Metrics** | `/metrics` endpoint for request count, errors, latency, cache stats. |

## API Endpoints

| Endpoint                                                   | Description               | Example                                            |
| ---------------------------------------------------------- | ------------------------- | -------------------------------------------------- |
| `GET /quote/{symbol}`                                      | Latest quote for a symbol | `/quote/AAPL`                                      |
| `GET /quote?symbols=SYM1,SYM2`                             | Bulk quotes (CSV)         | `/quote?symbols=AAPL,MSFT`                         |
| `GET /historical/{symbol}?start=&end=&interval=`           | Historical OHLCV data     | `/historical/AAPL?start=2024-01-01&end=2024-02-01&interval=1d` |
| `GET /info/{symbol}`                                       | Company details           | `/info/TSLA`                                       |
| `GET /health`                                              | Health check              | `/health`                                          |
| `GET /metrics`                                             | Prometheus metrics        | `/metrics`                                         |
| `GET /earnings/{symbol}?frequency={period}`        | Earnings history (EPS, revenue, surprise) | `/earnings/AAPL?frequency=quarterly` |
| `GET /snapshot/{symbol}`                                   | Combined info + quote     | `/snapshot/AAPL`                                   |
| `GET /ready`                                               | Readiness check (yfinance connectivity) | `/ready`                             |

## Quick Start

### Run with Docker
```sh
docker pull ghcr.io/vorckea/yfinance-service:latest
docker run -p 8000:8000 ghcr.io/vorckea/yfinance-service:latest
```

Then visit:
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Local Development (Poetry)
```sh
poetry install
poetry run uvicorn app.main:app --reload
```

### With Prometheus + Grafana
```sh
docker compose up --build
```

Access:
- API: http://localhost:8000
- Prometheus: http://localhost:9090
- Grafana: http://localhost:3000

Relevant files:
- Prometheus config: `monitoring/infra/prometheus.yml`
- Alert rules: `monitoring/infra/alert.rules.yml`
- Dashboards: `monitoring/grafana/dashboards/`

## Configuration

### Environment Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `MAX_BULK_CONCURRENCY` | Max concurrent requests for bulk quote endpoint | 10 | `MAX_BULK_CONCURRENCY=20` |
| `EARNINGS_CACHE_TTL` | Cache TTL for earnings data in seconds (0 = disable) | 3600 | `EARNINGS_CACHE_TTL=1800` |

### Examples

```bash
# Increase bulk quote concurrency to 20
MAX_BULK_CONCURRENCY=20 poetry run uvicorn app.main:app

# Disable earnings caching
EARNINGS_CACHE_TTL=0 poetry run uvicorn app.main:app

# Reduce earnings cache to 30 minutes
EARNINGS_CACHE_TTL=1800 poetry run uvicorn app.main:app
```

## Usage Example

Get the latest quote for Apple:
```sh
curl http://localhost:8000/quote/AAPL
```

**Response:**
```json
{
  "symbol": "AAPL",
  "current_price": 178.72,
  "previous_close": 177.49,
  "open_price": 177.52,
  "high": 179.63,
  "low": 176.21,
  "volume": 62456800
}
```

Fetch quotes for multiple symbols:

```sh
curl http://localhost:8000/quote?symbols=AAPL,MSFT,GOOGL
```

Get company info for Tesla:

```sh
curl http://localhost:8000/info/TSLA
```

Fetch quarterly earnings for Apple:

```sh
curl http://localhost:8000/earnings/AAPL?frequency=quarterly
```

Fetch annual earnings for Apple:

```sh
curl http://localhost:8000/earnings/AAPL?frequency=annual
```

## Monitoring Example
Prometheus query for average latency (5-minute window):
```promql
rate(http_request_duration_seconds_sum[5m]) / rate(http_request_duration_seconds_count[5m])
```

## Contributing
Contributions are welcome!
- Open an issue for bugs or new features.
- Look for **good first issue** labels to get started.
- Please see [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Aksel Heggland Schrader ([@Vorckea](https://github.com/Vorckea))

---

**Keywords**: yfinance docker, yahoo finance api, stock market api, yfinance rest api, yfinance microservice, stock data api, financial data api, python finance api, fastapi stock api