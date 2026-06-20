# Data Pipeline — src/

Full data ingestion from exchange WebSockets through Kafka, Flink processing, and output to Redis/InfluxDB.

## Cross-Component Data Flow

```
EXCHANGE (Binance WebSocket)
  │  wss://stream.binance.com:9443/stream
  ▼
PRODUCER (src/producer/main.py)
  │  Thread per symbol, Avro serialization
  ├──→ KAFKA (crypto_ticker, crypto_klines, crypto_trades, crypto_depth)
  │     3 brokers, 12 partitions, RF=3, LZ4, retention 48h
  │
  ├──→ DirectRedisWriter (bypass when Kafka/Flink down)
  │     Dynamic health gate via health_monitor
  │     Pool: 50 connections, configurable
  │
  ▼
FLINK (src/processing/pipeline.py)
  │  PyFlink Streaming, parallelism=12, 2 TMs
  │
  ├── keydb_ticker    → ticker:latest:{ex}:{sym} (String)
  │                      ticker:history:{ex}:{sym} (Sorted Set)
  │
  ├── keydb_kline     → candle:1s:{sym} (Sorted Set, BATCH 500ms)
  │                      candle:1m:{ex}:{sym} (Sorted Set, BATCH 500ms)
  │
  ├── kline_aggregator→ Stateful 1s→1m KeyedProcessFunction
  │                      On 1m watermark: emit OHLCV, forward-fill on gap
  │
  ├── keydb_trades    → trade:latest:{ex}:{sym} (List, cap 200)
  │
  ├── keydb_depth     → orderbook:{ex}:{sym} (Hash: bids/asks JSON)
  │
  ├── indicators      → indicator:{ex}:{sym}:{interval} (String)
  │                      Writes SMA/EMA/RSI/MACD/Bollinger/Stoch/ATR/OBV/VWAP
  │
  ├── influxdb_ticker → market_ticks InfluxDB measurement
  │
  ├── influxdb_kline  → candles InfluxDB measurement
  │
  ├── whale_alert     → whale:alert:{ex}:{sym} + InfluxDB whale_alerts
  │
  └── liquidity_heatmap→ InfluxDB liquidity_heatmap measurement
```

---

## Exchange Layer (src/exchanges/)

### base.py — ExchangeClient ABC

```python
class ExchangeClient(ABC):
    name: str                          # "binance" | "okx"
    symbols: list[str]                 # Subscribed symbols
    async def subscribe()              # WS subscription
    async def start()                  # Main event loop
    async def stop()                   # Clean shutdown
    def get_recent_trades()            # Fallback REST query
```

**Strengths**: Clean ABC with clear interface. `name` property added in v0.25.41.

**Weakness**: No `disconnect()` callback or reconnection policy in base class. Each exchange implements its own reconnection.

### binance/client.py — Primary Exchange

**Connection**: `wss://stream.binance.com:9443/stream` (combined streams)
**Subscription**: Batched per connection (max 200 streams). Each symbol subscribes to 4 streams: ticker, kline_1s, depth, trade.
**Reconnection**: Exponential backoff, max 30s, resubscribes all streams.
**Symbol selection**: `fetch_symbols()` returns alphabetical top-N USDT pairs (default 200). Paginates through Binance exchangeInfo.

**Critical Bug — Symbol Selection Strategy**:
- Uses alphabetical sorting, NOT volume ranking
- `audit_data_coverage.py` flags this as "fake cow" risk
- High-volume symbols like `COMPUSDT` may be excluded if alphabetically after `Z`
- **Impact**: ~5-10% miss rate for high-volume pairs vs volume-ranked top 200
- **Fix**: Replace alphabetical sort with Binance 24hr ticker volume sort

**Data Mappers** (binance/mappers.py):
- `binance_ticker_to_kafka()` — Normalizes Binance 24hr ticker → Avro schema
- `binance_kline_to_kafka()` — Normalizes 1s kline → Avro schema
- `binance_depth_to_kafka()` — Normalizes order book → Avro schema
- `binance_trade_to_kafka()` — Normalizes trade → Avro schema
- All handle field renaming and type conversion

### binance/redis_writer.py — DirectRedisWriter

**Purpose**: Bypass writer when Kafka/Flink are unavailable.
**Activation**: `health_monitor.is_direct_redis_active()` — dynamic check every cycle.
**Pool**: Configurable via `DIRECT_REDIS_POOL_SIZE` (default 50), using `redis.ConnectionPool`.

**Bug (Fixed in v0.25.41)**:
- `__init__` was calling `redis.ConnectionPool()` before `import redis` → `NameError`
- Fixed by adding `import redis` at module level

**Remaining Issue**:
- DirectRedisWriter flushes to Redis per-event, not batched. Under high volume (e.g., 30+ symbols), individual Redis writes create significant overhead.

### okx/client.py — Opt-in Exchange

