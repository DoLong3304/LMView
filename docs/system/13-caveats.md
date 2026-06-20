# Caveats & Known Issues — Complete Bug Inventory

All known bugs, design weaknesses, and technical debt as of 2026-06-19 (v0.25.42).

---

## Critical Data Integrity Issues

### CI-1: Exchange Field Dropped in Flink Depth Processing
- **File**: `src/processing/writers/keydb_depth.py`
- **Impact**: All orderbook keys stored as `orderbook:binance:{symbol}`, losing exchange context
- **Root Cause**: Flink SELECT for depth stream omits `exchange` column
- **Fix**: Add `exchange` to depth DDL, update Flink SELECT to include it
- **Risk**: Low (only Binance active). High if OKX depth support added.

### CI-2: Exchange Field Omitted in Spark Ticker Dedup
- **File**: `src/lakehouse/pipeline.py`
- **Impact**: Same-symbol same-timestamp records from multiple exchanges collapsed into one
- **Root Cause**: Dedup key is `[symbol, timestamp]` instead of `[exchange, symbol, timestamp]`
- **Fix**: Update Spark DataFrame dedup to include exchange field

### CI-3: Flink 1m Forward-Fill Creates Phantom Candles
- **File**: `src/processing/writers/kline_aggregator.py`
- **Impact**: Low-volume symbols show incorrect closing prices. Frontend shows flat candles with 0 volume.
- **Root Cause**: Aggregator emits candle at 1m boundary even when no 1s data arrived, using `close = previous_close`
- **Fix**: Only emit candle if ≥1 1s candle received. Or set `is_closed=false` on forward-filled.

### CI-4: Symbol Selection Alphabetical, Not Volume-Ranked
- **File**: `src/exchanges/binance/client.py:fetch_symbols()`
- **Impact**: ~5-10% of top volume symbols (by 24h quote volume) may be excluded in favor of low-volume alphabetical pairs
- **Root Cause**: Uses `sorted(symbols)[:MAX_SYMBOLS]` instead of sorting by 24h volume
- **Example**: If MAX_SYMBOLS=200 and `ZRXUSDT` (rank 201 by volume) is selected but `COMPUSDT` (rank 180 by volume) is not because it starts with C
- **Fix**: Replace alphabetical sort with Binance 24hr ticker volume sort

---

## Backend Bugs

### BB-1: No Redis Caching in Klines API
- **File**: `backend/services/candle_service.py`
- **Impact**: Every `/api/klines` call hits InfluxDB and potentially Trino. No TTL cache for popular symbols/intervals.
- **Throughput Impact**: Under load (100+ req/s for BTCUSDT), InfluxDB becomes bottleneck. Flux queries take 10-50ms each.
- **Fix**: Add Redis TTL-based cache for recent candles. Cache key: `candle:cache:{symbol}:{interval}:{limit}` with 1s TTL.

### BB-2: Trino Connection Leak on Query Exception
- **File**: `backend/services/candle_service.py` (lines in `query_trino_1m`, `query_trino_hourly`)
- **Impact**: If Trino query throws an exception that's not `TABLE_NOT_FOUND`, the connection is not closed before re-raising
- **Root Cause**: `conn.close()` in `finally` block, but `get_trino_connection()` called BEFORE try block. If that raises, no conn to close. If `cur.execute()` raises (not TABLE_NOT_FOUND), `finally` runs `conn.close()` → actually this is fine. Let me re-check...
  
  Actually looking at the code:
  ```python
  conn = get_trino_connection()  # Before try
  try:
      cur = conn.cursor()
      try:
          cur.execute(...)  # If this raises non-TABLE_NOT_FOUND
          ...
      except Exception as exc:
          if _is_missing_trino_table_error(exc):
              return []
          raise  # Re-raises, but conn remains open
      ...
  finally:
      conn.close()  # This runs even on re-raise
  ```
  Wait, the `finally` IS reached because the second `raise` is inside the inner try. The outer `finally` runs. So actually no leak for this pattern. But there's another issue: `conn.close()` inside `finally` will also close the cursor.

  Actually, looking more carefully: the pattern is `conn = ...` outside try, `try: cur = conn.cursor(); try: cur.execute()... finally: conn.close()`. The `conn.close()` in `finally` will close the cursor too. This is correct.

  But wait — there's a subtle bug: if `get_trino_connection()` succeeds but `conn.cursor()` raises, the `finally` block runs `conn.close()` correctly. 

  Actually the real Trino bug is: `conn.close()` in `finally` doesn't release the connection back to the pool (if Trino uses connection pooling). It closes the TCP connection. Each call creates a new TCP connection. Under high load, this creates connection churn on the Trino side.

