"""Multi-shard Binance WebSocket ticker feed.

Replaces the dead producer's WS ticker path. Connects to Binance combined
streams, parses @ticker payloads (24 fields), and writes to Redis hash
``ticker:latest:binance:{symbol}`` with full Binance field coverage.

Architecture:
  Shard 0 ─┐
  Shard 1 ─┤
  Shard 2 ─┼─→ Redis HSET (pipeline, 50ms batch)
  ...     ─┤
  Shard N ─┘

Each shard = 1 async task = 1 WebSocket connection.
Target: <1s end-to-end latency, no 403 Forbidden from Binance.
"""

from src.ticker_ws.config import TickerConfig
from src.ticker_ws.shard import TickerShard

__all__ = ["TickerConfig", "TickerShard"]