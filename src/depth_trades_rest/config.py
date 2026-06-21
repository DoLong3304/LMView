"""Configuration for the binance-depth-trades-rest Swarm service.

Polls Binance REST API for:
  - Order book snapshots (``/api/v3/depth``) → ``orderbook:binance:{symbol}`` hash
  - Aggregate trades (``/api/v3/aggTrades``) → ``trade:latest:binance:{symbol}``
    sorted set, scored by trade time in ms, member is a compact JSON.

The producer's WebSocket path is geofenced from AWS us-east-1 (Binance
returns 403 for the @depth and @aggTrade streams). The REST endpoints
on the same host are not blocked, so we run a periodic poller to keep
the Redis cache warm and avoid falling through to the per-request REST
fallback in the API layer.
"""
from __future__ import annotations

import os

REDIS_HOST = os.environ.get("REDIS_HOST", "redis-master")
REDIS_PORT = int(os.environ.get("REDIS_PORT", "6379"))
REDIS_DB = int(os.environ.get("REDIS_DB", "0"))
REDIS_SENTINELS = os.environ.get(
    "REDIS_SENTINELS", "redis-sentinel-1:26379,redis-sentinel-2:26379,redis-sentinel-3:26379"
)
REDIS_MASTER_NAME = os.environ.get("REDIS_MASTER_NAME", "mymaster")

# ── Symbol universe ──
# Top-N USDT symbols by 24h volume. Refreshed hourly from Binance REST.
TOP_N = int(os.environ.get("DEPTH_TRADES_TOP_N", "100"))
SYMBOL_REFRESH_S = int(os.environ.get("DEPTH_TRADES_SYMBOL_REFRESH_S", "3600"))

# ── Polling cadence ──
DEPTH_POLL_S = float(os.environ.get("DEPTH_TRADES_DEPTH_POLL_S", "2.0"))
TRADES_POLL_S = float(os.environ.get("DEPTH_TRADES_TRADES_POLL_S", "1.0"))
DEPTH_LIMIT = int(os.environ.get("DEPTH_TRADES_DEPTH_LIMIT", "20"))
TRADES_LIMIT = int(os.environ.get("DEPTH_TRADES_TRADES_LIMIT", "50"))
# How many trade history entries to keep in the sorted set
TRADES_HISTORY_MAX = int(os.environ.get("DEPTH_TRADES_TRADES_HISTORY_MAX", "200"))

# ── HTTP ──
HTTP_TIMEOUT_S = float(os.environ.get("DEPTH_TRADES_HTTP_TIMEOUT_S", "5.0"))
HTTP_MAX_CONCURRENT = int(os.environ.get("DEPTH_TRADES_MAX_CONCURRENT", "20"))
HTTP_INTER_SYMBOL_DELAY_S = float(os.environ.get("DEPTH_TRADES_INTER_SYMBOL_DELAY_S", "0.05"))

# ── Cache TTLs ──
DEPTH_TTL_S = int(os.environ.get("DEPTH_TRADES_DEPTH_TTL_S", "30"))
TRADES_TTL_S = int(os.environ.get("DEPTH_TRADES_TRADES_TTL_S", "1800"))

# ── Metrics & health ──
METRICS_HOST = os.environ.get("METRICS_HOST", "0.0.0.0")
METRICS_PORT = int(os.environ.get("METRICS_PORT", "9102"))
LOG_LEVEL = os.environ.get("LOG_LEVEL", "INFO")
