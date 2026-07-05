# Architecture Overview

LMView is a real-time cryptocurrency technical-analysis platform using **Lambda Architecture** across 3 layers, deployed on 3-node Docker Swarm.

## Lambda Architecture

```
Exchange WebSockets (Binance, OKX opt-in)
  │
  ▼
┌──────────────────────────────────────────────────────────┐
│ INGESTION (src/producer/main.py)                         │
│ WebSocket → Avro serialization → Kafka topics            │
│ Topics: crypto_ticker, crypto_klines, crypto_trades,     │
│         crypto_depth                                     │
│ 1s klines → DirectRedisWriter (always, bypass Kafka)     │
│ Other data → DirectRedisWriter (health-monitored failover)│
│ 1s klines → DirectRedisWriter (always, bypass Kafka)       │
│ 1s klines → binance-kline-ws 8-shard WS → Redis (primary)  │
│ REST poller (binance-kline-rest) → Redis (1m only)         │
└────────┬────────────────────────────────────────────────┘
         │
    ┌────▼────┐
    │  KAFKA  │  3 brokers, 12 partitions/topic, LZ4 compression
    │ 3.9.0   │  retention: 48h, RF=3, min ISR=2
    └────┬────┘
         │
    ┌────┴──────────────────────────────┐
    │                                  │
    ▼ SPEED LAYER                      ▼ BATCH/LAKEHOUSE LAYER
┌─────────────────────┐        ┌──────────────────────────────┐
│ Apache Flink 1.18.1 │        │ Apache Spark 3.5.5 Structured │
│ PyFlink streaming   │        │ Streaming → Iceberg tables   │
│ ~100-500ms latency  │        │ MinIO (S3) object storage    │
│ 2 TaskManagers,     │        │ PostgreSQL Iceberg catalog    │
│ parallelism=12      │        │ Trino SQL query engine        │
│ Writes Redis +      │        │ Medallion: Bronze→Silver→Gold │
│ InfluxDB (BATCH)    │        │ ~min-hr latency               │
└────────┬────────────┘        └──────────────┬───────────────┘
         │                                    │
    ┌────┴──────┐                    ┌────────┴────────┐
    │   Redis   │                    │   MinIO +       │
    │  Sentinel  │                    │   Iceberg       │
    │  1M + 2R +│                    │   5.6 GB data   │
    │  3 sent.  │                    │   Parquet files  │
    └────┬──────┘                    └────────┬────────┘
         │                                    │
    ┌────┴────────────────────────────────────┴──────────┐
    │              SERVING LAYER                          │
    │         FastAPI (REST + WebSocket)                  │
    │  Reads Redis (hot) → InfluxDB (warm) → Trino (cold) │
    │  Fallback chain: Redis → InfluxDB → Trino           │
    │  Auth: PostgreSQL sessions + JWT                    │
    │  18 API routers, 50ms WS poll loop                  │
    └─────────────────────┬──────────────────────────────┘
                          │
                    ┌─────▼──────┐
                    │   Nginx    │  TLS (Let's Encrypt)
                    │   reverse  │  Rate limiting, HSTS
                    │   proxy    │  gzip, security headers
                    └─────┬──────┘
                          │
                    ┌─────▼──────────────────┐
                    │  React 19 SPA           │
                    │  lightweight-charts     │
                    │  TailwindCSS + shadcn   │
                    │  i18n (en/vi)           │
                    │  WebSocket for realtime │
                    └─────────────────────────┘
```

## Cross-Component Cooperation Modes

### Mode 1: Normal Real-Time Flow
```
Binance WS → Producer → Avro/Kafka → Flink → Redis + InfluxDB
                                                │
FastAPI ←────────────────────────────────────────┘  (reads Redis)
  │
WS push (50ms) → Browser renders candle update
```

