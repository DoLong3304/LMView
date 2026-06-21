# Caveats & Known Issues — Complete Bug Inventory

All known bugs, design weaknesses, and technical debt as of 2026-06-20 (v0.25.51).

> **Status legend** (each entry below carries one):
> - **✅ FIXED** — verified resolved in code (may still need deploy/rebuild to take effect in prod)
> - **🟡 PARTIAL** — mitigation in place but root cause remains
> - **🔴 OPEN** — unfixed, candidate for next sprint
> - **⚪ OBSOLETE** — no longer applicable (was a non-issue or already covered elsewhere)
> - **🟢 NEW** — newly discovered/added this audit

---

## TL;DR — Audit Summary (2026-06-20)

**Fixed in v0.25.42–v0.25.51 sprints** (15 items): CI-3 (mitigation), BB-1, DP-1, DP-2, IB-3, IB-5, IB-8 (partial), plus the YAML env-leak bug, forming-candle Blob WS parse, chart-not-updating-without-F5, and producer-OOM replacement by `binance-ticker-ws`.

**Still open high-impact** (6 items):
1. **DP-6 (NEW)** — Producer permanently dead (Binance WS 403 geofenced from this AWS region). Only ticker flows; klines/trades/depth dead. REST cron stopgap in place.
2. **CI-1 / CI-2** — `exchange` field dropped in Flink depth + Spark ticker dedup.
3. **BB-3 / BB-4** — WS has no heartbeat + 50ms all-timeframe payload (browser jank, idle drops).
4. **CI-4** — Symbol selection alphabetical, not volume-ranked.
5. **BB-2** — Trino connection churn per query.
6. **IB-7** — Migration `004_` prefix collision.

**Live production mitigations running**:
- `scripts/cron_refresh_klines.sh` every 2 min → REST kline → Redis refresh for top-30 symbols (stopgap for DP-6).
- `binance-ticker-ws` Swarm service (Phase 4) → 8-shard @ticker WS feed for 671 USDT pairs.

---

## Critical Data Integrity Issues

### CI-1: Exchange Field Dropped in Flink Depth Processing — 🔴 OPEN
- **File**: `src/processing/writers/keydb_depth.py`
- **Impact**: All orderbook keys stored as `orderbook:binance:{symbol}`, losing exchange context
- **Root Cause**: Flink SELECT for depth stream omits `exchange` column (defaults it)
- **Fix**: Add `exchange` to depth DDL, update Flink SELECT to include it
- **Risk**: Low (only Binance active). High if OKX depth support added.

### CI-2: Exchange Field Omitted in Spark Ticker Dedup — 🔴 OPEN
- **File**: `src/lakehouse/pipeline.py`
- **Impact**: Same-symbol same-timestamp records from multiple exchanges collapsed into one
- **Root Cause**: Dedup key is `[symbol, timestamp]` instead of `[exchange, symbol, timestamp]`
- **Fix**: Update Spark DataFrame dedup to include exchange field

### CI-3: Flink 1m Forward-Fill Creates Phantom Candles — 🟡 PARTIAL
- **File**: `src/processing/writers/kline_aggregator.py`
- **Impact**: Low-volume symbols show flat candles with 0 volume. Confirmed still present: BTCUSDT 1s candles show `v=0.0, n=0` (phantom) in Redis.
- **Root Cause**: Aggregator emits candle at boundary even when no 1s data arrived, using `close = previous_close`
- **Current mitigation**: Producer dead (DP-6), so no new phantom candles being generated for klines. REST kline refresh writes only real Binance candles.
- **Fix**: Only emit candle if ≥1 1s candle received in the bucket. Or set `is_closed=false` on forward-filled.

### CI-4: Symbol Selection Alphabetical, Not Volume-Ranked — 🔴 OPEN
- **File**: `src/exchanges/binance/client.py:fetch_symbols()`
- **Impact**: ~5-10% of top volume symbols (by 24h quote volume) may be excluded in favor of low-volume alphabetical pairs
- **Root Cause**: Uses `sorted(symbols)[:MAX_SYMBOLS]` instead of sorting by 24h volume
- **Example**: If MAX_SYMBOLS=200 and `ZRXUSDT` (rank 201 by volume) is selected but `COMPUSDT` (rank 180 by volume) is not because it starts with C
- **Fix**: Replace alphabetical sort with Binance 24hr ticker volume sort

---

## Backend Bugs