### BB-3: No WebSocket Heartbeat
- **File**: `backend/api/websocket.py`
- **Impact**: Browsers may close idle WebSocket connections after 30-60s of no data (low-volume symbols)
- **Fix**: Send WebSocket ping frame every 10s. Use `websocket.send(json.dumps({"type": "ping"}))` or enable `websocket_ping_interval` in Nginx proxy.

### BB-4: All-Timeframe WebSocket Sends Large Payloads
- **File**: `backend/api/websocket.py` (`/api/stream/all`)
- **Impact**: Pushes all 8 timeframe candles every 50ms. Payload can exceed 1MB, causing browser jank on slow connections.
- **Fix**: Only push timeframes that changed since last poll. Or let client specify which timeframes to receive.

### BB-5: Health Check No Per-Component Timeout
- **File**: `backend/api/health.py`
- **Impact**: A hung Trino query blocks the health endpoint for all components, causing false degradation.
- **Fix**: Use `asyncio.wait_for(trino_check(), timeout=5)` for each component.

### BB-6: Ticker Exchange Aggregation Not Volume-Weighted
- **File**: `backend/api/ticker.py`
- **Impact**: Mid-price average across exchanges. If one exchange has stale data, aggregate is inaccurate.
- **Fix**: Volume-weighted mid-price when both exchanges have data.

### BB-7: Flux Query Injection Risk
- **File**: `backend/services/candle_service.py`
- **Impact**: Symbol and interval interpolated directly into Flux query string. Validated upstream by `validate_symbol()` and `validate_interval()`, but defense-in-depth should use InfluxDB parameterized queries.
- **Fix**: Use InfluxDB Flux parameterized query API when available.

---

## Data Pipeline Bugs

### DP-1: DirectRedisWriter Per-Event Write (No Batch)
- **File**: `src/exchanges/binance/redis_writer.py`
- **Impact**: Each trade/ticker/kline writes to Redis individually. Under 30+ concurrent symbol threads, Redis CPU spikes.
- **Fix**: Buffer writes and flush every 200ms using `asyncio` batching.

### DP-2: deps.zip Build Logic Duplicated
- **Files**: `scripts/auto_submit_jobs.sh` (lines 28-44), `scripts/submit_flink.sh` (all)
- **Impact**: Two copies of identical Python code building deps.zip. Fix in one doesn't update the other.
- **Fix**: Extract deps.zip building to a shared script (`scripts/build_deps_zip.sh`).

### DP-3: deps.zip writers/__init__.py Wrong Path
- **File**: `scripts/auto_submit_jobs.sh`
- **Impact**: Creates `writers/__init__.py` but actual structure is `processing/writers/__init__.py`. Cross-writer imports may fail.
- **Fix**: Write `processing/writers/__init__.py` instead, or ensure empty init exists in source.

### DP-4: Producer Doesn't Check Topic Existence
- **File**: `src/producer/main.py`
- **Impact**: If `create_kafka_topics.sh` wasn't run, `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false` causes silent message drops.
- **Fix**: On startup, check all 4 topics exist. Exit with clear error if missing.

### DP-5: OKX Stream Threads Always Spawned
- **File**: `src/producer/main.py`
- **Impact**: Even when `ENABLE_OKX=false`, symbol list evaluation runs (returns empty list, spawns 0 threads). Minor overhead.
- **Fix**: Skip all OKX setup when disabled.

---

## Infrastructure Bugs

### IB-1: Deploy Script CUSTOM_IMAGES Includes Kafka Without Build
- **File**: `scripts/deploy_aws_swarm.sh` (line 148)
- **Impact**: `cryptoprice/kafka:3.9.0` in CUSTOM_IMAGES but docker-compose.yml uses `apache/kafka:3.9.0` directly (no build). Push silently skips.
- **Fix**: Remove kafka from CUSTOM_IMAGES, or add docker-compose build context for kafka.

### IB-2: Deploy Script sed Port Normalization Fragile
- **File**: `scripts/deploy_aws_swarm.sh` (sed -E -i)
- **Impact**: Uses regex to strip quotes from `published:` and `target:` port numbers. If `docker compose config` outputs them differently (e.g., no quotes for integers), sed could mangle them.
- **Fix**: Use YAML-aware Python to fix port numbers instead of sed.

