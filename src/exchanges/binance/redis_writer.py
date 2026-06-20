"""
Direct Redis writer for Binance WebSocket data.
Bypasses Kafka/Flink for resilience when speed layer fails.
"""

import json
import logging
from typing import Optional

import redis

from common.flink_redis_sentinel import get_flink_redis
from common.config import ENABLE_DIRECT_REDIS

log = logging.getLogger(__name__)


class DirectRedisWriter:
    """Write ticker/kline/trade/depth directly to Redis from WebSocket."""

    TICKER_TTL = 300          # 5 min
    CANDLE_TTL = 86400        # 1 day
    TRADE_TTL = 600           # 10 min
    DEPTH_TTL = 300           # 5 min

    def __init__(self):
        # Dedicated connection pool — separate from get_flink_redis() shared pool
        import os
        pool_size = int(os.getenv('DIRECT_REDIS_POOL_SIZE', '50'))
        self._pool = redis.ConnectionPool(
            host=os.getenv('REDIS_HOST', 'redis-master'),
            port=int(os.getenv('REDIS_PORT', '6379')),
            db=0,
            max_connections=pool_size,
            socket_connect_timeout=5,
            socket_keepalive=True,
            decode_responses=True,
            health_check_interval=30,
        )
        self._r = redis.Redis(connection_pool=self._pool)
        self._enabled = ENABLE_DIRECT_REDIS

    def _check_enabled(self) -> bool:
        if not self._enabled:
            # Check global flag from health monitor
            from exchanges.binance.redis_writer import _direct_redis_active
            return _direct_redis_active
        return True

    def write_ticker(self, exchange: str, symbol: str, data: dict) -> bool:
        """Write ticker to Redis hash: ticker:latest:{exchange}:{symbol}"""
        if not self._check_enabled():
            return False
        try:
            key = f"ticker:latest:{exchange}:{symbol}"

            # Calculate real-time % change from current price vs 24h open
            current_price = float(data.get("close", 0))
            h24_open = float(data.get("h24_open", 0))
            if h24_open > 0:
                calculated_change = ((current_price - h24_open) / h24_open) * 100
            else:
                # Fallback to Binance-provided % change
                calculated_change = float(data.get("h24_price_change_pct", 0))

            mapping = {
                "price":      str(current_price),
                "bid":        str(data.get("bid", 0)),
                "ask":        str(data.get("ask", 0)),
                "volume":     str(data.get("h24_volume", 0)),
                "change24h":  str(round(calculated_change, 4)),
                "event_time": str(data.get("event_time", 0)),
                "exchange":   exchange,
                "h24_open":   str(h24_open),
                "h24_high":   str(data.get("h24_high", 0)),
                "h24_low":    str(data.get("h24_low", 0)),
            }
            # DP-1: Pipeline HSET + EXPIRE into single round-trip
            pipe = self._r.pipeline()
            pipe.hset(key, mapping=mapping)
            pipe.expire(key, self.TICKER_TTL)
            pipe.execute()
            return True
        except Exception as e:
            log.error("[DirectRedis/ticker] write error: %s", e)
            return False

    def write_kline(self, exchange: str, symbol: str, interval: str, data: dict) -> bool:
        """Write kline to Redis sorted set: candle:{interval}:{exchange}:{symbol}"""
        if not self._check_enabled():
            return False
        if interval not in ("1s", "1m"):
            return False
        try:
            key = f"candle:{interval}:{exchange}:{symbol}"
            candle = {
                "t": data["kline_start"],
                "o": data["open"],
                "h": data["high"],
                "l": data["low"],
                "c": data["close"],
                "v": data["volume"],
                "qv": data.get("quote_volume", 0),
                "n": data.get("trade_count", 0),
                "x": data.get("is_closed", False),
            }
            # DP-1: Pipeline ZADD + EXPIRE into single round-trip
            pipe = self._r.pipeline()
            pipe.zadd(key, {json.dumps(candle): data["kline_start"]})
            pipe.expire(key, self.CANDLE_TTL)

            # Also update latest candle hash for 1m+
            if interval != "1s":
                latest_key = f"candle:latest:{exchange}:{symbol}"
                pipe.hset(latest_key, mapping={
                    "open":         str(data["open"]),
                    "high":         str(data["high"]),
                    "low":          str(data["low"]),
                    "close":        str(data["close"]),
                    "volume":       str(data["volume"]),
                    "quote_volume": str(data.get("quote_volume", 0)),
                    "trade_count":  str(data.get("trade_count", 0)),
                    "is_closed":    str(int(data.get("is_closed", False))),
                    "kline_start":  str(data["kline_start"]),
                    "interval":     interval,
                    "exchange":     exchange,
                })
                pipe.expire(latest_key, self.CANDLE_TTL)
            pipe.execute()
            return True
        except Exception as e:
            log.error("[DirectRedis/kline] write error: %s", e)
            return False

    def write_trade(self, exchange: str, symbol: str, data: dict) -> bool:
        """Write trade to Redis sorted set: trade:latest:{exchange}:{symbol}"""
        if not self._check_enabled():
            return False
        try:
            key = f"trade:latest:{exchange}:{symbol}"
            trade = {
                "p": data["price"],
                "q": data["quantity"],
                "t": data["trade_time"],
                "m": data.get("is_buyer_maker", False),
                "T": data.get("event_time", 0),
            }
            # DP-1: Pipeline ZADD + EXPIRE into single round-trip
            pipe = self._r.pipeline()
            pipe.zadd(key, {json.dumps(trade): data["trade_time"]})
            pipe.expire(key, self.TRADE_TTL)
            pipe.execute()
            return True
        except Exception as e:
            log.error("[DirectRedis/trade] write error: %s", e)
            return False

    def write_depth(self, exchange: str, symbol: str, data: dict) -> bool:
        """Write order book depth to Redis hash: orderbook:{exchange}:{symbol}"""
        if not self._check_enabled():
            return False
        try:
            key = f"orderbook:{exchange}:{symbol}"
            bids = data.get("bids", [])
            asks = data.get("asks", [])
            # DP-1: Pipeline HSET + EXPIRE into single round-trip
            pipe = self._r.pipeline()
            pipe.hset(key, mapping={
                "bids":           json.dumps(bids),
                "asks":           json.dumps(asks),
                "last_update_id": str(data.get("last_update_id", 0)),
                "event_time":     str(data.get("event_time", 0)),
                "exchange":       exchange,
                "bid_depth":      str(len(bids)),
                "ask_depth":      str(len(asks)),
                "best_bid":       str(float(bids[0][0]) if bids else 0),
                "best_ask":       str(float(asks[0][0]) if asks else 0),
                "spread":         str(round(float(asks[0][0]) - float(bids[0][0]), 8) if bids and asks else 0),
            })
            pipe.expire(key, self.DEPTH_TTL)
            pipe.execute()
            return True
        except Exception as e:
            log.error("[DirectRedis/depth] write error: %s", e)
            return False

    def close(self):
        try:
            self._r.close()
        except Exception as e:
            log.error("[DirectRedis] close error: %s", e)


# Global instance (lazy init)
_direct_writer: Optional[DirectRedisWriter] = None
_direct_redis_active: bool = False  # Global flag from health monitor


def get_direct_writer() -> DirectRedisWriter:
    """Get or create the global DirectRedisWriter instance."""
    global _direct_writer
    if _direct_writer is None:
        _direct_writer = DirectRedisWriter()
    return _direct_writer


def set_direct_redis_active(enabled: bool) -> None:
    """Called by HealthMonitor to enable/disable direct Redis writes."""
    global _direct_redis_active
    _direct_redis_active = enabled
    if _direct_writer is not None:
        _direct_writer._enabled = enabled
    log.info("[DirectRedis] Global flag set to: %s", enabled)