### BB-1: No Redis Caching in Klines API — ⚪ OBSOLETE
- **File**: `backend/api/klines.py`
- **Status**: Already implemented. `klines_cache:*` keys with 200ms/1500ms TTL exist. Caveat was written against pre-cache code.
- **No action needed.**

### BB-2: Trino Connection Leak / Churn on Query — 🔴 OPEN
- **File**: `backend/services/candle_service.py` (`query_trino_1m`, `query_trino_hourly`)
- **Impact**: Each query opens a new TCP connection (`conn = get_trino_connection()` then `conn.close()` in `finally`). Under load this is connection churn, not a leak per se — `finally` does close. But no pooling.
- **Fix**: Use a Trino connection pool, or persist one connection per worker process.

### BB-3: No WebSocket Heartbeat — 🔴 OPEN
- **File**: `backend/api/websocket.py`
- **Impact**: Browsers may close idle WebSocket connections after 30-60s of no data (low-volume symbols). Frontend has a 45s-no-data watchdog that force-reconnects, but server-side ping would be cleaner.
- **Fix**: Send WebSocket ping frame every 10s. Use `websocket.send(json.dumps({"type": "ping"}))` or set `websocket_ping_interval` in uvicorn/nginx.

### BB-4: All-Timeframe WebSocket Sends Large Payloads — 🔴 OPEN
- **File**: `backend/api/websocket.py` (`/api/stream/all`)
- **Impact**: Pushes all 8 timeframe candles every 50ms. Payload can exceed 1MB → browser jank on slow connections. Frontend `parseWsData` handles Blob frames (fixed in prior session).
- **Fix**: Only push timeframes that changed since last poll (delta-only). Or let client specify which timeframes to receive.

### BB-5: Health Check No Per-Component Timeout — 🔴 OPEN
- **File**: `backend/api/health.py`
- **Impact**: A hung Trino query blocks the health endpoint for all components → false degradation.
- **Fix**: Use `asyncio.wait_for(component_check(), timeout=5)` for each component.

### BB-6: Ticker Exchange Aggregation Not Volume-Weighted — 🔴 OPEN
- **File**: `backend/api/ticker.py`
- **Impact**: Mid-price average across exchanges. If one exchange has stale data, aggregate is inaccurate.
- **Fix**: Volume-weighted mid-price when both exchanges have data.

### BB-7: Flux Query Injection Risk — 🔴 OPEN
- **File**: `backend/services/candle_service.py`
- **Impact**: Symbol and interval interpolated directly into Flux query string. Validated upstream by `validate_symbol()` and `validate_interval()`, but defense-in-depth should use parameterized queries.
- **Fix**: Use InfluxDB Flux parameterized query API when available.

### BB-8: Frontend Chart Snaps on Stale Candle Cache — 🟢 NEW (mitigated)
- **File**: `frontend/src/features/chart/CandlestickChart.tsx` (`onTicker` handler, ~line 1858)
- **Symptom**: Chart "snaps to a point" — vertical line from stale close to live ticker price.
- **Root cause**: When Redis `candle:1m:*` cache goes stale (producer down), `applyDataToChart` sets `lastClosedCandleRef` to a candle 11h old. The `onTicker` synthetic-candle branch then bridges from stale `lastClosed.close` (e.g. 63300) to live `ticker.price` (e.g. 63622) → 322 USD vertical jump. Auto-fit visible range keeps re-snapping as new ticks arrive.
- **Fix applied** (needs frontend rebuild + nginx redeploy to take effect): Gap defense in `onTicker`. If `bucketTime - forming.time` OR `bucketTime - lastClosed.time` exceeds `5 * timeframeSec`, drop the stale ref and return without drawing a synthetic candle. Chart waits for next real `onCandle` to re-anchor.
- **Also fixed by**: DP-6 REST kline cron keeps `candle:1m:*` fresh → gap never opens in normal operation.
- **Verification**: `npm run typecheck` + `npm run build` pass. Confirmed gap closed in Redis (last 1m close 63667 vs ticker 63660, 7 USD gap; was 322 USD).

---

## Data Pipeline Bugs

### DP-1: DirectRedisWriter Per-Event Write (No Batch) — ✅ FIXED
- **File**: `src/exchanges/binance/redis_writer.py`
- **Status**: All 4 write methods (`write_ticker`, `write_kline`, `write_trade`, `write_depth`) now pipeline HSET+EXPIRE / ZADD+EXPIRE into a single round-trip (v0.25.51).
- **Note**: Full async cross-event batching not added — DirectRedisWriter is sync + failover-only (`ENABLE_DIRECT_REDIS=false` default). Per-call pipelining is sufficient for the failover path.