**Connection**: `wss://ws.okx.com:8443/ws/v5/public`
**Protocol**: Login frame → subscribe frame (different from Binance's combined streams)
**Symbols**: Filtered to 20 well-known pairs (no alphabetical top-N)
**Kline interval**: 1m only (no 1s support from OKX)

**Known Issues**:
- Kline interval mapping **fixed** in v0.25.41 (was hardcoded "1s")
- No depth or trade stream support (ticker + klines only)
- Filtering to 20 pairs misses long-tail altcoins

---

## Producer (src/producer/main.py)

**Thread Model**:
```
Main Thread
├── health_monitor thread (checks Kafka/Flink health every 10s)
├── Symbol thread 1: Binance BTCUSDT (WS + Kafka producer)
├── Symbol thread 2: Binance ETHUSDT (WS + Kafka producer)
├── ... up to 200 symbol threads
│
├── (if ENABLE_OKX=true)
│   └── Symbol threads for OKX pairs
│
└── Per-symbol DirectRedisWriter thread (if bypass active)
```

**Startup Flow**:
1. Parse env vars: `MAX_SYMBOLS`, `ENABLE_OKX`, Kafka brokers
2. `health_monitor.start()` — background thread pings Kafka brokers + Flink JobManager
3. For each exchange:
   - `ExchangeClient.fetch_symbols()` → list of symbols
   - For each symbol: spawn `asyncio.run(stream_handler(symbol))` in thread
4. Each stream handler:
   - Subscribe to exchange WebSocket
   - Loop: receive message → map to Avro → produce to Kafka
   - If `health_monitor.is_direct_redis_active()`: also write to DirectRedisWriter
   - On disconnect: log error, reconnect with backoff

**Health Monitor** (`health_monitor.py`):
- Pings Kafka (`list_topics`) and Flink (`/jobs/overview`) every 10s
- Sets `direct_redis_active = True` when both Kafka and Flink are unreachable for 60+ seconds
- Resets to `False` when either recovers
- Exposed via `is_direct_redis_active()` — called by every stream handler

**Bug — Topic auto-creation**:
- `main.py` sends `KAFKA_AUTO_CREATE_TOPICS_ENABLE=false` but producer's Kafka client doesn't check if topics exist before writing. If topics weren't created by `create_kafka_topics.sh`, the producer silently drops messages.

**Bug — OKX always-on threads**:
- When `ENABLE_OKX=false`, the code still evaluates OKX symbol list (which is empty) and spawns 0 threads. But the health_monitor still tracks OKX streams. Minor overhead, no functional impact.

---

## Flink Processing (src/processing/)

### pipeline.py — Main Job

**Parallelism**: 12 (matches Kafka partitions)
**Checkpointing**: Every 60s (exactly-once semantics)
**Watermark**: 5s event-time out-of-orderness

**Consumed Topics**:
```
crypto_ticker → FlatMap → keydb_ticker + influxdb_ticker
crypto_klines → FlatMap → keydb_kline + kline_aggregator + influxdb_kline
crypto_trades → FlatMap → keydb_trades + whale_alert
crypto_depth  → FlatMap → keydb_depth + liquidity_heatmap
```

**Each operator**:
1. Deserializes Avro using Confluent's `AvroDeserializationSchema`
2. Maps to internal dict
3. Writes to Redis/InfluxDB via `RichSinkFunction` (BATCH flush every 500ms)

### kline_aggregator.py — 1s → 1m Aggregation

**KeyedProcessFunction** keyed by `(exchange, symbol)`.
- Accumulates 1s candles in `ValueState`
- On 1m watermark: computes OHLCV from accumulated candles
- Emits to `candle:1m:{exchange}:{symbol}` in Redis
- Forward-fills close price if no data arrived in current 1m window

**Bug — Forward-Fill creates phantom candles**:
- If no 1s candle arrives for 2 minutes, the aggregator emits a candle at the 1m boundary with `close = previous_close`. The volume is 0.
- Frontend shows this as a flat candle with no volume — users interpret this as "exchange was down" or "trading halted."
- **Impact**: Low-volume symbols show incorrect closing prices on every gap.
- **Fix**: Only emit candle if at least one 1s candle was received. Or set `is_closed=false` on forward-filled candles.

### deps.zip Strategy

PyFlink requires Python dependencies bundled as a ZIP.
- Built at job submission time by `auto_submit_jobs.sh` or `submit_flink.sh`
- Includes: `src/common/` modules + `src/processing/writers/` modules
- Flattened structure: `writers/filename.py` (without full source tree)

**Bug — duplicate deps.zip logic**:
- `auto_submit_jobs.sh` (lines 28-44) and `submit_flink.sh` (all lines) both build deps.zip
- Logic is identical but maintained separately → drift risk
- The `src/processing/deps.zip` committed to git is a stale pre-built version (not used at runtime)

**Bug — writers/__init__.py handling**:
- When `processing/writers/__init__.py` doesn't exist, creates an empty one
- But the ZipFile `writestr` writes to wrong path: `writers/__init__.py` but the actual structure is `processing/writers/__init__.py`
- This means imports in Flink jobs may fail for cross-writer references

---

## Writers Deep Dive

### keydb_ticker.py
- **Redis Key**: `ticker:latest:{exchange}:{symbol}` (String, JSON)
- **Redis Key**: `ticker:history:{exchange}:{symbol}` (Sorted Set, score=timestamp_ms, member=JSON)
- **Flush**: Per-event (no batching)
- **Exchange Field**: ✅ Preserved

### keydb_kline.py
- **Redis Key**: `candle:1s:{symbol}` (Sorted Set, BATCH written)
- **Redis Key**: `candle:1m:{exchange}:{symbol}` (Sorted Set, BATCH written)
- **Flush**: Every 500ms (accumulated buffer)
- **Exchange Field**: ✅ Preserved for 1m, ⚠️ Missing for 1s (no exchange prefix)

### keydb_depth.py
- **Redis Key**: `orderbook:{exchange}:{symbol}` (Hash: `bids` + `asks` as JSON arrays)
- **Flush**: Per-snapshot
- **Exchange Field**: ❌ **DROPPED** — always defaults to `binance`
- **Known Bug**: AGENTS.md flags this. Fix needs `exchange` column in depth DDL + SELECT update.

### keydb_trades.py
- **Redis Key**: `trade:latest:{exchange}:{symbol}` (List, capped at 200, LTRIM)
- **Flush**: Per-event
- **Exchange Field**: ✅ Preserved

### indicators.py
- **Redis Key**: `indicator:{exchange}:{symbol}:{interval}` (String, JSON)
- **InfluxDB**: Writes to `indicators` measurement
- **Indicators**: SMA, EMA, RSI, MACD, Bollinger Bands, Stochastic, ATR, OBV, VWAP
- **Flush**: Per-calculation
- **Exchange Field**: ⚠️ Used in key but not always consistent

### influxdb_ticker.py / influxdb_kline.py
- **InfluxDB Measurement**: `market_ticks` / `candles`
- **Tags**: `symbol`, `exchange`, `interval`
- **Fields**: OHLCV for candles, close/bid/ask/volume for ticker
- **Flush**: BATCH every 500ms

### Whale Alert
- Threshold: Configurable trade size (default ±$100k)
- Redis: `whale:alert:{exchange}:{symbol}` (String, JSON)
- InfluxDB: `whale_alerts` measurement
- Triggered from trade stream

### Liquidity Heatmap
- Reads `orderbook:{exchange}:{symbol}` hash
- Aggregates bids/asks into price buckets
- Writes to InfluxDB `liquidity_heatmap` measurement
- Bucket size: Configurable (default 1% price intervals)

---

## Cross-Component Cooperation Patterns

### Pattern 1: Normal Path (Kafka+Flink healthy)

```
Producer → Avro → Kafka → Flink → Redis + InfluxDB
                                    │
                          FastAPI ←──┘  (reads Redis for hot data)
                          Browser ←── WebSocket (50ms poll)
```

**Latency**: Exchange → Producer (50-200ms) → Kafka (5-50ms) → Flink (100-500ms) → Redis
**Total**: ~200-750ms end-to-end for candle updates
**Bottleneck**: Flink BATCH flush (500ms) dominates latency

### Pattern 2: Bypass Path (Kafka or Flink down >60s)

```
Producer → DirectRedisWriter → Redis
                                │
                      FastAPI ←──┘
```

**Activation**: `health_monitor` detects Kafka/Flink unreachable for 60+ seconds
**Latency**: ~50-100ms (no Kafka serialization or Flink processing)
**Risk**: Data loss on producer crash. No InfluxDB writes during bypass.

### Pattern 3: Historical Query (beyond Redis retention)

```
FastAPI → InfluxDB (last 90 days)
       → Trino → Iceberg/MinIO (beyond 90 days)
```

**Latency**: InfluxDB 10-50ms, Trino 50-500ms

### Pattern 4: WebSocket Streaming

```
Flink → Redis (candle:1m:binance:BTCUSDT)
                         │
FastAPI WebSocket ←──────┘  (50ms poll)
       │
Browser ←───────────────────  (50ms push)
```

---

## Known Data Integrity Issues

| Issue | Component | Impact | Fix Status |
|---|---|---|---|
| Exchange field dropped in depth | keydb_depth.py | All depth shows as binance | Unfixed |
| Exchange field omitted in Spark dedup | lakehouse/pipeline.py | Multi-exchange data collapsed | Unfixed |
| Forward-fill phantom candles | kline_aggregator.py | Low-volume symbols show wrong close | Unfixed |
| Symbol selection alphabetical | binance/client.py | ~5-10% high-volume symbols missed | Unfixed |
| deps.zip duplicate build logic | auto_submit_jobs.sh + submit_flink.sh | Code drift | Unfixed |
| deps.zip init.py path mismatch | auto_submit_jobs.sh | Cross-writer import failures | Unfixed |
| Trino connection leak on error | candle_service.py | Connection pool exhaustion | Unfixed |
| No topic existence check | producer/main.py | Silent message drops | Unfixed |
| Flux query injection risk | candle_service.py | Low risk (validated upstream) | Low |
