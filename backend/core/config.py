import os
import sys
import logging

log = logging.getLogger("backend.core.config")

# ─── Redis Sentinel (High Availability) ─────────────────────────────────────
# Redis Sentinel configuration is handled in redis_sentinel.py
# using REDIS_SENTINELS and REDIS_MASTER_NAME environment variables

# ─── InfluxDB ───────────────────────────────────────────────────────────────
INFLUX_URL = os.environ.get("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.environ.get("INFLUX_TOKEN", "")
INFLUX_ORG = os.environ.get("INFLUX_ORG", "vi")
INFLUX_BUCKET = os.environ.get("INFLUX_BUCKET", "crypto")

# ─── Trino (Iceberg query engine) ───────────────────────────────────────────
TRINO_HOST = os.environ.get("TRINO_HOST", "trino")
TRINO_PORT = int(os.environ.get("TRINO_PORT", "8080"))

# ─── PostgreSQL (Auth, AI, Session persistence) ─────────────────────────────
POSTGRES_HOST = os.environ.get("POSTGRES_HOST", "postgres")
POSTGRES_PORT = os.environ.get("POSTGRES_PORT", "5432")
POSTGRES_USER = os.environ.get("POSTGRES_USER", "iceberg")
POSTGRES_PASSWORD = os.environ.get("POSTGRES_PASSWORD", "")
POSTGRES_LMVIEW_DB = os.environ.get("POSTGRES_LMVIEW_DB", "iceberg_catalog")

# ─── Auth/Session ────────────────────────────────────────────────────────────
SESSION_EXPIRY_HOURS = int(os.environ.get("SESSION_EXPIRY_HOURS", "168"))  # 7 days
RUN_MIGRATIONS = os.environ.get("RUN_MIGRATIONS", "false")

# ─── CORS ───────────────────────────────────────────────────────────────────
CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*").split(",")

# ─── Startup validation ────────────────────────────────────────────────────
_missing = []
if not INFLUX_TOKEN:
    _missing.append("INFLUX_TOKEN")
if _missing:
    log.error("Missing required environment variables: %s", ", ".join(_missing))
    sys.exit(1)