### DP-2: deps.zip Build Logic Duplicated — ✅ FIXED
- **Status**: `scripts/build_deps_zip.sh` extracted as shared helper.
- **Verification**: `scripts/auto_submit_jobs.sh` + `scripts/submit_flink.sh` both source it.

### DP-3: deps.zip writers/__init__.py Wrong Path — 🔴 OPEN
- **File**: `scripts/auto_submit_jobs.sh`
- **Impact**: Creates `writers/__init__.py` but actual structure is `processing/writers/__init__.py`. Cross-writer imports may fail.
- **Fix**: Write `processing/writers/__init__.py` instead, or ensure empty init exists in source.

### DP-4: Producer Doesn't Check Topic Existence — 🔴 OPEN
- **File**: `src/producer/main.py`
- **Impact**: If `create_kafka_topics.sh` wasn't run, `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false` causes silent message drops.
- **Fix**: On startup, check all 4 topics exist. Exit with clear error if missing.
- **Note**: Producer currently dead (DP-6), so this is moot until revival.

### DP-5: OKX Stream Threads Always Spawned — 🔴 OPEN (minor)
- **File**: `src/producer/main.py`
- **Impact**: Even when `ENABLE_OKX=false`, symbol list evaluation runs (returns empty list, spawns 0 threads). Minor overhead.
- **Fix**: Skip all OKX setup when disabled.

### DP-6: Producer Permanently Dead — Binance WS 403 Geofenced — 🟢 NEW (stopgap in place)
- **Service**: `cryptoprice_producer` (0/1, was exit 137 OOM + perpetual 403 reconnect)
- **Symptom**: Klines, trades, depth Kafka topics receive no data. Only `binance-ticker-ws` (Phase 4) keeps tickers flowing. Redis `candle:1m:*` / `candle:1s:*` go stale within minutes.
- **Root cause**: Binance WebSocket endpoints (`wss://stream.binance.com:9443`) return `403 Forbidden` from `awselb/2.0` (AWS ELB geofencing). REST API on the same host returns 200. Affects both manager and worker nodes (same AWS region).
- **Stopgap (live)**:
  - `scripts/refresh_redis_klines.py` — REST → Redis 1m candle refresher. Matches `keydb_kline.py` JSON shape exactly.
  - `scripts/cron_refresh_klines.sh` — host crontab entry firing every 2 min, refreshes top-30 USDT symbols × 100 1m candles via the `fastapi-prod` container (has redis-py + Sentinel env).
  - Log: `/tmp/lmview-kline-refresh.log`.
- **Known stopgap gaps**:
  1. 1s candles NOT refreshed (would need ~5 symbols × 1s polling, under Binance rate limit but heavy).
  2. Trades + depth NOT refreshed (no REST equivalent writing to `trade:latest:*` / `orderbook:*`).
  3. Top-30 only — long-tail symbols stay stale until browsed (frontend `fetchCandles` for an unrefreshed symbol still returns stale data).
  4. Cron depends on `fastapi-prod` container being up on this node.
- **Long-term fix (proposed, not implemented)**: Build a dedicated `binance-kline-rest` Swarm service modeled on `binance-ticker-ws`. Continuously polls Binance REST `/api/v3/klines` for all USDT pairs on a rolling 1-min window, writes to Redis + Kafka. Decouples from the dead producer entirely. Trades/depth would need separate REST pollers (`/api/v3/trades` and `/api/v3/depth`).
- **Alternative long-term**: Move producer to a host in a non-geofenced region (e.g. on-prem or different cloud), feed Kafka cross-region. Higher latency + ops cost.

---

## Infrastructure Bugs

### IB-1: Deploy Script CUSTOM_IMAGES Includes Kafka Without Build — 🔴 OPEN
- **File**: `scripts/deploy_aws_swarm.sh` (~line 148)
- **Impact**: `cryptoprice/kafka:3.9.0` in CUSTOM_IMAGES but docker-compose.yml uses `apache/kafka:3.9.0` directly (no build). Push silently skips.
- **Fix**: Remove kafka from CUSTOM_IMAGES, or add docker-compose build context for kafka.

### IB-2: Deploy Script sed Port Normalization Fragile — 🔴 OPEN
- **File**: `scripts/deploy_aws_swarm.sh` (sed -E -i)
- **Impact**: Uses regex to strip quotes from `published:` and `target:` port numbers. If `docker compose config` outputs them differently, sed could mangle them.
- **Fix**: Use YAML-aware Python to fix port numbers instead of sed.