### IB-3: Deploy Script No Rollback on Failure
- **File**: `scripts/deploy_aws_swarm.sh`
- **Impact**: Failed `docker stack deploy` leaves stack in unknown state.
- **Fix**: Snapshot current `docker service ls` before deploy, restore on failure.

### IB-4: auto_submit_jobs.sh Spark URL Wrong
- **File**: `scripts/auto_submit_jobs.sh` (line 5)
- **Impact**: `SPARK_HEALTH_URL` defaults to `http://127.0.0.1:8080`, but Spark Master internal port is 8080 (published as 8082). Inside Swarm, this resolves correctly via `spark-master:8080`. But the script runs in a separate container that may not resolve `spark-master`.
- **Fix**: Use `SPARK_HEALTH_URL=${SPARK_HEALTH_URL:-http://spark-master:8080}` and document container must be on same overlay network.

### IB-5: DuckDNS Token Exposed in Logs
- **File**: `scripts/duckdns_auto.sh`
- **Impact**: On failed update, token is printed to stdout with the error message. Visible in `docker service logs duckdns-auto`.
- **Fix**: Mask token in log output.

### IB-6: No Prometheus/Loki Running in Production
- **Image**: Most monitoring services at 0/1 replicas
- **Impact**: No metrics collection, no centralized logging. Troubleshooting requires per-service logs.
- **Fix**: Enable prometheus/loki with proper resource limits for worker node.

### IB-7: Migration File Prefix Conflict
- **Files**: `backend/migrations/004_agents_metadata.sql`, `backend/migrations/004_phaseC_news_enhancements.sql`
- **Impact**: Both use 004 prefix. Execution order is alphabetical, so `004_agents_metadata.sql` runs before `004_phaseC_news_enhancements.sql`. If they modify related tables, order matters.
- **Fix**: Rename to `005_phaseC_news_enhancements.sql`.

### IB-8: No Health Check on Critical Services
- **Missing from**: producer, flink-jobmanager, flink-taskmanager, spark-worker, schema-registry
- **Impact**: Docker doesn't know if these are healthy. A stuck producer goes undetected until data stops flowing.
- **Fix**: Add Docker health check to each (e.g., producer: `CMD curl -sf http://localhost:8000/health`)

---

## AI Service Issues

### AI-1: litellm/sentence-transformers Installed at Runtime
- **Impact**: First request triggers `pip install` inside FastAPI lifespan thread. Creates 5-30s delay on first /api/ai/chat call.
- **Fix**: Include in base image `docker/fastapi/requirements.txt`.

### AI-2: ai-service Container is Scaffolded (0/1)
- **Impact**: docker-compose.ai.yml defines `ai-service` but it runs `echo "ai-service placeholder"` and exits.
- **Fix**: Either remove or implement actual standalone service.

### AI-3: RAG Knowledge Base Docs May Be Stale
- **Files**: `docs/ai/knowledge_base/approved/*.md`
- **Impact**: AI assistant answers based on potentially outdated knowledge docs.
- **Fix**: Add knowledge doc versioning and periodic re-ingestion.

---

## Performance Bottlenecks

| Bottleneck | Component | Impact | Suggested Fix |
|---|---|---|---|
| Flush 500ms BATCH | Flink writers | Dominates end-to-end latency | Reduce to 200ms for ticker/trades |
| No Redis cache for klines | candle_service.py | InfluxDB per request | Add TTL cache |
| WebSocket 50ms poll all-timeframes | websocket.py | 1MB+ payloads per push | Delta-only pushes |
| Flux query per klines call | candle_service.py | 10-50ms overhead | Batch multiple intervals |
| 30+ Python threads | producer/main.py | GIL contention | Use asyncio + multiprocessing |
| Trino connection per query | candle_service.py | TCP connection churn | Connection pool |

---

## Documentation Debt

| Doc | Issue | Fix |
|---|---|---|
| `docs/DEPLOY_SWARM.md` | Moved to trash, but referenced by old worktrees | Remove from trash or keep as historical ref |
| `README.md` version | Was 0.25.36, updated to 0.25.41 | ✅ Done |
| `SYSTEM.md` | Stale container names, compose-only flow | Forward-ref to docs/system/ added ✅ |
| `AGENTS.md` version | Was 0.25.0 | Updated ✅ |
| `docs/final_data_flow.md` (263KB) | Very large, likely stale ASCII art | Needs audit |
