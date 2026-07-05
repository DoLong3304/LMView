"""
Centralized environment configuration for data processing services.

All environment variables are read once at import time.  Flink writer
modules intentionally keep their own ``os.environ.get()`` calls for
serialization safety — this module serves the producer, batch jobs,
and lakehouse pipeline.
"""

import os
from datetime import datetime, timezone

# ── Kafka ────────────────────────────────────────────────────────────────────
KAFKA_BOOTSTRAP = os.environ.get("KAFKA_BOOTSTRAP", "kafka-1:9092,kafka-2:9092,kafka-3:9092")

KAFKA_TOPIC_TICKER = "crypto_ticker"
KAFKA_TOPIC_TRADES = "crypto_trades"
KAFKA_TOPIC_KLINES = "crypto_klines"
KAFKA_TOPIC_DEPTH  = "crypto_depth"

# ── Schema Registry ──────────────────────────────────────────────────────────
SCHEMA_REGISTRY_URL = os.environ.get(
    "SCHEMA_REGISTRY_URL", "http://schema-registry:8080"
)

# ── Redis / KeyDB ────────────────────────────────────────────────────────────
REDIS_HOST = os.environ.get("REDIS_HOST", "keydb")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))

# ── InfluxDB ─────────────────────────────────────────────────────────────────
INFLUX_URL    = os.environ.get("INFLUX_URL",    "http://influxdb:8086")
INFLUX_TOKEN  = os.environ.get("INFLUX_TOKEN",  "")
INFLUX_ORG    = os.environ.get("INFLUX_ORG",    "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

# ── MinIO / S3 ───────────────────────────────────────────────────────────────
#
# Two profiles — switch via env vars:
#
#   AWS S3 (default):
#     S3_PROVIDER=aws
#     S3_ENDPOINT=https://s3.ap-southeast-1.amazonaws.com
#     S3_SSL_ENABLED=true
#     S3_PATH_STYLE=false
#     AWS_S3_BUCKET=lmview-iceberg-storage
#
#   MinIO (local Docker):
#     S3_PROVIDER=minio
#     S3_ENDPOINT=http://minio:9000
#     S3_SSL_ENABLED=false
#     S3_PATH_STYLE=true
#     AWS_S3_BUCKET=cryptoprice
#     # Also set AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY to minioadmin creds
#
# ── credentials (shared) ────────────────────────────────────────────────────
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "")

# ── bucket & endpoint ───────────────────────────────────────────────────────
AWS_S3_BUCKET  = os.environ.get("AWS_S3_BUCKET", "lmview-iceberg-storage")
AWS_REGION     = os.environ.get("AWS_REGION", "ap-southeast-1")
S3_ENDPOINT    = os.environ.get("S3_ENDPOINT", "https://s3.ap-southeast-1.amazonaws.com")

# ── connectivity toggles (true for AWS S3, flip for MinIO) ──────────────────
S3_SSL_ENABLED = os.environ.get("S3_SSL_ENABLED", "true").lower() == "true"
S3_PATH_STYLE  = os.environ.get("S3_PATH_STYLE", "false").lower() == "true"

# ── object key prefix (e.g. "data/" for lmview-lakehouse migration doc) ────
S3_PREFIX      = os.environ.get("S3_PREFIX", "").strip("/")
if S3_PREFIX:
    S3_PREFIX += "/"

# ── Iceberg ──────────────────────────────────────────────────────────────────
ICEBERG_CATALOG      = "iceberg_catalog"
ICEBERG_DB           = "crypto_lakehouse"
ICEBERG_TABLE_TICKER = f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_ticker"
ICEBERG_TABLE_TRADES = f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_trades"
ICEBERG_TABLE_KLINES = f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_klines"

# ── Producer tuning ──────────────────────────────────────────────────────────
KLINE_INTERVAL_WS      = os.environ.get("KLINE_INTERVAL", "1m")
DEPTH_LEVEL            = os.environ.get("DEPTH_LEVEL", "20")
DEPTH_UPDATE_MS        = os.environ.get("DEPTH_UPDATE_MS", "100")
SYMBOLS_PER_CONNECTION = int(os.environ.get("SYMBOLS_PER_CONNECTION", "84"))
SYMBOLS_PER_DEPTH_CONN = int(os.environ.get("SYMBOLS_PER_DEPTH_CONN", "15"))
KLINE_SYMBOLS_PER_CONN  = int(os.environ.get("KLINE_SYMBOLS_PER_CONN", "20"))
MAX_SYMBOLS            = int(os.environ.get("MAX_SYMBOLS", "200"))
TICKER_HEARTBEAT_SEC   = 0.3
ENABLE_OKX             = os.environ.get("ENABLE_OKX", "false").lower() == "true"

