# YFinance Service — Stock Market API | yfinance REST API | Yahoo Finance Docker Container
<!-- ALL-CONTRIBUTORS-BADGE:START - Do not remove or modify this section -->
[![All Contributors](https://img.shields.io/badge/all_contributors-4-orange.svg?style=flat-square)](#contributors-)
<!-- ALL-CONTRIBUTORS-BADGE:END -->

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
| **News API**           | Get news about company 
| **Earnings API**       | Retrieve normalized earnings history with EPS, revenue, and surprise data.    |
| **Snapshot API**       | Combined info + quote in a single request with caching. |
| **Splits API**         |	Retrieve historical stock split data (dates and ratios) for ticker symbols.  |
| **Health Check**       | `/health` and `/ready` endpoints for liveness & readiness probes. |
| **Prometheus Metrics** | `/metrics` endpoint for request count, errors, latency, cache stats. |

## API Endpoints

| Endpoint                                                   | Description               | Example                                            |
| ---------------------------------------------------------- | ------------------------- | -------------------------------------------------- |
| `GET /quote/{symbol}`                                      | Latest quote for a symbol | `/quote/AAPL`                                      |
| `GET /quote?symbols=SYM1,SYM2`                             | Bulk quotes (CSV)         | `/quote?symbols=AAPL,MSFT`                         |
| `GET /historical/{symbol}?start=&end=&interval=`           | Historical OHLCV data     | `/historical/AAPL?start=2024-01-01&end=2024-02-01&interval=1d` |
| `GET /info/{symbol}`                                       | Company details           | `/info/TSLA`                                       |
| `GET /news/{symbol}?count={count}&tab={tab}` | Company news (Allowed tab values are `news` (default), `press-releases` and `all`) | `/news/TSLA?count=5&tab=news` |
| `GET /health`                                              | Health check              | `/health`                                          |
| `GET /metrics`                                             | Prometheus metrics        | `/metrics`                                         |
| `GET /earnings/{symbol}?frequency={period}`        | Earnings history (EPS, revenue, surprise) | `/earnings/AAPL?frequency=quarterly` |
| `GET /snapshot/{symbol}`                                   | Combined info + quote     | `/snapshot/AAPL`                                   |
| `GET /ready`                                               | Readiness check (yfinance connectivity) | `/ready`                             |
| `GET /splits/{symbol}	`                                    | List of stock splits (date and ratio) for the given symbol  | `/splits/AAPL`   |

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
|---|---|----|---|
| `LOG_LEVEL` | Logging level (CRITICAL/ERROR/WARNING/INFO/DEBUG/NOTSET) | `INFO` | `LOG_LEVEL=DEBUG` |
| `MAX_BULK_CONCURRENCY` | Max concurrent requests for bulk quote endpoint | `10` | `MAX_BULK_CONCURRENCY=20` |
| `EARNINGS_CACHE_TTL` | Cache TTL for earnings data in seconds (0 = disable caching) | `3600` | `EARNINGS_CACHE_TTL=1800` |
| `EARNINGS_CACHE_MAXSIZE` | Max entries for earnings cache | `128` | `EARNINGS_CACHE_MAXSIZE=256` |
| `INFO_CACHE_TTL` | Cache TTL for company info (seconds) | `300` | `INFO_CACHE_TTL=300` |
| `INFO_CACHE_MAXSIZE` | Max entries for info cache | `256` | `INFO_CACHE_MAXSIZE=512` |
| `CORS_ENABLED` | Enable CORS | `False` | `CORS_ENABLED=True` |
| `CORS_ALLOWED_ORIGINS` | Allowed origins (comma-separated list) | `*` (Any) | `CORS_ALLOWED_ORIGINS="https://example.org,https://www.example.org"` |
| `SPLITS_CACHE_TTL` |Time-to-live (in seconds) for the stock splits cache| `3600` | `SPLITS_CACHE_TTL=1800` |
| `API_KEY_ENABLED` | Enable API key authentication | `False` | `API_KEY_ENABLED=True` |
| `API_KEY` | API key for authentication (required if enabled) | `""` | `API_KEY=your-secret-key-here` |

### API Key Authentication

Optionally protect endpoints with API key authentication:

```bash
# Enable authentication
API_KEY_ENABLED=true
API_KEY=your-secret-key-here
```

**Usage:**
```bash
# Include API key in X-API-Key header
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/quote/AAPL
```
**Protected endpoints:**
- `/quote/*` - Stock quotes
- `/historical/*` - Historical data
- `/info/*` - Company information
- `/snapshot/*` - Combined snapshots
- `/earnings/*` - Earnings data

**Unprotected endpoints:**
- `/health`, `/ready` - Health checks
- `/metrics` - Prometheus metrics
- `/docs`, `/redoc` - API documentation

### Examples

Running natively (example)
```bash
# Increase bulk quote concurrency to 20
MAX_BULK_CONCURRENCY=20 poetry run uvicorn app.main:app

# Disable earnings caching
EARNINGS_CACHE_TTL=0 poetry run uvicorn app.main:app

# Reduce earnings cache to 30 minutes
EARNINGS_CACHE_TTL=1800 poetry run uvicorn app.main:app

# Enable API key authentication
API_KEY_ENABLED=true API_KEY=my-secret-key poetry run uvicorn app.main:app
```

Docker compose (example)
```yaml
services:
  yfinance-service:
    build: .
    image: ghcr.io/vorckea/yfinance-service:latest
    env_file: .env       # local use only; do not commit secrets to repo
    environment:
      - LOG_LEVEL=INFO
      - MAX_BULK_CONCURRENCY=10
      - EARNINGS_CACHE_TTL=3600
      - API_KEY_ENABLED=true
      - API_KEY=${API_KEY}  # Load from .env file or environment
    ports:
      - "8000:8000"
```

Kubernetes (example)
```yaml
# secret.yaml (sensitive values like API keys)
apiVersion: v1
kind: Secret
metadata:
  name: yfinance-secret
type: Opaque
stringData:
  API_KEY: "your-secret-key-here"

# configmap.yaml (non-sensitive configuration)
apiVersion: v1
kind: ConfigMap
metadata:
  name: yfinance-config
data:
  LOG_LEVEL: "INFO"
  MAX_BULK_CONCURRENCY: "10"
  EARNINGS_CACHE_TTL: "3600"
  API_KEY_ENABLED: "true"

# deployment.yaml (connects ConfigMap as env vars and uses a Secret for sensitive values)
apiVersion: apps/v1
kind: Deployment
metadata:
  name: yfinance-service
spec:
  replicas: 1
  selector:
    matchLabels:
      app: yfinance-service
  template:
    metadata:
      labels:
        app: yfinance-service
    spec:
      containers:
        - name: yfinance-service
          image: ghcr.io/vorckea/yfinance-service:latest
          ports:
            - containerPort: 8000
          envFrom:
            - configMapRef:
                name: yfinance-config
            - secretRef:
                name: yfinance-secret
          readinessProbe:
            httpGet:
              path: /ready
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8000
            initialDelaySeconds: 15
            periodSeconds: 20
```

## Usage Example

Get the latest quote for Apple:
```sh
# Without authentication (if API_KEY_ENABLED=false)
curl http://localhost:8000/quote/AAPL

# With authentication (if API_KEY_ENABLED=true)
curl -H "X-API-Key: your-secret-key-here" http://localhost:8000/quote/AAPL
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
## Contributors ✨

Thanks goes to these wonderful people ([emoji key](https://allcontributors.org/docs/en/emoji-key)):

<!-- ALL-CONTRIBUTORS-LIST:START - Do not remove or modify this section -->
<!-- prettier-ignore-start -->
<!-- markdownlint-disable -->
<table>
  <tbody>
    <tr>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Vorckea"><img src="https://avatars.githubusercontent.com/u/97853282?v=4?s=75" width="75px;" alt="Aksel Heggland Schrader"/><br /><sub><b>Aksel Heggland Schrader</b></sub></a><br /><a href="https://github.com/Vorckea/yfinance-service/commits?author=Vorckea" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Jarvis2001"><img src="https://avatars.githubusercontent.com/u/40858007?v=4?s=75" width="75px;" alt="Makarand More"/><br /><sub><b>Makarand More</b></sub></a><br /><a href="https://github.com/Vorckea/yfinance-service/commits?author=Jarvis2001" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/LaryStef"><img src="https://avatars.githubusercontent.com/u/120743460?v=4?s=75" width="75px;" alt="Tim"/><br /><sub><b>Tim</b></sub></a><br /><a href="https://github.com/Vorckea/yfinance-service/commits?author=LaryStef" title="Code">💻</a></td>
      <td align="center" valign="top" width="14.28%"><a href="https://github.com/Warkstee"><img src="https://avatars.githubusercontent.com/u/89970432?v=4?s=75" width="75px;" alt="Warkstee"/><br /><sub><b>Warkstee</b></sub></a><br /><a href="https://github.com/Vorckea/yfinance-service/commits?author=Warkstee" title="Code">💻</a></td>
    </tr>
  </tbody>
  <tfoot>
    <tr>
      <td align="center" size="13px" colspan="7">
        <img src="https://raw.githubusercontent.com/all-contributors/all-contributors-cli/1b8533af435da9854653492b1327a23a4dbd0a10/assets/logo-small.svg">
          <a href="https://all-contributors.js.org/docs/en/bot/usage">Add your contributions</a>
        </img>
      </td>
    </tr>
  </tfoot>
</table>

<!-- markdownlint-restore -->
<!-- prettier-ignore-end -->

<!-- ALL-CONTRIBUTORS-LIST:END -->

This project follows the [all-contributors](https://github.com/all-contributors/all-contributors) specification. Contributions of any kind welcome!