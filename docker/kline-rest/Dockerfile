FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install build deps only in builder stage
COPY docker/kline-rest/requirements.txt /build/requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r /build/requirements.txt


FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy source code + Avro schemas (needed for Schema Registry registration)
COPY src/ /app/src/
COPY schemas/ /app/schemas/

# Healthcheck — /healthz returns 503 if last 1m sweep is stale (> 2x poll interval).
# Match the compose healthcheck so either can fail the task.
HEALTHCHECK --interval=15s --timeout=5s --start-period=90s --retries=5 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:9101/healthz', timeout=3).status == 200 else 1)" || exit 1

EXPOSE 9101

ENTRYPOINT ["python", "-m", "src.kline_rest.main"]
