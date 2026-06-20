# Architecture Overview

LMView is a real-time cryptocurrency technical-analysis platform using **Lambda Architecture** across 3 layers, deployed on 2-node Docker Swarm.

## Lambda Architecture

```
Exchange WebSockets (Binance, OKX opt-in)
  │
  ▼
┌──────────────────────────────────────────────────────┐
│ INGESTION (src/producer/main.py)                      │
│ WebSocket → Avro serialization → Kafka topics         │
│ Topics: crypto_ticker, crypto_klines, crypto_trades,  │
│         crypto_depth                                  │
│ Direct Redis bypass (health-monitored, auto-failover)  │
└────────┬─────────────────────────────────────────────┘
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

### Mode 2: Kafka/Flink Failure (Bypass)
```
Binance WS → Producer → DirectRedisWriter → Redis
                                              │
FastAPI ←──────────────────────────────────────┘
```
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

## Service Placement Strategy (2-Node Swarm)

### Core Node (8 vCPU, 32 GB) — label `role=core`
- **Stateful services**: postgres, redis-{master,replica,sentinel}×3, influxdb, minio
- **Messaging**: zookeeper, kafka-1/2/3, schema-registry
- **Serving**: fastapi-prod, nginx-prod, producer
- **Utilities**: registry, certbot-auto, duckdns-auto, minio-init
- **Total**: ~20 services, ~25GB memory budget

### Worker Node (4 vCPU, 16 GB) — label `role=worker`
- **Compute**: flink-jobmanager, flink-taskmanager×2, spark-master, spark-worker×2
- **Query**: trino
- **Monitoring**: grafana, prometheus (opt-in), loki (opt-in)
- **Orchestration**: dagster (opt-in)
- **Total**: ~10 services, ~13GB memory budget

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

### End-to-End Candle Update (<1s target)
```
Timestamp T0: Binance emits 1s candle
T0+50ms: Producer receives via WebSocket
T0+100ms: Producer Avro-serializes → Kafka producer send()
T0+150ms: Kafka broker acks (min ISR=2)
T0+300ms: Flink TaskManager pulls from Kafka
T0+400ms: Flink keyBy → process → BATCH buffer
T0+700ms: Flink BATCH flush → Redis + InfluxDB
T0+750ms: FastAPI WebSocket poll reads Redis
T0+800ms: Browser receives WS push, renders candle
```
**Total**: ~800ms for a 1s candle. Bottleneck: Flink BATCH flush (300ms of 800ms).

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