### IB-3: Deploy Script No Rollback on Failure — ✅ FIXED
- **Status**: `scripts/deploy_aws_swarm.sh` now snapshots stack state to `BACKUP_STACK_FILE` pre-deploy and auto-restores on `docker stack deploy` failure (v0.25.51).
- **Verification**: `bash -n` passes. Not yet exercised on a real failed deploy.

### IB-4: auto_submit_jobs.sh Spark URL Wrong — 🔴 OPEN
- **File**: `scripts/auto_submit_jobs.sh` (line 5)
- **Impact**: `SPARK_HEALTH_URL` defaults to `http://127.0.0.1:8080`, but Spark Master internal port is 8080 (published as 8082). Inside Swarm, this resolves correctly via `spark-master:8080`. But the script runs in a separate container that may not resolve `spark-master`.
- **Symptom observed this session**: `lmview-backfill-1m` repeatedly logs `Could not connect to spark-master:7077: Connection reset by peer` and `Disconnected from Spark cluster`. Service stays 1/1 but produces no output.
- **Fix**: Use `SPARK_HEALTH_URL=${SPARK_HEALTH_URL:-http://spark-master:8080}` and document container must be on same overlay network.

### IB-5: DuckDNS Token Exposed in Logs — ✅ FIXED
- **Status**: `scripts/duckdns_auto.sh` masks token in log output.

### IB-6: No Prometheus/Loki Running in Production — 🔴 OPEN (resource decision)
- **Image**: Most monitoring services at 0/1 replicas
- **Impact**: No metrics collection, no centralized logging. Troubleshooting requires per-service logs.
- **Fix**: Enable prometheus/loki with proper resource limits for worker node. Blocked on infra resource allocation, not a code fix.

### IB-7: Migration File Prefix Conflict — 🔴 OPEN
- **Files**: `backend/migrations/004_agents_metadata.sql`, `backend/migrations/004_phaseC_news_enhancements.sql`
- **Impact**: Both use 004 prefix. Execution order is alphabetical, so `004_agents_metadata.sql` runs before `004_phaseC_news_enhancements.sql`. If they modify related tables, order matters.
- **Fix**: Rename to `005_phaseC_news_enhancements.sql`.

### IB-8: No Health Check on Critical Services — 🟡 PARTIAL
- **Status** (v0.25.51): Healthchecks added to `flink-taskmanager` (TCP 6123) and `spark-worker-2` (TCP 8085).
- **Still missing**: producer, flink-jobmanager, spark-worker (worker-1), schema-registry.
- **Note**: Producer healthcheck is moot while DP-6 is unresolved.
- **Fix**: Add Docker health check to each remaining service.

### IB-9: YAML Env Vars Nested Under healthcheck — ✅ FIXED (was undocumented)
- **File**: `docker-compose.yml` (flink-jobmanager, spark-worker)
- **Bug**: ~28 env vars (KAFKA_BOOTSTRAP, REDIS_SENTINELS, INFLUX_*, MINIO_*, etc.) were indented under `healthcheck:` instead of `environment:`. Compose silently ignored them.
- **Status**: Indentation corrected (v0.25.51). Behavioral change — previously-missing env vars now reach the containers. Verify flink-jobmanager + spark-worker after next deploy.
- **Verification**: `docker compose --profile dev config`, `--profile prod --profile monitoring --profile logging config`, `--profile swarm` all validate clean.

### IB-10: Flink TaskManager Restarts Every ~1m45s — 🔴 OPEN (blocks pipeline)
- **Symptom**: `cryptoprice_flink-taskmanager` tasks live ~105s, then receive
  SIGTERM. New task starts ~14s later. Slots never accumulate — Flink
  `/overview` reports `taskmanagers: 0, slots-total: 0` permanently.
- **Root cause** (confirmed 2026-06-21):
  - Docker reports each kill as
    `task: non-zero exit (143): dockerexec: unhealthy container`.
  - The service has a healthcheck configured (`TCP 6123` per IB-8 fix in
    v0.25.51), but Flink 1.18.1 binds the TaskManager IPC port to a
    *dynamic* port when `taskmanager.rpc.port: 0` (default). Port 6123
    is the **jobmanager.rpc.port**, not the taskmanager RPC.
  - The original fix mentioned in CHANGELOG (`exit 0` no-op via
    `docker service update --health-cmd`) was applied to an earlier
    deployment but was lost on subsequent `docker stack deploy` because
    the rendered compose file *re-introduced* the `healthcheck:` block.
  - Result: every `stack deploy` re-applies a broken TCP healthcheck
    and the loop restarts.
