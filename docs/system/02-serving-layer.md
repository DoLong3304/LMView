# Serving Layer — FastAPI

FastAPI 0.115 backend serving REST + WebSocket, reading from Redis/InfluxDB/Trino/PostgreSQL with multi-source fallback chains.

## Entry Point: backend/app.py

**Lifespan** (ordered):
1. `init_pg_pool()` — asyncpg connection pool (lazy import, retries)
2. `run_migration()` — SQL files in `backend/migrations/` sorted by filename prefix
3. `ensure_default_admin()` — creates admin account if not exists
4. **Embedding preload** — Thread attempts to `pip install sentence-transformers` + load model for AI RAG
5. **Background tasks**:
   - `news_fetcher.start()` — RSS poll every 300s
   - `market_fetcher.start()` — Trino gold poll every 300s
   - `binance_price_poller.start()` — Binance REST price poll
   - `sentiment_score_loop()` — Score unscored articles every 600s
6. `yield` — app runs
7. Shutdown: cancel sentiment task, stop all fetchers, close all DB connections

**Middleware Stack** (order matters):
```
CORS → RateLimiter (in-process token bucket) → RequestId → Prometheus Instrumentator
```
- CORS: configured from `CORS_ORIGINS` env var
- RateLimiter: token-bucket, configurable via `RATE_LIMIT_PER_MINUTE` (default 200)
- RequestId: adds `X-Request-Id` header, emits one JSON log line per request
- Prometheus: optional (requires prometheus-fastapi-instrumentator)

**18 Routers** registered in order:
health, ticker, klines, historical, orderbook, trades, symbols, indicators, websocket, market_overview, market, news, auth, ai, settings, admin, screener, rum

**Prometheus Custom Endpoints**:
- `/metrics-custom` — WebSocket/source/cache metrics (backend/api/metrics.py). Uses module-attribute scanning to discover metric instances.
- `/metrics-ai` — AI/RAG/cost metrics (backend/services/ai/metrics.py). Same technique.
- Both serialize Prometheus text format manually, filtering by metric name set.

---

## API Route Details

### `/api/health` — health.py

**Method**: GET
**Auth**: None
**Logic**: Checks PostgreSQL (pg_health_check), Redis (sentinel health), InfluxDB (ping), Trino (connection test). Returns `{"status": "ok"|"degraded"|"down"}` with per-service latency in ms.

**Data Sources**: PostgreSQL, Redis, InfluxDB, Trino — all queried in parallel with `asyncio.gather()`

**Bug**: If any check fails, status degrades to `degraded` but no per-check timeout. A hung Trino query blocks the entire health endpoint.

### `/api/ticker` — ticker.py

**Endpoints**:
- `GET /ticker/{symbol}` — single symbol, optional `?exchange=binance` filter
- `GET /ticker` — all symbols, optional `?exchange=` filter and `?sort_by=volume`

**Logic**:
- Scans Redis keys `ticker:latest:{exchange}:{symbol}` for each exchange
- If exchange param given: returns single-exchange data
- If no exchange: aggregates mid-price `(bid + ask) / 2` across exchanges
- `_activity_score()` computes ranking: `max(volume,0) * (1+min(|change_24h|,100)/100) + freshness_bonus`

**Data Sources**: Redis (`ticker:latest:*` keys)
**Auth**: None (public market data)

**Bug/Issue**: Exchange aggregation uses simple mid-price average. No volume-weighted price calculation. If one exchange has stale data, it pollutes the aggregate.

### `/api/klines` — klines.py — THE CRITICAL PATH

**Endpoint**: `GET /api/klines?symbol=BTCUSDT&interval=1h&limit=100&end_time=...`

**Data Flow — Multi-Source Fallback Chain**:
```
1. Redis (hot): 
   - `candle:1m:{exchange}:{symbol}` — BATCH read last N 1m candles from sorted set
   - Live 1s candles from `candle:1s:{symbol}` for sub-1m intervals
   
2. InfluxDB (warm, last 90 days):
   - `candles` measurement, filtered by symbol + interval
   - Pivoted from time-series to column format via Flux pivot()
   
3. Trino (cold, beyond 90 days):
   - `crypto_lakehouse.coin_klines` for 1m historical
   - `crypto_lakehouse.historical_hourly` for hourly/daily
```