### Mode 2: 1s Klines Direct-to-Redis (Always-On)
```
Binance WS → Producer → DirectRedisWriter → Redis
                                              │
FastAPI ←──────────────────────────────────────┘
```
Applies to: **1s klines only**. 1s data ALWAYS goes directly to Redis
(bypassing Kafka/Flink latency). All other data uses Mode 1 or Mode 3.
No activation gate — 1s path is always live.

## Mode 3: Kafka/Flink Failure (Bypass)
```
Binance WS → Producer → DirectRedisWriter → Redis
                                              │
FastAPI ←──────────────────────────────────────┘
```
Applies to: tickers, trades, depth, 1m+ klines.
Activation: Kafka + Flink both unreachable for >60s (health_monitor)
Deactivation: Either Kafka or Flink recovers

### Mode 3: Historical Query
```
FastAPI → InfluxDB (last 90 days candles)
       → Trino → Iceberg/MinIO (beyond 90 days)
```
Fallback: If InfluxDB returns <limit rows, cascade to Trino

### Mode 4: Batch Analytics
```
Kafka → Spark Streaming → Iceberg Bronze
                         → Iceberg Silver (hourly)
                         → Iceberg Gold (hourly)
                              ↓
                         Trino queries ← FastAPI overview endpoints
```

## Storage Tiers

| Tier | Tech | Access Pattern | Latency | Retention | Volume |
|---|---|---|---|---|---|
| Hot cache | Redis Sentinel | Direct key lookup | <1ms | Minutes-hours | ~200MB |
| Warm TSDB | InfluxDB 2.7 | Flux queries | 10-50ms | 90 days | ~5GB |
| Cold lakehouse | Iceberg/MinIO + Trino | SQL | 50-500ms | Indefinite | ~5.6GB |
| Relational | PostgreSQL 16 + pgvector | SQL | 1-10ms | Indefinite | ~500MB |

## Service Placement Strategy (3-Node Swarm)

### Core Node (8 vCPU, 32 GB) — label `role=core`
- **Serving**: nginx-prod, fastapi-prod, producer (0/1, all WS disabled)
- **Data feeds**: binance-ticker-ws, binance-kline-rest, binance-depth-trades-rest, combined-stream-producer
- **AI**: ai-service, litellm, finbert-worker
- **Utilities**: registry, certbot-auto, duckdns-auto
- **Total**: ~14 services, ~12GB memory budget

### Data Node (8 vCPU, 32 GB) — label `role=data`
- **Storage**: postgres, redis-master/replicas/sentinels ×6, influxdb, minio
- **Messaging**: zookeeper, kafka-1/2/3, schema-registry
- **Total**: ~15 services, ~10GB memory budget

### Compute Node (8 vCPU, 32 GB) — label `role=compute`
- **Streaming**: flink-jobmanager, flink-taskmanager ×2
- **Batch**: spark-master, spark-worker, spark-worker-2, spark-submit
- **Query**: trino
- **Orchestration**: dagster-webserver, dagster-daemon, job-watchdog
- **Monitoring**: grafana, prometheus, loki, promtail, kafka-exporter, node-exporter, redis-exporter
- **Total**: ~18 services, ~16GB memory budget

**Note**: All 3 nodes are identical hardware (8 vCPU, 32GB RAM, 145GB SSD).
The data node is significantly underutilized (~3GB of 32GB RAM). The compute
node carries the heaviest load (Flink + Spark + Trino + monitoring).

## Key Design Decisions & Rationale

### Why Three Separate Storage Systems?
| Problem | Solution |
|---|---|
| 1000+ clients at 50ms intervals would overwhelm SQL DB | Redis hot cache for latest prices |
| Time-series data (OHLCV) optimized for range scans | InfluxDB TSDB |
| Years of historical data, petabyte scale | Iceberg + MinIO + Trino |
| Structured relationships, transactions, vector search | PostgreSQL + pgvector |

