FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build

# Install build deps only in builder stage
COPY docker/ticker-ws/requirements.txt /build/requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r /build/requirements.txt


FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# Copy installed packages from builder
COPY --from=builder /install /usr/local

WORKDIR /app

# Copy source code
COPY src/ /app/src/

# Healthcheck
HEALTHCHECK --interval=10s --timeout=3s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:9100/healthz', timeout=2).status == 200 else 1)" || exit 1

EXPOSE 9100

ENTRYPOINT ["python", "-m", "src.ticker_ws.main"]