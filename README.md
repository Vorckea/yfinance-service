# YFinance Proxy Service

![Build Status](https://img.shields.io/github/actions/workflow/status/Vorckea/yfinance-service/ci.yml?branch=main)
![Coverage](https://img.shields.io/badge/coverage-83%25-brightgreen)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.116%2B-009688?logo=fastapi)
![License](https://img.shields.io/github/license/Vorckea/yfinance-service)
![Docker](https://img.shields.io/badge/docker-ghcr.io/vorckea/yfinance--service-blue)
[![Stars](https://img.shields.io/github/stars/Vorckea/yfinance-service?style=social)](https://github.com/Vorckea/yfinance-service)
![Release](https://img.shields.io/github/v/release/Vorckea/yfinance-service)


> *A lightweight* ***FastAPI*** microservice that wraps [yfinance](https://github.com/ranaroussi/yfinance), exposing **RESTful endpoints** for market data, perfect for **non-Python projects**, **microservice architectures**, and **monitorable deployments**.

## Why Use This?
- **Language-agnostic**: Get Yahoo Finance data via HTTP, no python dependency.
- **Production-ready**: Includes Prometheus metrics and health checks.
- **Simple setup**: Run with Docker, Poetry, or Docker Compose (Grafana/Prometheus included).
- **Extendable**: Built on FastAPI; easy to add routes or middleware.
- **Caching & Multithread**: Faster, more reliable responses. 

## Features
| Feature                | Description                                             |
| ---------------------- | ------------------------------------------------------- |
| **Quote API**          | Fetch latest market quotes (OHLCV) for ticker symbols.  |
| **Historical API**     | Retrieve historical data within a date range.           |
| **Info API**           | Get company fundamentals (sector, market cap, etc.).    |
| **Health Check**       | Simple `/health` endpoint to verify service status.     |
| **Prometheus Metrics** | `/metrics` endpoint for request count, errors, latency. |

## API Endpoints

| Endpoint                                                   | Description               | Example                                            |
| ---------------------------------------------------------- | ------------------------- | -------------------------------------------------- |
| `GET /quote/{symbol}`                                      | Latest quote for a symbol | `/quote/AAPL`                                      |
| `GET /historical/{symbol}?start=YYYY-MM-DD&end=YYYY-MM-DD` | Historical OHLCV data     | `/historical/AAPL?start=2024-01-01&end=2024-02-01` |
| `GET /info/{symbol}`                                       | Company details           | `/info/TSLA`                                       |
| `GET /health`                                              | Health check              | `/health`                                          |
| `GET /metrics`                                             | Prometheus metrics        | `/metrics`                                         |

## Quick Start

### Run with Docker
```sh
docker pull ghcr.io/vorckea/yfinance-service:latest
docker run -p 8000:8000 ghcr.io/vorckea/yfinance-service:latest
```

Then visit:
http://localhost:8000/docs: Interactive Swagger UI

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
- Grafana → http://localhost:3000

Relevant files:
- Prometheus config: monitoring/infra/prometheus.yml
- Alert rules: monitoring/infra/alert.rules.yml
- Dashboards: monitoring/dashboards/



## Usage Example

Get the latest quote for Apple:
```sh
curl http://localhost:8000/quote/AAPL
```

Get company info for Tesla:

```sh
curl http://localhost:8000/info/TSLA
```

## Monitoring Example:
Prometheus query for average latency (5-minute window):
```promql
rate(request_latency_seconds_sum[5m]) / rate(request_latency_seconds_count[5m])

```

## Contributing
Contributions are welcome!
- Open an issue for bugs or new features.
- Look for **good first issue** labels to get started.
- Please see [CONTRIBUTING.md](CONTRIBUTING.md)

## License

MIT License. See [LICENSE](LICENSE) for details.

## Author

Aksel Heggland Schrader (@Vorckea)