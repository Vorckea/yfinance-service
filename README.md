# YFinance Proxy Service

A FastAPI-based service that acts as a proxy for the [yfinance](https://github.com/ranaroussi/yfinance) Python library, enabling non-Python projects to access financial market data via HTTP endpoints.

## Features

- **Quote API**: Fetch latest market quotes for ticker symbols.
- **Historical API**: Retrieve historical market data for symbols over a date range.
- **Health Check**: Simple endpoint to verify service status.
- **Debug & Metrics**: Access logs, error logs, and basic service metrics.

## API Endpoints

### Quote
- `GET /quote/{symbol}`: Get the latest quote for a symbol.

### Historical
- `GET /historical/{symbol}?start_date=YYYY-MM-DD&end_date=YYYY-MM-DD`: Get historical data for a symbol within a date range.

### Health
- `GET /health`: Service health check.

### Debug
- `GET /debug/logs`: Retrieve all logs.
- `GET /debug/logs/errors`: Retrieve error logs.
- `GET /debug/metrics`: Get service metrics.

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

## Usage Example
Fetch the latest quote for Apple:
```sh
curl http://localhost:8000/quote/AAPL
```

## License
MIT License. See [LICENSE](LICENSE) for details.