**Aggregation Logic** (`candle_service.py`):
1. **`collect_base_1m_candles()`** — Paged backfill from InfluxDB then Trino
2. **`aggregate()`** — Re-samples 1m → target interval (1h, 4h, 1d, 1w)
   - `open` = first candle's open in bucket
   - `close` = last candle's close in bucket
   - `high` = max(high), `low` = min(low)
   - `volume` = sum(volume)
3. **`merge_unique()`** — Merges candles by openTime with quality priority:
   - Closed/final candle > partial
   - Higher volume > lower volume
   - Incoming > existing if equal quality

**Complexities & Bugs in candle_service.py**:
1. **Redundant InfluxDB queries on every klines call** — Each klines request hits InfluxDB with a Flux query. No server-side caching. High-traffic symbols trigger 10+ queries per second.
2. **`query_influx_candles()` constructs raw Flux strings** — No parameterized queries. SQL injection-like risk from symbol/interval (though validated upstream).
3. **Trino connection leak** — `query_trino_1m()` and `query_trino_hourly()` use `get_trino_connection()` each call, but close manually in `finally`. If `get_trino_connection()` itself fails, the exception propagates without connection cleanup.
4. **`collect_base_1m_candles()` paging logic** — Pages backward from `end_ms`. If `limit` is small but `target_sec` large (e.g., 1w), computes `raw_target = min((limit * mult) + mult, MAX_RAW_CANDLES)` which can be 60000 for `limit=1000, mult=10080`. The loop may never hit the `len(aggregate(candles, ...)) >= limit` break condition because 100k+ raw candles needed for 1000 weekly bars.
5. **Redis candle keys use `{exchange}` prefix** — But `collect_base_1m_candles()` doesn't pass exchange. InfluxDB/Trino queries filter by `symbol` only. A symbol present on both Binance and OKX gets double-counted.

### `/api/websocket` — websocket.py

**Endpoints**:
- `WS /api/stream/all?symbol=BTCUSDT` — all timeframes
- `WS /api/stream/{interval}?symbol=BTCUSDT` — single interval
- `WS /api/stream/indicators/{interval}?symbol=BTCUSDT` — indicators

**Logic**:
- 50ms poll loop reading Redis latest candles for subscribed symbol
- Pushes JSON candle data to client
- Tracks connection lifecycle via Prometheus metrics (connect, disconnect, message push, errors)
- Multi-source fallback: Redis → InfluxDB → Trino returning DataFreshness metadata

**Bugs & Issues**:
1. **Single-threaded per connection** — Each WebSocket runs an `asyncio.sleep(0.05)` loop. 100 concurrent connections = 100 concurrent tasks looping. Under high load, event loop contention causes latency spikes.
2. **No heartbeat/ping** — Lightweight-charts expects periodic pings. Without them, browser may close idle connections after 30-60s.
3. **All-timeframe route combines streams** — One client subscribes to all candles (1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w) in a single connection. If candle count is large, JSON payload can exceed 1MB per push.
4. **No client disconnect detection on stale sockets** — If client hard-closes without WebSocket close frame, the server task runs forever until TCP timeout.

---

## Candle Service Deep Dive — The Heart of the Backend

`backend/services/candle_service.py` is the most complex module (~450 lines). It handles:

### Data Flow on `GET /api/klines`

```
Request: GET /api/klines?symbol=BTCUSDT&interval=1h&limit=100&end_time=now

1. validate_symbol(BTCUSDT) → "BTCUSDT"
2. validate_interval(1h) → ("1h", 3600)
3. target_sec=3600, limit=100, end_ms=now_ms

4. Call collect_base_1m_candles():
   target_sec=3600, limit=100, end_ms=now_ms
   
   a. Compute raw_target = min(100*60 + 60, 6000) = 6000 1m candles needed
   b. Compute per_page = min(500, max(60*240, 60*8)) = 500
   c. Loop pages (max 3 pages):
      Page 1: query_influx_candles(BTCUSDT, 1m, 500, range_h, now_ms)
        → Flux query: range [now - 130h, now]
        → Returns up to 500 1m candles from InfluxDB
      merge_unique() → store in candles list
      cursor = oldest candle's openTime
      
      If len(aggregate(candles, 3600000)) >= 100: break
      
      Page 2: query_influx_candles() from cursor
      ...
      If past influx_cutoff_ms: query_trino_1m() instead
      ...

5. aggregate(candles, 3600000):
   - Group candles into 1h buckets by (openTime // 3600000) * 3600000
   - For each bucket: open=first.open, close=last.close, high=max(high),
     low=min(low), volume=sum(volume)
   
6. Return last 100 aggregated candles
```

