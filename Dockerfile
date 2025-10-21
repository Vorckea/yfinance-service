# --- Stage 1: Builder ---
FROM python:3.14-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    POETRY_VERSION=2.1.3 \
    PYTHONPATH=/app

WORKDIR /app

RUN python -m pip install --upgrade pip setuptools wheel \
    && python -m pip install --no-cache-dir "poetry==$POETRY_VERSION" "poetry-plugin-export" \
    && poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* /app/

RUN poetry export --without-hashes --with docker -f requirements.txt -o requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.14-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONPATH=/app \
    SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt \
    CURL_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt

RUN groupadd -r appuser && useradd -r -g appuser -d /home/appuser -s /usr/sbin/nologin -c "App user" appuser \
    && mkdir -p /app

WORKDIR /app

COPY --from=builder /app/requirements.txt /app/requirements.txt

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates libcurl4 \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir --no-compile -r requirements.txt

COPY --chown=appuser:appuser app ./app

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import sys, urllib.request; urllib.request.urlopen('http://localhost:8000/health',timeout=3);sys.exit(0)"

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--loop", "uvloop", "--http", "httptools"]
