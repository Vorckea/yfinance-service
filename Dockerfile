# --- Stage 1: Builder ---
FROM python:3.13-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    POETRY_VERSION=2.1.3 \
    PYTHONPATH=/app

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir "poetry==$POETRY_VERSION" "poetry-plugin-export" && \
    poetry config virtualenvs.create false

COPY pyproject.toml poetry.lock* /app/

RUN poetry export --without-hashes --only main -f requirements.txt -o requirements.txt

# --- Stage 2: Runtime ---
FROM python:3.13-slim-bookworm AS runtime

ENV PYTHONUNBUFFERED=1 \
    PYTHONFAULTHANDLER=1 \
    PYTHONPATH=/app

WORKDIR /app

COPY --from=builder /app/requirements.txt /app/
RUN pip install --no-cache-dir --no-compile -r requirements.txt

COPY app ./app

RUN useradd --create-home --shell /usr/sbin/nologin appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl --fsS http://localhost:8000/health || exit 1


CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