### Why Direct Redis Bypass?
- Kafka/Flink are the primary data path but add ~500ms latency
- When either fails, the producer detects via health_monitor and writes directly to Redis
- Ensures frontend always has real-time data even during pipeline outages
- Trade-off: No InfluxDB writes during bypass (historical gaps)

### Why AI Runs Inside FastAPI Container?
- Simple deployment (no separate AI service to manage)
- Shared PostgreSQL connection pool
- ai-service container is scaffolded only (0/1 replicas)
- Trade-off: AI model loading blocks FastAPI startup

## Data Flow Critical Paths

### End-to-End 1s Candle Update (8-Shard WebSocket Path)
```
Timestamp T0: Binance emits 1s candle
T0+50ms:  binance-kline-ws shard receives via WebSocket
T0+55ms:  parse_kline() → Redis writer buffer
T0+80ms:  Redis pipeline flush (ZADD + EXPIRE)
T0+120ms: FastAPI WebSocket poll reads Redis
T0+170ms: Browser receives WS push, renders candle
```
**Total**: ~170ms for a 1s candle. Bypasses Kafka/Flink entirely.
Uses 8 parallel WebSocket shards (~25 symbols/shard), writing
directly to ``candle:1s:binance:{symbol}`` sorted set.

Frontend acts as the final consumer:
- **Chart candle (lightweight-charts)**: Updated imperatively via `updateAllPriceSeries()` — no React state involvement, immediate render on WS tick
- **Right panel overview price**: Reads `_livePriceMap[symbol]` (synchronously mutated on each WS ticker message via `updateLivePrice()`), re-renders every 2s via internal interval
- **Left toolbar price**: Same `_livePriceMap` source as right panel, re-rendered every 500ms via `setLiveTick` interval. Fixed v0.28.3 (was using deferred `candles` state — lagged).

Fallback path (producer DirectRedisWriter): same latency profile.
REST poller (binance-kline-rest) serves 1m data only.

### End-to-End 1m+ Candle Update (Flink Path)
```
Timestamp T0: Binance emits candle
T0+50ms:  Producer receives via WebSocket
T0+100ms: Producer Avro-serializes → Kafka producer send()
T0+150ms: Kafka broker acks (min ISR=2)
T0+300ms: Flink TaskManager pulls from Kafka
T0+400ms: Flink keyBy → process → BATCH buffer
T0+700ms: Flink BATCH flush → Redis + InfluxDB
T0+750ms: FastAPI WebSocket poll reads Redis
T0+800ms: Browser receives WS push, renders candle
```
**Total**: ~800ms for a 1m+ candle. Bottleneck: Flink BATCH flush (300ms of 800ms).

### Ticker Page Load
```
Browser → GET /api/ticker/BTCUSDT
  → FastAPI reads Redis ticker:latest:binance:BTCUSDT → 2ms
  → Response to browser → 5ms

Browser → WS /api/stream/all?symbol=BTCUSDT
  → Every 50ms: Redis poll → push update
```

### Market Overview Load
```
Browser → GET /api/market/overview
  → Trino: SELECT * FROM crypto_lakehouse.gold.market_overview → 200ms
  → Response to browser → 50ms
```

## Current Production Status (2026-06-19)

| Component | Status | Notes |
|---|---|---|
| Frontend | ✅ | lmview.duckdns.org |
| FastAPI | ✅ | Health checks pass |
| PostgreSQL | ✅ | Pool size 10 |
| Redis Sentinel | ✅ | 1M+2R+3S, healthy |
| InfluxDB | ✅ | 90 days retention |
| Kafka | ✅ | 3 brokers, 0 LAG |
| Flink | ✅ | Job RUNNING, 5 vertices |
| Spark | ⚠️ | Workers up, job not auto-submitted |
| Trino | ✅ | Iceberg queries working |
| Grafana | ✅ | Running, 22 dashboards |
| Prometheus | ❌ | 0/1, not collecting |
| Loki | ❌ | 0/1, no centralized logs |
| AI Service | ⚠️ | Mock provider, deps install at runtime |