### Quality Merge Logic (`merge_unique`)

```
Priority:
1. Closed/final candle (is_closed=true or x=true) > partial
2. Higher volume > lower volume
3. New (incoming) > existing if tie

This matters when InfluxDB has a partially-written candle
and Trino returns the same candle as closed — Trino's version wins.
```

### Weaknesses

1. **No Redis caching layer** — Every `/api/klines` call hits InfluxDB and potentially Trino. No in-memory TTL cache for popular symbols/intervals.
2. **MAX_RAW_CANDLES=6000** — Hard limit on how many 1m candles to collect. For `1w` interval with `limit=200`, needs 10080 1m candles per week bar × 200 = 2M. Hits limit and returns incomplete data.
3. **`influx_cutoff_ms` calculation** — Uses `INFLUX_1M_RETENTION_DAYS` (90 days). But InfluxDB retention may be different. No config validation.
4. **Flux queries for every interval** — Even for 1m data, constructs a separate Flux query. Flux query overhead (~10-50ms) adds up.

---

## Cross-Component Cooperation

### How Backend Connects to Other Systems

```
FastAPI
├── Redis Sentinel (read/write)
│   ├── health → sentinel health check
│   ├── ticker → ticker:latest:{ex}:{sym}
│   ├── klines → candle:1m:{ex}:{sym} (sorted set)
│   ├── trades → trade:latest:{ex}:{sym} (list)
│   ├── orderbook → orderbook:{ex}:{sym} (hash)
│   └── indicators → indicator:{ex}:{sym}:{interval}
├── InfluxDB (read)
│   └── candles measurement (Flux query)
├── Trino (read)
│   └── crypto_lakehouse.coin_klines, historical_hourly
└── PostgreSQL (read/write)
    ├── users, sessions (auth)
    ├── ai_chat_sessions, messages (AI)
    ├── knowledge_chunks (RAG)
    ├── news_articles (news)
    └── app_settings, user_preferences (settings)
```

### Request Flow Example: Ticker Page Load

```
1. Browser → WS /api/stream/all?symbol=BTCUSDT
   → FastAPI WebSocket accepts, starts 50ms poll loop
   → Every 50ms: read Redis candle:1m:binance:BTCUSDT
   → Push latest candle to browser
   → [continues until client disconnects]

2. Browser → GET /api/ticker/BTCUSDT
   → FastAPI reads Redis ticker:latest:binance:BTCUSDT
   → Returns 24hr ticker data

3. Browser → GET /api/klines?symbol=BTCUSDT&interval=1h&limit=200
   → FastAPI calls candle_service.collect_base_1m_candles()
   → Reads Redis candles (hot), then InfluxDB (warm)
   → Aggregates 1m→1h, returns last 200 candles
```

---

## Known Hot Spots & Required Fixes

| File | Issue | Risk | Fix Priority |
|---|---|---|---|
| `candle_service.py` | No Redis caching, hits InfluxDB per request | High latency under load | High |
| `candle_service.py` | Trino connection leak on exception | Connection pool exhaustion | High |
| `websocket.py` | No heartbeat/ping | Browser disconnect after 30s | Medium |
| `websocket.py` | All-timeframe route sends large JSON | Bandwidth waste | Medium |
| `klines.py` | Flux query injection risk from symbol | Low (validated) | Low |
| `ticker.py` | Mid-price avg not volume-weighted | Inaccurate aggregate | Medium |
| `health.py` | No per-check timeout | Trino hang blocks health | Medium |
