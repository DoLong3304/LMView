# LMView — System Documentation

> **Purpose:** Complete technical reference for the LMView platform — for human understanding and AI agent context.
> **Last updated:** 2026-05-16

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture](#2-architecture)
3. [Tech Stack](#3-tech-stack)
4. [Directory Structure](#4-directory-structure)
5. [Data Flow](#5-data-flow)
6. [Storage Layer](#6-storage-layer)
7. [Processing Layer](#7-processing-layer)
8. [API Layer](#8-api-layer)
9. [Frontend](#9-frontend)
10. [Schemas & Data Formats](#10-schemas--data-formats)
11. [Orchestration](#11-orchestration)
12. [Infrastructure](#12-infrastructure)
13. [Setup & Operations](#13-setup--operations)
14. [Testing](#14-testing)
15. [Known Issues & Gotchas](#15-known-issues--gotchas)

---

## 1. Project Overview

**LMView** (Lambda View) is a real-time cryptocurrency technical analysis platform. It streams market data from exchanges, processes it through a Lambda Architecture (speed + batch layers), and serves it via a TradingView-style web interface.

**Key capabilities:**
- Real-time OHLCV candlestick charting for ~400 USDT pairs
- Multi-timeframe support: 1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w
- Order book depth, recent trades, ticker data
- Technical indicators (SMA, EMA, RSI, MFI)
- Historical data browsing with date range picker
- 12 drawing tools (trendline, fibonacci, etc.)
- Full observability stack (Prometheus, Grafana, Loki)

**Deployment target:** AWS t3a.2xlarge (8 vCPU, 32GB RAM, 100GB gp3 SSD)

---

## 2. Architecture

LMView uses **Lambda Architecture** — parallel processing paths for real-time and historical data:

```
                    ┌──────────────────────────────┐
                    │    Exchange WebSocket APIs    │
                    │  (Binance ~400 USDT pairs)   │
                    └──────────────┬───────────────┘
                                   │
                          [src/producer/main.py]
                         Avro serialize → Kafka HA
                                   │
              ┌────────────────────┼────────────────────┐
              │                    │                     │
       crypto_ticker        crypto_klines         crypto_depth
       crypto_trades               │              crypto_trades
              │                    │                     │
              │           ┌────────▼────────┐           │
              │           │  Apache Flink   │◄──────────┘
              │           │ (Speed Layer)   │
              │           │ <1s latency     │
              │           └────────┬────────┘
              │                    │
              │    ┌───────────────┼───────────────┐
              │    │               │               │
              ▼    ▼               ▼               │
         Redis Sentinel      InfluxDB 2.7         │
         (hot cache)         (warm storage)       │
         TTL: 8h-7d          retention: 90d       │
              │                    │               │
              │               [Batch Layer]        │
              │           Spark + Dagster          │
              │                    │               │
              │              Iceberg/MinIO         │
              │              (cold storage)        │
              │                    │               │
              └────────┬──────────┘               │
                       │                           │
                  [FastAPI API]                    │
                  REST + WebSocket                 │
                       │                           │
                  [Nginx Proxy]                    │
                       │                           │
                  [React 19 SPA]                   │
                  lightweight-charts               │
```

**Why Lambda?**
- **Speed layer** (Flink): Real-time with <1s latency → Redis + InfluxDB
- **Batch layer** (Spark): Accurate historical reprocessing → Iceberg (MinIO)
- **Serving layer** (FastAPI): Merges sources by priority: Redis → InfluxDB → Trino/Iceberg

---

## 3. Tech Stack

| Component | Technology | Version | Container |
|---|---|---|---|
| Message broker | Apache Kafka HA (KRaft) | 3.9.0 | kafka-1, kafka-2, kafka-3 |
| Schema registry | Apicurio | 2.6.2 | schema-registry |
| Stream processing | Apache Flink (PyFlink) | 1.18.1 (Python 3.10) | flink-jobmanager, flink-taskmanager |
| Batch processing | Apache Spark (PySpark) | 3.5 (Python 3.10) | spark-master, spark-worker |
| Hot cache | Redis Sentinel HA | latest | redis-master, redis-replica-1/2, redis-sentinel-1/2/3 |
| Time-series DB | InfluxDB | 2.7 | influxdb |
| Cold storage | Apache Iceberg + MinIO | 1.5.2 + latest | minio |
| Federated query | Trino | 442 | trino |
| Orchestration | Dagster | 1.8.10 | dagster-daemon, dagster-webserver |
| API server | FastAPI + Uvicorn | 0.115+ (Python 3.11) | fastapi |
| Producer | Python WebSocket | Python 3.11 | producer |
| Frontend | React 19 + lightweight-charts v5.2.0 | TypeScript 5.7+ / Vite 6.4 | frontend |
| CSS framework | TailwindCSS | 3.4.4 | (bundled) |
| Reverse proxy | Nginx | 1.31.0 | nginx |
| Metadata DB | PostgreSQL | 16 | postgres |
| Monitoring | Prometheus + Grafana + Loki | 2.45 / 10.2 / 2.9 | prometheus, grafana, loki, promtail, redis-exporter |

---

## 4. Directory Structure

```
lmview/
├── backend/                    # FastAPI API layer (MVC architecture)
│   ├── app.py                  # App entry point, router registration
│   ├── api/                    # Route handlers (thin controllers)
│   │   ├── health.py           # GET /api/health
│   │   ├── klines.py           # GET /api/klines (main OHLCV endpoint)
│   │   ├── historical.py       # GET /api/klines/historical (Trino)
│   │   ├── websocket.py        # WS /api/stream
│   │   ├── ticker.py           # GET /api/ticker
│   │   ├── orderbook.py        # GET /api/orderbook
│   │   ├── trades.py           # GET /api/trades
│   │   ├── symbols.py          # GET /api/symbols
│   │   ├── indicators.py       # GET /api/indicators
│   │   ├── market.py           # GET /api/market
│   │   ├── market_overview.py  # GET /api/market/overview, /heatmap
│   │   └── news.py             # GET /api/news
│   ├── core/                   # Config, constants, connections
│   │   ├── config.py           # Environment variable reader
│   │   ├── constants.py        # Shared constants (intervals, limits)
│   │   ├── database.py         # Singleton InfluxDB/Trino connections
│   │   └── redis_sentinel.py   # RedisSentinelManager (HA client)
│   ├── services/               # Business logic layer
│   │   ├── candle_service.py   # OHLCV validation, aggregation, merge
│   │   └── heatmap_service.py  # Heatmap data aggregation
│   ├── tasks/                  # Background task workers
│   │   ├── market_fetcher.py   # Continuous market data fetching
│   │   └── news_fetcher.py     # Continuous news data fetching
│   └── models/                 # Pydantic response models
│       ├── candle.py
│       └── ticker.py
├── src/                        # Data processing layer
│   ├── common/                 # Shared infrastructure
│   │   ├── config.py           # Centralized env config
│   │   ├── kafka_client.py     # Thread-safe Kafka HA producer
│   │   ├── avro_serializer.py  # Confluent wire format Avro
│   │   ├── flink_redis_sentinel.py  # Flink-specific Redis Sentinel client
│   │   └── logging.py          # Structured logging setup
│   ├── exchanges/              # Exchange abstraction layer
│   │   ├── base.py             # ExchangeClient abstract base class
│   │   ├── binance/            # Binance implementation
│   │   └── okx/                # OKX implementation
│   ├── producer/               # Kafka producer (WebSocket → Kafka)
│   │   └── main.py             # Exchange-agnostic WS orchestrator
│   ├── processing/             # Flink streaming pipeline
│   │   ├── pipeline.py         # Job entry point
│   │   └── writers/            # Individual writer modules
│   ├── lakehouse/              # Spark Structured Streaming → Iceberg
│   │   └── pipeline.py
│   ├── batch/                  # Historical data jobs
│   │   ├── backfill.py         # Multi-mode backfill (Spark/direct)
│   │   ├── aggregate.py        # 1m → 1h aggregation
│   │   └── maintenance.py      # Iceberg compaction
│   └── news/                   # News sentiment analysis
│       ├── scraper.py
│       ├── enhanced_scraper.py
│       ├── multi_source_scraper.py
│       └── sentiment_analyzer.py
├── frontend/                   # React 19 SPA (Vite + TypeScript)
│   └── src/
│       ├── App.tsx             # Main dashboard layout
│       ├── index.tsx           # Entry point
│       ├── components/         # 19 components + chart/ subdir
│       │   ├── LeftSidebar.tsx
│       │   ├── RightPanel.tsx
│       │   └── TopToolbar.tsx
│       ├── services/           # marketDataService.ts, symbolMetaService.ts
│       ├── hooks/              # useApiCall.ts, useSymbolMeta.ts
│       ├── contexts/           # AuthContext.tsx
│       ├── i18n/               # translations.ts, index.tsx
│       ├── types/              # index.ts (shared interfaces)
│       ├── data/               # fallbackSymbolMeta.ts
│       ├── pages/              # Page-level components
│       │   ├── MarketOverviewPage.tsx
│       │   └── NewsPageRedesigned.tsx
│       └── utils/              # storageHelpers.ts, errors.ts
├── orchestration/              # Dagster workflow definitions
│   ├── assets.py               # Asset + schedule definitions
│   ├── medallion_assets.py     # Bronze/Silver/Gold layer assets
│   └── workspace.yaml
├── schemas/                    # Avro schemas (5 files)
│   ├── ticker.avsc, kline.avsc, trade.avsc, depth.avsc, news.avsc
├── config/                     # Service configurations
│   ├── prometheus.yml, loki-config.yml, promtail-config.yml
│   ├── spark-defaults.conf
│   └── grafana/                # Dashboard + datasource provisioning
├── docker/                     # Dockerfiles (10 subdirs)
│   ├── backfill/, dagster/, fastapi/, flink/, nginx/
│   ├── postgres/, producer/, redis/, spark/, trino/
├── scripts/                    # Shell scripts
│   ├── auto_submit_jobs.sh     # Flink + Spark job submission
│   ├── create_kafka_topics.sh  # Topic initialization
│   ├── certbot_auto.sh         # SSL certificate automation
│   ├── setup_influx_retention.sh/.ps1  # InfluxDB retention setup
│   └── duckdns_auto.sh, nginx_auto_reload.sh
├── tests/                      # pytest test suite (161 tests)
│   ├── conftest.py
│   ├── unit/, integration/, e2e/, security/, performance/
├── docs/                       # Documentation
│   ├── SYSTEM.md               # This file
│   ├── CHANGELOG.md            # Change history
│   └── AGENTS.md               # AI agent coding instructions
├── docker-compose.yml          # All services (profiles: dev/prod/monitoring/logging)
├── Makefile                    # Convenience targets
├── pyproject.toml              # pytest config
├── .env.example                # Environment variable template
└── README.md                   # User-facing overview
```

---

## 5. Data Flow

### 5.1 Real-time Path (<1s latency)

```
Binance WS (!miniTicker@arr, @kline_1s, @aggTrade, @depth20@100ms)
  → src/producer/main.py
  → Avro serialize (Confluent wire format: 0x00 + schema_id + binary)
  → Kafka HA topics (3 brokers, replication factor 3)
  → Flink consumers (5 parallel pipelines)
```

**Pipeline 1 — Ticker:** `crypto_ticker` → KeyDBWriter (buffer 100, flush 0.5s) → `ticker:latest:{symbol}` + InfluxDBWriter → `market_ticks`

**Pipeline 2 — Raw 1s candles:** `crypto_klines` → KeyDBKlineWriter → `candle:1s:{symbol}` (ZREMRANGEBYSCORE + ZADD, TTL 8h) + InfluxDBKlineWriter → `candles` measurement

**Pipeline 3 — 1s→1m aggregation:** `crypto_klines` → KlineWindowAggregator (KeyedProcessFunction):
- MapState stores 1s candles per minute window
- On minute boundary: aggregate 60 candles → emit 1m candle
- Safety timer at 65s: emit partial if stream silent
- Gap-fill: forward-fill close price for missing seconds
- Output → KeyDBKlineWriter (`candle:1m`, TTL 7d) + InfluxDBKlineWriter + IndicatorWriter (SMA/EMA)

**Pipeline 4 — Depth:** `crypto_depth` → DepthWriter → `orderbook:{symbol}` (HSET)

**Pipeline 5 — Trades:** `crypto_trades` → TradeWriter → `trades:{symbol}` (LPUSH + LTRIM 100)

### 5.2 Batch Path

| Job | Schedule | Input | Output |
|---|---|---|---|
| `backfill.py --mode populate` | Manual | Binance REST 1m API (90d) | InfluxDB |
| `backfill.py --mode influx` | Manual | Binance REST (gap fill) | InfluxDB |
| `backfill.py --mode iceberg` | Manual | Binance REST 1h API | Iceberg |
| `aggregate.py` | Daily 04:00 UTC | InfluxDB 1m | InfluxDB 1h + Iceberg |
| `maintenance.py` | Weekly Sun 03:00 | Iceberg | Compacted Iceberg |

### 5.3 API Serving Path

**GET /api/klines (real-time):**
1. Check Redis cache `klines_cache:{symbol}:{interval}:{limit}` (100ms TTL)
2. Query Redis `candle:1m:{symbol}` via ZRANGEBYSCORE
3. If insufficient: fallback to InfluxDB (90d range)
4. Client-side aggregate: 1m → target interval (5m/15m/1h/4h/1d/1w)
5. Build in-progress candle from `candle:1s` sub-candles + ticker enrichment
6. Cache 100ms → return JSON

**GET /api/klines (scroll-left with endTime):**
1. Skip cache and Redis (only 7d data)
2. Calculate absolute range from endTime
3. Query InfluxDB with `range(start: RFC3339, stop: RFC3339)`
4. Aggregate → return

**WS /api/stream:**
- Loop every 0.5s
- Build candle from sub-candles, enrich with ticker if fresher
- Push on diff (avoid spam)

---

## 6. Storage Layer

### 6.1 Redis Sentinel HA (Hot Cache)

| Key Pattern | Type | TTL | Content |
|---|---|---|---|
| `ticker:latest:{symbol}` | Hash | None | price, bid, ask, volume, change24h, event_time |
| `candle:1s:{symbol}` | Sorted Set | 8h | score=kline_start_ms, member=candle JSON |
| `candle:1m:{symbol}` | Sorted Set | 7d | score=kline_start_ms, member=candle JSON |
| `indicator:latest:{symbol}` | Hash | None | sma20, sma50, ema12, ema26 |
| `orderbook:{symbol}` | Hash | None | bids JSON, asks JSON, ts |
| `trades:{symbol}` | List | None | max 100 trade JSONs |
| `klines_cache:*` | String | 100ms | Cached API response |

Candle JSON format: `{"t": ms, "o": open, "h": high, "l": low, "c": close, "v": volume, "qv": quote_vol, "n": trades, "x": is_closed}`

Config: `maxmemory 2560mb`, `maxmemory-policy allkeys-lru`, Sentinel cluster (1 master + 2 replicas + 3 sentinels)

### 6.2 InfluxDB 2.7 (Warm Storage)

- **Org:** `vi`, **Bucket:** `crypto`, **Retention:** 90 days (managed by Spark aggregate job)
- **Measurements:** `candles` (tags: symbol, exchange, interval; fields: OHLCV), `market_ticks`, `indicators`
- **Query language:** Flux

### 6.3 Iceberg + MinIO (Cold Storage)

- **Tables:** `historical_hourly`, `coin_klines_hourly` — partitioned by symbol + year + month
- **Medallion Architecture (News):** `bronze.news`, `silver.news_enriched`, `gold.news_sentiment_daily`
- **Gold Metrics Tables:** `gold.market_dominance`, `gold.volatility_ranking`, `gold.movers_ranking`, `gold.momentum_indicators`
- **Format:** Parquet on MinIO (`s3a://cryptoprice/`)
- **Query:** Trino SQL with predicate pushdown
- **Catalog:** PostgreSQL (`iceberg_catalog` database)

### 6.4 Kafka HA (Message Broker)

- 3 KRaft brokers, 3 partitions per topic, replication factor 3, retention 48h, LZ4 compression
- **Topics:** `crypto_ticker`, `crypto_klines`, `crypto_trades`, `crypto_depth`, `crypto_news_sentiment`

---

## 7. Processing Layer

### 7.1 Flink (Speed Layer)

- **Containers:** jobmanager (2.5GB cap) + taskmanager (7GB cap, 6GB reserved)
- **Checkpointing:** HashMapStateBackend, 120s interval, EXACTLY_ONCE, unaligned
- **Web UI:** http://localhost:8081
- **Job file:** `src/processing/pipeline.py`
- **Writers:** Split into `src/processing/writers/` (one file per writer)

### 7.2 Spark (Batch Layer)

- **Containers:** spark-master + spark-worker (4GB RAM, 4 vCores)
- **Only runs** when called by Dagster (no idle resources)
- **Jobs:** backfill.py, aggregate.py, maintenance.py, calculate_all_metrics.py, calculate_indicators.py

---

## 8. API Layer

### 8.1 Endpoints

| Method | Endpoint | Source | Description |
|---|---|---|---|
| GET | `/api/klines` | Redis → InfluxDB | OHLCV candles with scroll-left support |
| WS | `/api/stream` | Redis (real-time) | Live candle stream (0.5s interval) |
| GET | `/api/ticker/{symbol}` | Redis | Price, bid, ask, 24h change |
| GET | `/api/ticker` | Redis scan | All tickers |
| GET | `/api/orderbook/{symbol}` | Redis | Top-20 bid/ask depth |
| GET | `/api/trades/{symbol}` | Redis | 100 most recent trades |
| GET | `/api/symbols` | Redis scan | All available symbols |
| GET | `/api/indicators/{symbol}` | Redis | SMA20/50, EMA12/26 |
| GET | `/api/klines/historical` | Trino → Iceberg | Long-range date queries |
| GET | `/api/health` | All backends | Service health check |
| GET | `/api/market` | Redis | Market overview data |
| GET | `/api/market/overview` | Trino | Market overview aggregations |
| GET | `/api/market/heatmap` | Trino | Market heatmap data |
| GET | `/api/news` | Redis | News sentiment data |

### 8.2 Architecture

MVC pattern in `backend/`:
- `api/` — Thin route handlers. No business logic.
- `services/` — Business logic (candle_service.py: validate, aggregate, merge, dedup)
- `models/` — Pydantic response models
- `core/` — Config, constants, database singletons, Redis Sentinel manager

---

## 9. Frontend

### 9.1 Stack

React 19 + TypeScript 5.7+ + Vite 6.4 + TailwindCSS 3.4 + lightweight-charts v5.2.0

### 9.2 Component Tree

```
App.tsx (TradingDashboard)
├── ErrorBoundary.tsx
├── ToastProvider.tsx
├── I18nProvider
├── AuthContext.Provider
├── Header.tsx + LanguageSwitcher.tsx
├── DrawingToolbar.tsx + ToolSettingsPopup.tsx
├── CandlestickChart.tsx (~1020 lines — CORE)
│   ├── MarketSelector.tsx
│   ├── DateRangePicker.tsx
│   ├── chart/IndicatorPanel.tsx, OHLCVBar.tsx, OscillatorPane.tsx
│   ├── ChartOverlay.tsx (SVG drawings)
│   ├── OrderBook.tsx
│   └── RecentTrades.tsx
├── Watchlist.tsx
├── OverviewChart.tsx
├── SystemHealthCard.tsx
└── AuthModal.tsx
```

### 9.3 Key Patterns

- **API layer:** All calls through `marketDataService.ts`. Never direct `fetch()` in components.
- **3 update channels:** Initial load (`setData`), WebSocket (`update`), Poll incremental (1s interval, skip live bar for 1m+)
- **Scroll-left:** On `visibleLogicalRangeChanged`, if `range.from < 20`, fetch 500 older candles via `endTime` param
- **Time convention:** lightweight-charts = seconds, API = milliseconds. Convert at service layer.
- **i18n:** ~130 keys (en + vi) via `useI18n()` hook

---

## 10. Schemas & Data Formats

### Avro Schemas (in `schemas/`)

**crypto_ticker** — `ticker.avsc`: symbol, event_time, close, bid, ask, h24_open/high/low/volume/quote_volume/price_change/price_change_pct/trade_count

**crypto_klines** — `kline.avsc`: symbol, interval, kline_start, kline_close, OHLCV, quote_volume, trade_count, is_closed, event_time

**crypto_trades** — `trade.avsc`: symbol, event_time, agg_trade_id, price, quantity, trade_time, is_buyer_maker

**crypto_depth** — `depth.avsc`: symbol, event_time, last_update_id, bids[][], asks[][]

**crypto_news_sentiment** — `news.avsc`: news sentiment data

Wire format: `0x00` magic byte + 4-byte big-endian schema_id + Avro binary payload

---

## 11. Orchestration

**Dagster** — 2 containers (webserver + daemon), state in PostgreSQL

| Asset | Description | Schedule |
|---|---|---|
| `backfill_historical` | Binance → Iceberg + InfluxDB gap fill | Manual |
| `aggregate_candles` | 1m→1h aggregation + retention cleanup | Daily 04:00 UTC |
| `iceberg_table_maintenance` | Compact + expire snapshots | Weekly Sun 03:00 UTC |

**Web UI:** http://localhost:3000

---

## 12. Infrastructure

### 12.1 Docker Profiles

| Profile | Services | RAM |
|---|---|---|
| `dev` | 21 core services | ~17GB |
| `monitoring` | + Prometheus, Grafana, exporters | ~18GB |
| `logging` | + Loki, Promtail | ~18.8GB |

### 12.2 Port Reference

| Service | Port | URL |
|---|---|---|
| Frontend (Nginx) | 80, 443 | http://localhost |
| FastAPI docs | 8080 | http://localhost:8080/docs |
| Grafana | via nginx | http://localhost/grafana/ |
| Prometheus | via nginx | http://localhost/prometheus/ |
| Loki | via nginx | http://localhost/loki/ |
| Flink UI | 8081 | http://localhost:8081 |
| Spark UI | 8082 | http://localhost:8082 |
| Trino UI | 8083 | http://localhost:8083 |
| InfluxDB | 8086 | http://localhost:8086 |
| Dagster | 3000 | http://localhost:3000 |
| MinIO Console | 9001 | http://localhost:9001 |

### 12.3 Monitoring

- **7 Grafana dashboards** (3 metrics + 4 logs), 47+ panels
- **Metrics integration**: Spark metrics via JMX, Redis Exporter (`redis-exporter`)
- **8 alerting rules** (Flink restart, Kafka down, API error rate, memory/CPU thresholds)
- **Loki** — centralized logs from all containers, 7-day retention
- **Nginx routing** — Grafana at `/grafana/`, Prometheus at `/prometheus/`, Loki at `/loki/`
- **Basic Auth** — Prometheus and Loki protected via htpasswd (MONITORING_USER/MONITORING_PASSWORD)

---

## 13. Setup & Operations

### 13.1 Prerequisites

- Docker Engine >= 24.x or Docker Desktop >= 4.x
- RAM: 32GB recommended (24GB minimum)
- Disk: 100GB+ free
- CPU: 8 cores recommended

### 13.2 First-Time Setup

```bash
git clone https://github.com/StupidDuck64/Lambda-Architecture-for-TradingView-Style-Platform.git
cd Lambda-Architecture-for-TradingView-Style-Platform
cp .env.example .env
# Edit .env: set INFLUX_TOKEN, passwords, API keys

# Start core services
make core                # or: docker compose --profile dev up -d

# Wait for healthy (~3-5 min)
docker compose ps

# Backfill historical data (30-60 min for 400 symbols × 90 days)
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode populate --days 90

# Submit Flink job
make submit-jobs         # or: bash scripts/auto_submit_jobs.sh

# Verify: http://localhost → chart should show real-time data
```

### 13.3 Makefile Commands

| Command | Description |
|---|---|
| `make core` | Start core services (17GB) |
| `make monitoring` | Core + monitoring (18GB) |
| `make full` | All services (18.8GB) |
| `make stop-all` | Stop everything |
| `make submit-jobs` | Submit Flink + Spark jobs |
| `make dev` | Start dev mode |
| `make prod` | Start production mode |
| `make test` | Run unit + integration tests |
| `make test-all` | Run all tests |
| `make test-cov` | Tests with coverage |
| `make status` | Container status + RAM usage |
| `make clean` | Remove all containers + volumes (DANGEROUS) |

### 13.4 Rebuild After Code Changes

| Changed | Command |
|---|---|
| `backend/` | `docker compose up -d --build fastapi` |
| `frontend/` | `docker compose up -d --build nginx` |
| `src/` (Flink) | Cancel job → re-submit via `make submit-jobs` |
| `src/` (Spark) | Re-submit via `spark-submit` |
| `docker/` | `docker compose up -d --build <service>` |

---

## 14. Testing

**Framework:** pytest + pytest-asyncio

**Structure:**
- `tests/unit/` — 80 tests (constants, mappers, models, services)
- `tests/integration/` — 39 tests (all API endpoints)
- `tests/security/` — 17 tests (injection, XSS, traversal)
- `tests/performance/` — 9 benchmarks (aggregation, merging)
- `tests/e2e/` — 6 tests (routes, OpenAPI schema)
- **Total: 161 tests**

**Commands:**
```bash
PYTHONPATH=. python -m pytest tests/unit/ -v          # Unit only
PYTHONPATH=. python -m pytest tests/ -v               # All tests
PYTHONPATH=. python -m pytest tests/ --cov=backend    # With coverage
make test                                              # Unit + integration
make test-all                                          # Everything
```

---

## 15. Known Issues & Gotchas

1. **Time units:** lightweight-charts = seconds, backend = milliseconds. Always convert.
2. **Timeframe casing:** Frontend `1H`/`4H`/`1D`/`1W` → `.toLowerCase()` before API calls.
3. **Redis sorted set dedup:** Must `ZREMRANGEBYSCORE` before `ZADD` (same score + different member = duplicate).
4. **Ticker staleness:** `!ticker@arr` has 14-30s delay. Only enrich candle if ticker is fresher than last sub-candle.
5. **WS vs Poll coordination:** WS authoritative for live bar (1m+). Poll skips last candle to prevent flicker.
6. **InfluxDB scroll-left:** Must use absolute `range(start: RFC3339, stop: RFC3339)` for historical queries.
7. **Flink safety timer:** Must cancel old timer before registering new one in KlineWindowAggregator.
8. **Frontend chart updates:** `.update()` for single bar, `.setData()` only for bulk operations.
9. **Producer WS limit:** Max 200 symbols per WebSocket connection (Binance 502).
10. **Python compatibility:** Flink 1.18 needs Python 3.10 (`distutils`). Producer/FastAPI = 3.11. Do NOT use 3.12+.
11. **PyFlink writers:** Still named `keydb_*` prefix but use Redis Sentinel under the hood.
12. **Pydantic compatibility:** Use `Optional[X]` not `X | None` for Pydantic models (Python 3.9 compat).

---

> **Document version:** 3.1
> **Last updated:** 2026-05-19
> **Maintained by:** AI agents + human contributors (see `docs/CHANGELOG.md`)