# ── Per-stream WS gates (Binance WS is geofenced on AWS us-east-1; only
#    the ticker stream and the REST kline poller are reliable there).
#    Trade and depth WS will be served by a separate REST poller service
#    (or disabled entirely) until Binance WS is reachable again. ──
ENABLE_TICKER_WS       = os.environ.get("ENABLE_TICKER_WS", "true").lower() == "true"
ENABLE_TRADES_WS       = os.environ.get("ENABLE_TRADES_WS", "false").lower() == "true"
ENABLE_DEPTH_WS        = os.environ.get("ENABLE_DEPTH_WS", "false").lower() == "true"
ENABLE_KLINE_WS        = os.environ.get("ENABLE_KLINE_WS", "false").lower() == "true"

# ── Direct Redis Bypass ──
ENABLE_DIRECT_REDIS      = os.environ.get("ENABLE_DIRECT_REDIS", "false").lower() == "true"

# ── Health Check / Auto-failover ──
HEALTH_CHECK_INTERVAL_SEC = int(os.environ.get("HEALTH_CHECK_INTERVAL_SEC", "30"))
FAILOVER_THRESHOLD_SEC   = int(os.environ.get("FAILOVER_THRESHOLD_SEC", "60"))
RECOVERY_THRESHOLD_SEC   = int(os.environ.get("RECOVERY_THRESHOLD_SEC", "120"))
FLINK_JM_URL             = os.environ.get("FLINK_JM_URL", "http://flink-jobmanager:8081")

# ── Backfill ─────────────────────────────────────────────────────────────────
MAX_RETRIES          = 5
REQUEST_DELAY        = 0.12
KLINE_BATCH_INFLUX   = 1000
KLINES_PER_REQ       = 1000
MIN_GAP_SEC          = 300
MAX_BACKFILL_DAYS    = 7
MAX_WORKERS          = 8
FLUSH_THRESHOLD      = int(os.environ.get("BACKFILL_FLUSH_THRESHOLD", "10000"))
RETENTION_1M_DAYS    = int(os.environ.get("RETENTION_1M_DAYS", "90"))

# ── Producer concurrency (Phase 1 NOTE.MD: cap simultaneous WS threads to
#    stay under Binance connection limit and avoid 403 Forbidden) ──
MAX_PRODUCER_WORKERS = int(os.environ.get("MAX_PRODUCER_WORKERS", "8"))
PRODUCER_403_BACKOFF_SEC = int(os.environ.get("PRODUCER_403_BACKOFF_SEC", "60"))

# ── Spark ────────────────────────────────────────────────────────────────────
BACKFILL_SPARK_CORES_MAX          = os.environ.get("BACKFILL_SPARK_CORES_MAX", "2")
BACKFILL_SPARK_SHUFFLE_PARTITIONS = os.environ.get("BACKFILL_SPARK_SHUFFLE_PARTITIONS", "8")

# ── Iceberg maintenance ─────────────────────────────────────────────────────
SNAPSHOT_RETENTION_HOURS     = 48
ORPHAN_FILE_RETENTION_HOURS  = 72
TARGET_FILE_SIZE_BYTES       = 128 * 1024 * 1024

ICEBERG_TABLES = [
    f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_ticker",
    f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_trades",
    f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_klines",
    f"{ICEBERG_CATALOG}.{ICEBERG_DB}.coin_klines_hourly",
]

# ── Indicator history / hot cache ───────────────────────────────────────────
INDICATOR_HISTORY_TTL_SEC = int(os.environ.get("INDICATOR_HISTORY_TTL_SEC", "604800"))
INDICATOR_HISTORY_MAX_ENTRIES = int(os.environ.get("INDICATOR_HISTORY_MAX_ENTRIES", "10080"))
