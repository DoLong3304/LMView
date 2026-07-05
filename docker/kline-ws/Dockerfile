FROM python:3.11-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /build
COPY docker/kline-ws/requirements.txt /build/requirements.txt
RUN pip install --upgrade pip && pip install --prefix=/install -r /build/requirements.txt

FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

COPY --from=builder /install /usr/local

WORKDIR /app
COPY src/ /app/src/

HEALTHCHECK --interval=15s --timeout=5s --start-period=60s --retries=5 \
    CMD python -c "import urllib.request, sys; sys.exit(0 if urllib.request.urlopen('http://localhost:9102/healthz', timeout=3).status == 200 else 1)" || exit 1

EXPOSE 9102

ENTRYPOINT ["python", "-m", "src.kline_ws.main"]
