"""
Redis Schema Design for Price Change %
Optimized for real-time updates with no duplication

Key Pattern: price_change:{symbol}
Example: price_change:BTCUSDT

Value Format: JSON
{
    "symbol": "BTCUSDT",
    "current_price": 67850.50,
    "reference_price": 67000.00,
    "change_pct": 1.27,
    "change_abs": 850.50,
    "snapshot_time": 1716019200000
}

Features:
- TTL: 60 seconds (auto-cleanup stale data)
- Update frequency: Every 1 second
- Mode: UPSERT (replaces old value, no duplication)
- Memory efficient: ~200 bytes per symbol
- Estimated memory: 200 bytes × 500 symbols = 100 KB

Redis Commands:
- SET price_change:BTCUSDT '{"symbol":"BTCUSDT",...}' EX 60
- GET price_change:BTCUSDT
- KEYS price_change:*
- DEL price_change:BTCUSDT

Flink Integration:
- Flink writes to Redis every 1 second
- Uses Redis connector with upsert mode
- Automatically replaces old value (no append)
- TTL ensures cleanup of stale data

API Integration:
- FastAPI reads from Redis (fast lookup)
- Fallback to Iceberg if Redis miss
- Cache warming on startup
"""
