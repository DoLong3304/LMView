"""binance-kline-rest: REST kline poller → Redis.

Long-term replacement for the dead producer's kline WebSocket path
(Binance WS is 403-geofenced from this AWS region; REST is not) and
for the cron-based ``scripts/cron_refresh_klines.sh`` stopgap.

Polls ``api.binance.com/api/v3/klines`` for the top-N USDT symbols by
24h quote volume and writes the canonical LMView candle shape to Redis:

    ZADD candle:{interval}:binance:{symbol} {json:open_time_ms} {open_time_ms}
    HSET candle:latest:binance:{symbol} {latest fields}   (1m+ only)

This matches the shape produced by ``src/processing/writers/keydb_kline.py``
and ``src/exchanges/binance/redis_writer.py`` so backend reads are
transparent. See ``docs/system/13-caveats.md`` DP-6 for background.
"""