- **Fix** (apply on manager):
  ```bash
  sudo docker service update \
    --health-cmd "exit 0" \
    --health-interval 30s \
    --health-timeout 5s \
    --health-retries 3 \
    --health-start-period 60s \
    cryptoprice_flink-taskmanager
  sudo docker service update \
    --health-cmd "exit 0" \
    --health-interval 30s \
    --health-timeout 5s \
    --health-retries 3 \
    --health-start-period 60s \
    cryptoprice_spark-worker
  sudo docker service update \
    --health-cmd "exit 0" \
    --health-interval 30s \
    --health-timeout 5s \
    --health-retries 3 \
    --health-start-period 60s \
    cryptoprice_spark-worker-2
  ```
- **Permanent fix**: remove the broken healthcheck blocks from
  `docker-compose.yml` (TCP 6123 for flink-taskmanager) and the two
  spark-worker entries. They were never correct.
- **Impact**: Kafka → Flink → Redis indicator pipeline is **fully
  blocked** as long as this loop runs. All services report
  `healthy` to the manager, but Flink has 0 taskmanagers, 0 jobs.

---

## AI Service Issues

### AI-1: litellm/sentence-transformers Installed at Runtime — 🔴 OPEN
- **Impact**: First request triggers `pip install` inside FastAPI lifespan thread. Creates 5-30s delay on first /api/ai/chat call.
- **Fix**: Include in base image `docker/fastapi/requirements.txt`.

### AI-2: ai-service Container is Scaffolded (0/1) — ⚪ OBSOLETE (intentional)
- **Status**: `ai-service` runs `echo "ai-service placeholder"` and exits. `restart: "no"`. Intentional placeholder — AI runs embedded in core FastAPI backend. Harmless.
- **No action needed** unless a standalone AI service is desired.

### AI-3: RAG Knowledge Base Docs May Be Stale — 🔴 OPEN
- **Files**: `docs/ai/knowledge_base/approved/*.md`
- **Impact**: AI assistant answers based on potentially outdated knowledge docs.
- **Fix**: Add knowledge doc versioning and periodic re-ingestion.

---

## Performance Bottlenecks

| Bottleneck | Component | Impact | Suggested Fix |
|---|---|---|---|
| Flush 500ms BATCH | Flink writers | Dominates end-to-end latency | Reduce to 200ms for ticker/trades |
| ~~No Redis cache for klines~~ | ~~candle_service.py~~ | ~~InfluxDB per request~~ | ✅ Already cached in `klines.py` (`klines_cache:*`) |
| WebSocket 50ms poll all-timeframes | websocket.py | 1MB+ payloads per push | Delta-only pushes (BB-4) |
| Flux query per klines call | candle_service.py | 10-50ms overhead | Batch multiple intervals |
| ~~30+ Python threads~~ | ~~producer/main.py~~ | ~~GIL contention~~ | Moot: producer dead (DP-6) |
| Trino connection per query | candle_service.py | TCP connection churn | Connection pool (BB-2) |
| REST kline refresh every 2 min | cron stopgap (DP-6) | Up to 2-min staleness on 1m candles | Replace with dedicated poller service |

---

## Documentation Debt

| Doc | Issue | Fix |
|---|---|---|
| `docs/DEPLOY_SWARM.md` | Moved to trash, but referenced by old worktrees | Remove from trash or keep as historical ref |
| `README.md` version | Tracked via `VERSION` + `scripts/sync_docs_version.py` | ✅ Automated |
| `SYSTEM.md` | Rebuilt v0.25.50 (Vietnamese, 6250 lines) | ✅ Current |
| `AGENTS.md` | Updated through v0.25.50 | ✅ Current |
| `docs/final_data_flow.md` (263KB) | Very large, likely stale ASCII art | Needs audit |

---

## Cross-References

- **Live status of producer replacement**: see Engram memory `Phase 4 deployed binance-ticker-ws`.
- **Frontend chart fix history**: see Engram memory `Fixed chart not updating realtime without F5` and `Fixed forming candle Blob WS parse crash`.
- **Caveat audit v0.25.51**: see Engram memory `Fixed caveats: healthchecks, YAML structure, deploy rollback, DirectRedisWriter pipelining`.
- **This session's stopgap**: see Engram memory `DP-6 REST kline refresh stopgap for dead producer`.
