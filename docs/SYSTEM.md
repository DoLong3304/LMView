# LMView System Documentation

> Complete project map for humans and coding agents.
> Last reviewed from code: 2026-05-21.

---

## 1. Project Snapshot

**LMView** is a real-time cryptocurrency technical-analysis platform. It combines:

- A speed layer for live market data.
- A batch/lakehouse layer for historical data and analytics.
- A serving layer for REST/WebSocket APIs.
- A React TradingView-style frontend.

Current project version from `docs/CHANGELOG.md`: **0.12.3**.

Current repo state at this audit:

- Source branch: `main`.
- Runtime orchestration: one `docker-compose.yml` with profiles.
- Development profile service count: **27** services.
- Full dev + monitoring + logging count: **34** services.
- Production + monitoring + logging count: **36** services.
- Backend tests in source: **193 pytest test functions** across **24 Python test files**.
- Frontend hook tests in source: **35 Jest-style specs** across **2 files**.
- Existing uncommitted user change observed: `frontend/tsconfig.json`.

This document describes the code as it exists now, including caveats where implementation and intended architecture differ.

---

## 2. Architecture Overview

LMView follows Lambda Architecture:

```text
Exchange WebSockets / REST
  -> src/producer/main.py
  -> Avro serialization + Kafka topics
  -> Speed layer: Flink -> Redis Sentinel + InfluxDB
  -> Batch layer: Spark -> Iceberg tables on MinIO, queried by Trino
  -> Serving layer: FastAPI REST + WebSocket
  -> Nginx reverse proxy
  -> React 19 frontend
```

Main runtime paths:

| Path | Purpose | Main files |
|---|---|---|
| Ingestion | Stream exchange ticker, kline, trade, depth data to Kafka | `src/producer/main.py`, `src/exchanges/*` |
| Speed processing | Hot candles/tickers/order books/indicators | `src/processing/pipeline.py`, `src/processing/writers/*` |
| Warm storage | Recent analytical history | InfluxDB via Flink writers and batch jobs |
| Cold storage | Long-term historical/lakehouse data | `src/lakehouse/pipeline.py`, `src/batch/*`, MinIO, Iceberg, Trino |
| Serving | API and WebSocket data access | `backend/app.py`, `backend/api/*`, `backend/services/*` |
| UI | Trading dashboard, market overview, news, drawings, replay | `frontend/src/*` |
| Operations | Compose, Nginx, monitoring, logging | `docker-compose.yml`, `docker/*`, `config/*` |

---

## 3. Repository Map

```text
backend/
  app.py                    FastAPI app, lifespan tasks, router registration
  api/                      Thin route handlers
  core/                     Config, constants, DB and Redis Sentinel clients
  models/                   Pydantic response models
  services/                 Business logic and in-memory market/news caches
  tasks/                    Background market/news fetchers

src/
  common/                   Shared config, Kafka client, Avro serializer, logging
  exchanges/                Exchange abstraction plus Binance and OKX clients
  producer/                 Exchange -> Kafka WebSocket producer
  processing/               Flink speed-layer pipeline
  processing/writers/       Redis, InfluxDB, indicator, and kline aggregation writers
  lakehouse/                Spark structured streaming and Bronze/Silver/Gold helpers
  batch/                    Backfill, retention, metrics, unified medallion jobs
  news/                     News scraping and sentiment analysis

frontend/
  src/App.tsx               Main dashboard shell
  src/components/           Chart, toolbars, panels, market/news UI
  src/services/             API, market overview, symbol metadata, drawing storage
  src/hooks/                API, symbol metadata, replay, zoom, keyboard shortcuts
  src/i18n/                 English/Vietnamese translation system
  src/mock/                 Mock market/news data generator
  src/types/                Shared TypeScript types

orchestration/
  assets.py                 Dagster assets and schedules
  workspace.yaml            Dagster code location

schemas/                    Avro contracts for Kafka payloads
docker/                     Dockerfiles and service configs
config/                     Prometheus, Loki, Promtail, Spark, JMX, Grafana
scripts/                    Job submission, Kafka topic creation, certbot/DuckDNS helpers
tests/                      Pytest unit/integration/e2e/security/performance suites
docs/                       System docs and changelog
```

---

## 4. Runtime Services

`docker-compose.yml` is the single source of truth.

Profiles:

| Profile | Role | Service count from compose config |
|---|---|---:|
| `dev` | Core local stack with hot reload/local CORS | 27 |
| `monitoring` | Prometheus, Grafana, exporters | +5 |
| `logging` | Loki, Promtail | +2 |
| `prod` | Production FastAPI/Nginx, SSL automation, DuckDNS | 36 with monitoring+logging |
| `dont-start` | Compose extension templates only | internal |

Core service groups:

| Group | Services |
|---|---|
| Kafka | `kafka-1`, `kafka-2`, `kafka-3`, `zookeeper`, `schema-registry` |
| Storage | `redis-master`, `redis-replica-1`, `redis-replica-2`, three Sentinels, `influxdb`, `minio`, `postgres`, `trino` |
| Processing | `producer`, `flink-jobmanager`, `flink-taskmanager`, `spark-master`, `spark-worker`, `auto-submit-jobs`, `influx-backfill` |
| API/UI | `fastapi-dev` or `fastapi-prod`, `nginx-dev` or `nginx-prod` |
| Orchestration | `dagster-webserver`, `dagster-daemon` |
| Monitoring/logging | `prometheus`, `grafana`, `kafka-exporter`, `redis-exporter`, `node-exporter`, `loki`, `promtail` |
| Production helpers | `certbot-auto`, `duckdns-auto` |

Important ports:

| Service | Host port | Notes |
|---|---:|---|
| Nginx frontend/proxy | 80, 443 | HTTP redirects to HTTPS; dev uses self-signed cert if no real cert |
| FastAPI | 8080 | `/docs`, `/api/health` |
| Flink UI | 8081 | JobManager UI |
| Spark master UI | 8082 | Host maps Spark master UI |
| Trino UI | 8083 | Query engine |
| InfluxDB | 8086 | Warm time-series store |
| Dagster | 3000 | Orchestration UI |
| Grafana direct | 3001 | Also proxied under `/grafana/` |
| Prometheus direct | 9090 | Also proxied under `/prometheus/` |
| MinIO API/console | 9000/9001 | Object storage |
| Loki direct | 3100 | Also proxied under `/loki/` |

---

## 5. Ingestion Layer

### 5.1 Exchange Abstraction

Exchange clients implement `src/exchanges/base.py`.

Current clients:

| Exchange | Files | State |
|---|---|---|
| Binance | `src/exchanges/binance/*` | Primary path. REST and combined-stream URL builders fit current producer logic. |
| OKX | `src/exchanges/okx/*` | Present and started by producer, but should be treated as experimental until OKX WebSocket subscription handling is validated. OKX uses subscription frames, while current generic producer mostly assumes Binance-style URL streams. |

Producer entry point: `src/producer/main.py`.

Default producer tuning from `src/common/config.py`:

| Setting | Default |
|---|---:|
| `MAX_SYMBOLS` | 200 per exchange client |
| `SYMBOLS_PER_CONNECTION` | 25 |
| `SYMBOLS_PER_DEPTH_CONN` | 15 |
| `KLINE_INTERVAL` | `1m` |
| `DEPTH_LEVEL` | `20` |
| `DEPTH_UPDATE_MS` | `100` |
| `TICKER_HEARTBEAT_SEC` | 5 seconds |

Producer streams:

| Stream | Kafka topic | Schema |
|---|---|---|
| All ticker / mini ticker | `crypto_ticker` | `schemas/ticker.avsc` |
| Aggregate trades | `crypto_trades` | `schemas/trade.avsc` |
| Klines | `crypto_klines` | `schemas/kline.avsc` |
| Depth snapshots | `crypto_depth` | `schemas/depth.avsc` |

The producer registers Avro schemas through Apicurio's Confluent-compatible endpoint:

```text
http://schema-registry:8080/apis/ccompat/v7
```

Wire format:

```text
0x00 magic byte + 4-byte schema id + Avro binary payload
```

All market Avro schemas currently include an `exchange` field with default `binance`.

---

## 6. Kafka Layer

Kafka uses three brokers with KRaft-style images plus a Zookeeper service still present in compose.

Topics used by code:

| Topic | Produced by | Consumed by |
|---|---|---|
| `crypto_ticker` | Producer | Flink speed layer, Spark lakehouse |
| `crypto_klines` | Producer | Flink speed layer, Spark lakehouse |
| `crypto_trades` | Producer | Spark lakehouse |
| `crypto_depth` | Producer | Flink speed layer |
| `crypto_news_sentiment` | Dagster/news path | News/lakehouse path, partially wired |
| `reference_prices` | Price-change stream | `src/processing/price_change_stream.py` |

Topic creation helper: `scripts/create_kafka_topics.sh`.

---

## 7. Speed Layer: Flink + Redis + InfluxDB

Main job: `src/processing/pipeline.py`.

Flink config:

- Image: `flink:1.18.1-java11` with `apache-flink==1.18.1`.
- Parallelism default: `FLINK_PARALLELISM=12`.
- State backend: `HashMapStateBackend`.
- Checkpoint interval: 120 seconds.
- Checkpoint mode: `EXACTLY_ONCE`.
- Unaligned checkpoints enabled.
- Checkpoint path: `file:///tmp/flink-checkpoints`.

Pipeline branches:

| Branch | Input | Output |
|---|---|---|
| Ticker | `crypto_ticker` | Redis latest/history, InfluxDB `market_ticks` |
| Raw kline | `crypto_klines` | Redis `candle:1s:*`, InfluxDB closed `1m` candles only |
| Kline aggregation | `crypto_klines` 1s rows | Flink state aggregation to 1m, Redis, InfluxDB, indicators |
| Indicators | Closed 1m candles | Redis `indicator:latest:*`, InfluxDB `indicators` |
| Depth | `crypto_depth` | Redis order book hashes |

Current speed-layer gap:

- `crypto_trades` is produced and written to Iceberg by Spark, but no current Flink hot-cache trade writer exists.
- `/api/trades/{symbol}` currently derives ticker-level price ticks, not true exchange trades.

### 7.1 Kline Aggregation

`src/processing/writers/kline_aggregator.py` performs in-flight `1s -> 1m` aggregation.

Behavior:

- Stores 1s candles in keyed Flink `MapState`.
- Deduplicates by `kline_start`.
- Emits previous minute when a new minute appears.
- Has a 65-second processing-time safety timer.
- Forward-fills missing seconds using last close.
- Emits closed 1m candles with OHLCV and trade count.

Current caveat:

- Aggregator is keyed by `symbol` only and emitted records do not preserve `exchange`. For multi-exchange candle correctness, future work should key by `(exchange, symbol)` and carry `exchange` through all downstream sinks.

### 7.2 Redis Sentinel Hot Cache

Redis HA layout:

- `redis-master`
- `redis-replica-1`
- `redis-replica-2`
- `redis-sentinel-1`
- `redis-sentinel-2`
- `redis-sentinel-3`

Main client code:

- Backend: `backend/core/redis_sentinel.py`
- Flink: `src/common/flink_redis_sentinel.py`

Current writer key patterns:

| Key | Type | Writer | Notes |
|---|---|---|---|
| `ticker:latest:{exchange}:{symbol}` | hash | `keydb_ticker.py` | Latest price, bid/ask, volume, change, event time |
| `ticker:history:{exchange}:{symbol}` | sorted set | `keydb_ticker.py` | Ticker-level history, 24h TTL |
| `candle:1s:{exchange}:{symbol}` | sorted set | `keydb_kline.py` | 1s candles, TTL from writer config |
| `candle:1m:{exchange}:{symbol}` | sorted set | `keydb_kline.py` | 1m candles, TTL from writer config |
| `candle:latest:{exchange}:{symbol}` | hash | `keydb_kline.py` | Latest 1m+ candle snapshot |
| `indicator:latest:{symbol}` | hash | `indicators.py` | SMA20, SMA50, EMA12, EMA26 |
| `orderbook:{exchange}:{symbol}` | hash | `keydb_depth.py` | Bids/asks JSON, TTL 300s |
| `klines_cache:{exchange}:{symbol}:{interval}:{limit}` | string | `backend/api/klines.py` | API cache, 200ms for 1s, 1500ms for other intervals |

Important mismatch to fix:

- `backend/api/orderbook.py` reads `orderbook:{symbol}` but Flink writes `orderbook:{exchange}:{symbol}`.
- `backend/api/trades.py` reads `ticker:history:{symbol}` but Flink writes `ticker:history:{exchange}:{symbol}`.

Until those API paths are aligned, order book and recent trades may fall back, return synthetic data, or 404 even when exchange-qualified data exists.

### 7.3 InfluxDB Warm Storage

InfluxDB 2.7 stores recent analytical data.

Default config:

| Setting | Default |
|---|---|
| URL | `http://influxdb:8086` |
| Org | `vi` |
| Bucket | `crypto` |
| Retention constant | `INFLUX_1M_RETENTION_DAYS=90` |

Measurements used by code:

| Measurement | Writer | Notes |
|---|---|---|
| `market_ticks` | `influxdb_ticker.py`, backfill path | Ticker samples |
| `candles` | `influxdb_kline.py`, backfill path | Closed 1m candles and historical OHLCV |
| `indicators` | `indicators.py` | SMA/EMA metrics |

Flux historical scroll queries must use absolute RFC3339 ranges for `endTime` mode. Relative ranges can break scroll-left semantics.

---

## 8. Batch and Lakehouse Layer

### 8.1 Spark Structured Streaming

Main job: `src/lakehouse/pipeline.py`.

Purpose:

- Read Kafka topics.
- Strip Confluent Avro wire header.
- Decode with `from_avro`.
- Write append streams to Iceberg tables.

Tables created in `iceberg_catalog.crypto_lakehouse`:

| Table | Source topic | Checkpoint |
|---|---|---|
| `coin_ticker` | `crypto_ticker` | `s3a://cryptoprice/checkpoints/crypto_ticker_v1` |
| `coin_trades` | `crypto_trades` | `s3a://cryptoprice/checkpoints/crypto_trades_v1` |
| `coin_klines` | `crypto_klines` | `s3a://cryptoprice/checkpoints/crypto_klines_v1` |

Current caveat:

- The Avro schemas contain `exchange`, but current Spark table DDLs in `src/lakehouse/pipeline.py` do not include `exchange`. Multi-exchange lakehouse correctness needs schema/table alignment before relying on exchange-level historical analytics.

### 8.2 Batch Jobs

| File | Role |
|---|---|
| `src/batch/backfill.py` | Unified historical import and gap fill for InfluxDB/Iceberg |
| `src/batch/aggregate.py` | 1m retention maintenance for InfluxDB/Iceberg |
| `src/batch/maintenance.py` | Iceberg compaction, manifest optimization, orphan cleanup |
| `src/batch/calculate_all_metrics.py` | Gold metrics orchestration |
| `src/batch/calculate_indicators.py` | Momentum indicators |
| `src/batch/bronze_to_silver.py`, `silver_to_gold.py` | Older medallion jobs |
| `src/batch/unified/*` | Consolidated medallion jobs for ticker/kline/news/indicators |

### 8.3 Medallion Tables

Bronze/Silver/Gold modules exist under `src/lakehouse/`.

Examples:

| Layer | Examples |
|---|---|
| Bronze | Raw ticker/kline/news writers |
| Silver | `ticker_unified`, `kline_multi_timeframe`, `news_enriched` |
| Gold | `market_overview`, `symbol_stats_daily`, `sector_performance`, `market_dominance`, `volatility_ranking`, `movers_ranking`, `momentum_indicators`, `news_sentiment_daily` |

Gold table outputs back the market overview, heatmap, ranking, news sentiment, and future AI features.

### 8.4 Dagster

Dagster files:

- `orchestration/assets.py`
- `orchestration/workspace.yaml`

Declared schedules:

| Schedule | Cron | Role |
|---|---|---|
| `silver_transformation_schedule` | `*/5 * * * *` | Ticker unification and 5m/15m/1h kline aggregation |
| `gold_aggregation_schedule` | `*/5 * * * *` | Market overview/statistics/sector metrics |
| `daily_aggregation_schedule` | `0 0 * * *` | 4h/1d/1w candle aggregation |
| `news_sentiment_schedule` | `*/5 * * * *` | News scraping and sentiment |
| `gold_advanced_schedule` | `*/5 * * * *` | Dominance, volatility, movers, momentum indicators |

Current caveat:

- `assets.py` declares assets and schedules but does not currently expose a `Definitions` object. Validate Dagster code-location loading before relying on all schedules in production.

---

## 9. Serving Layer: FastAPI

FastAPI entry point: `backend/app.py`.

Lifecycle:

- Starts `news_fetcher` and `market_fetcher` on startup.
- Stops both fetchers and closes database clients on shutdown.
- Adds CORS from `backend/core/config.py`.
- Optionally exposes Prometheus metrics if `prometheus-fastapi-instrumentator` is installed.

Router inclusion order matters:

```text
health, ticker, klines, historical, orderbook, trades, symbols,
indicators, websocket, market_overview, market, news
```

`market_overview` is registered before legacy `market`, so overlapping routes such as `/api/market/overview` resolve to `backend/api/market_overview.py`.

### 9.1 API Endpoints

| Method | Path | Main source | Notes |
|---|---|---|---|
| GET | `/api/health` | Redis, InfluxDB, Trino | Reports dependency status and latency |
| GET | `/api/klines` | Redis -> InfluxDB -> Trino | Live/recent candles, `endTime` scroll-left mode |
| GET | `/api/klines/historical` | InfluxDB recent + Trino old | Range query, max 1 year, derives intervals from 1m |
| WS | `/api/stream/all` | Redis | Single WebSocket that sends all timeframes |
| GET | `/api/ticker/{symbol}` | Redis | Aggregates Binance/OKX mid-price unless `exchange` query is set |
| GET | `/api/ticker` | Redis scan | All tickers, optional exchange filter |
| GET | `/api/orderbook/{symbol}` | Redis or synthetic fallback | Needs key alignment for real exchange-qualified book data |
| GET | `/api/trades/{symbol}` | Redis ticker history | Ticker-level price ticks, not true trade topic data |
| GET | `/api/symbols` | Redis scan | Supports old and exchange-qualified ticker keys |
| GET | `/api/indicators/{symbol}` | Redis | SMA20, SMA50, EMA12, EMA26 |
| GET | `/api/market/overview` | Placeholder object | Currently returns zero/default overview fields |
| GET | `/api/market/heatmap` | Trino gold tables | Heatmap data |
| GET | `/api/market/rankings/{category}` | Trino gold tables | `gainers`, `losers`, `volume`, `volatile` |
| GET | `/api/market/metrics` | In-memory cache | Legacy market cache |
| GET | `/api/market/gainers` | In-memory cache | Legacy market cache |
| GET | `/api/market/losers` | In-memory cache | Legacy market cache |
| GET | `/api/market/symbol/{symbol}` | In-memory cache | Legacy market cache |
| GET | `/api/news/latest` | In-memory news cache | Optional source/symbol/hour filters |
| GET | `/api/news/sources` | Static service data | News source list |
| GET | `/api/news/trending` | In-memory news cache | Trending articles and symbols |
| GET | `/api/news/sentiment/{symbol}` | In-memory news cache | Sentiment by symbol |
| GET | `/api/news/search` | In-memory news cache | Search by query |

### 9.2 Candle Serving Logic

`backend/api/klines.py` and `backend/services/candle_service.py` are the core candle serving path.

Live `/api/klines`:

1. Normalize symbol and interval.
2. Use cache key `klines_cache:{exchange}:{symbol}:{interval}:{limit}` unless `endTime` is provided.
3. For `1s`, read `candle:1s:{exchange}:{symbol}` from Redis.
4. For `1m+`, read `candle:1m:{exchange}:{symbol}` first.
5. If Redis is sparse, fall back to InfluxDB.
6. If historical scroll requires older data, use InfluxDB then Trino.
7. Aggregate 1m rows into target interval for `5m+`.
8. For live `5m+`, enrich latest candle with ticker only when ticker is fresher than source sub-candle.
9. Cache result briefly.

Historical `/api/klines/historical`:

1. Validates range, max 1 year.
2. Recent range uses InfluxDB 1m.
3. Older range uses Trino/Iceberg 1m.
4. If no 1m rows and interval is `1h+`, falls back to hourly cold table.
5. Aggregates to requested interval.

### 9.3 Background Tasks

| Task | File | Interval | Notes |
|---|---|---:|---|
| Market fetcher | `backend/tasks/market_fetcher.py` | 300s | Queries Trino and updates `market_service` in-memory cache |
| News fetcher | `backend/tasks/news_fetcher.py` | 300s | Scrapes news, runs VADER sentiment, updates `news_service` in-memory cache |

The in-memory caches reset on FastAPI restart. Future production hardening should move these caches to Redis or lakehouse-backed queries.

---

## 10. Frontend

Stack:

- React `19.1.0`
- TypeScript `5.8.3`
- Vite `6.3.3`
- TailwindCSS `3.4.4`
- lightweight-charts `5.2.0`
- lucide-react `0.396.0`

Build scripts from `frontend/package.json`:

| Script | Command |
|---|---|
| `dev` | `vite` |
| `build` | `tsc --noEmit && vite build` |
| `preview` | `vite preview` |
| `typecheck` | `tsc --noEmit` |

`frontend/tsconfig.json` uses strict TypeScript, `moduleResolution: bundler`, `@/*` alias, and excludes `src/**/__tests__`.

### 10.1 Main UI Areas

| Area | Files |
|---|---|
| App shell | `App.tsx`, `Header.tsx`, `LeftSidebar.tsx`, `RightPanel.tsx`, `TopToolbar.tsx` |
| Chart | `CandlestickChart.tsx`, `chart/*`, `ChartOverlay.tsx` |
| Drawing tools | `DrawingToolbar.tsx`, `DrawingContextToolbar.tsx`, `ToolSettingsPopup.tsx`, `chartStorageService.ts` |
| Market/news | `MarketOverviewPage.tsx`, `NewsPageRedesigned.tsx`, `MarketNews.tsx`, `marketOverviewService.ts` |
| Replay | `ReplayButton.tsx`, `ReplayControls.tsx`, `useReplayMode.ts` |
| Data access | `marketDataService.ts`, `symbolMetaService.ts`, `useApiCall.ts`, `useSymbolMeta.ts` |
| i18n | `i18n/index.tsx`, `i18n/translations.ts` |

### 10.2 Data Mode

Frontend data source is selected by:

```text
VITE_DATA_SOURCE=mock | api
VITE_API_BASE_URL=/api
```

Behavior:

- `mock`: `frontend/src/mock/mockDataGenerator.ts` simulates candles, order books, trades, tickers, and news.
- `api`: services call FastAPI through `/api` by default.

All new frontend API access should live in service files, not directly inside components.

### 10.3 Chart and Time Conventions

Timeframes supported:

```text
1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w
```

Important rules:

- Backend timestamps are epoch milliseconds.
- lightweight-charts uses epoch seconds.
- Convert at service boundary: `openTime / 1000`.
- UI may display uppercase labels (`1H`, `4H`, `1D`, `1W`), but API calls must use lowercase interval keys.
- Live chart uses `/api/stream/all` through `subscribeAllTimeframes`.
- The older `subscribeCandle()` service builds `/api/stream`, but backend currently only exposes `/api/stream/all`.

### 10.4 Drawing and Replay Features

Drawing toolbar currently includes 12 analysis drawing tools:

```text
trendline, ray, extendedLine, horizontal, vertical, rectangle,
arrow, fibRetracement, text, ruler, elliottWave, harmonicABCD
```

It also includes cursor/crosshair and utility controls such as magnet, lock/hide all, eraser, delete selected, and clear all.

Drawings are persisted by symbol/timeframe through `chartStorageService.ts`.

Replay mode:

- Lets user choose a starting candle.
- Pauses live WebSocket/poll updates while replay is active.
- Advances candles based on selected playback speed.

---

## 11. Schemas and Data Contracts

Canonical Avro files:

| File | Record | Notes |
|---|---|---|
| `ticker.avsc` | `Ticker` | Has `exchange`, close, bid, ask, 24h fields |
| `kline.avsc` | `Kline` | Has `exchange`, interval, OHLCV, close flag |
| `trade.avsc` | `AggTrade` | Has `exchange`, aggregate trade fields |
| `depth.avsc` | `Depth` | Has `exchange`, bids/asks as strings |
| `news.avsc` | `NewsSentiment` | News title/source/sentiment/symbols/url |

Rules:

- Treat schemas as cross-service contracts.
- Changing schemas requires producer, Flink, Spark, and tests to be coordinated.
- Do not modify `schemas/*.avsc` casually.

---

## 12. Observability

Monitoring stack:

- Prometheus `v2.45.0`
- Grafana `10.2.0`
- Loki `2.9.0`
- Promtail `2.9.0`
- Redis exporter `v1.83.0`
- Kafka exporter `v1.7.0`
- Node exporter `v1.6.1`
- JMX agents for Kafka and Trino

Prometheus scrape jobs include:

- FastAPI `/metrics`
- Kafka exporter
- Kafka JVM JMX
- Flink JobManager/TaskManager
- Node exporter
- MinIO
- Trino JMX
- Redis exporter
- Spark master/worker Prometheus endpoints

Grafana dashboards in `config/grafana/dashboards`: **11** JSON dashboards.

Alerting rules in `config/grafana/provisioning/alerting/rules.yml`: 8 rules across Flink, Kafka, API, and system health.

Nginx routes:

| Route | Backend | Auth |
|---|---|---|
| `/grafana/` | Grafana | Grafana auth |
| `/prometheus/` | Prometheus | Basic Auth via `MONITORING_USER`/`MONITORING_PASSWORD` |
| `/loki/` | Loki | Basic Auth via `MONITORING_USER`/`MONITORING_PASSWORD` |
| `/api/*` | FastAPI | App/API auth only |

---

## 13. Setup and Operations

Prerequisites:

- Docker Engine 24+ or Docker Desktop 4+.
- 32GB RAM recommended; 24GB minimum for full local stack.
- 100GB+ free disk recommended.
- 8 CPU cores recommended.

First-time setup:

```bash
git clone https://github.com/DoLong3304/LMView.git
cd LMView
cp .env.example .env
# Edit .env: set INFLUX_TOKEN, passwords, API keys, monitoring credentials.
make dev
```

Nginx dev mode creates a temporary self-signed cert if no cert exists. Browser access may redirect from `http://localhost` to `https://localhost`.

Useful commands:

| Command | Purpose |
|---|---|
| `make dev` | Start dev profile |
| `make dev-build` | Rebuild and start dev profile |
| `make dev-logs` | Tail logs |
| `make dev-down` | Stop dev services |
| `make monitoring` | Start dev + monitoring |
| `make logging` | Start dev + monitoring + logging |
| `make prod` | Start prod + monitoring + logging |
| `make stop-all` | Stop all profiles |
| `make submit-jobs` | Run `scripts/auto_submit_jobs.sh` |
| `make status` | Show compose status and container memory |
| `make clean` | Destructive: remove containers, volumes, networks |

Backfill examples:

```bash
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode populate --days 90
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode influx
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode iceberg --iceberg-mode incremental
```

Rebuild guide:

| Changed area | Typical action |
|---|---|
| `backend/` | `docker compose up -d --build fastapi-dev` or `fastapi-prod` |
| `frontend/` | `docker compose up -d --build nginx-dev` or `nginx-prod` |
| `src/producer/` | Rebuild `producer` |
| `src/processing/` | Rebuild Flink image if dependencies changed, then resubmit job |
| `src/batch/`, `src/lakehouse/` | Re-run relevant Spark/Dagster job |
| `docker-compose.yml` | Re-run `docker compose config` and affected profile |

---

## 14. Testing

Pytest config: `pyproject.toml`.

Test directories:

| Directory | Role |
|---|---|
| `tests/unit/` | Constants, models, mappers, candle service |
| `tests/integration/` | FastAPI endpoints with mocked dependencies |
| `tests/e2e/` | App route registration and docs/OpenAPI checks |
| `tests/security/` | Injection, validation, CORS/path checks |
| `tests/performance/` | Aggregation, merge, conversion benchmarks |

Commands:

```bash
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. python -m pytest tests/ -m "unit or integration" -v
PYTHONPATH=. python -m pytest tests/ --cov=backend --cov-report=term-missing
make test
make test-all
make test-cov
```

Frontend:

```bash
cd frontend
npm run typecheck
npm run build
```

Current frontend test files exist under `frontend/src/hooks/__tests__`, but `frontend/package.json` currently has no `test` script and no explicit Jest/Vitest dependency listed.

---

## 15. AI/ML Extension Points

No production ML inference service is currently wired. The project has strong foundations for future AI features:

| Layer | AI use |
|---|---|
| Kafka raw topics | Online feature extraction and event replay |
| Redis hot cache | Low-latency inference inputs and model outputs |
| InfluxDB | Recent time-series windows |
| Iceberg Bronze/Silver/Gold | Offline feature generation, training data, backtests |
| Trino | Feature queries and analytics |
| FastAPI | Future inference and explanation endpoints |
| Frontend | Model signal overlays, explanations, confidence bands, alerts |

Recommended AI feature pattern:

1. Define data contract first: input features, target, prediction horizon, latency target.
2. Store durable training data in Iceberg, not in Redis-only structures.
3. Keep online features reproducible from offline feature code when possible.
4. Add model outputs under clear names such as `prediction:{model}:{symbol}:{timeframe}` or Gold tables.
5. Add monitoring: inference latency, data freshness, drift, null rate, model version.
6. Make model-serving code an explicit boundary (`backend/services` for API logic, future `src/ml` or separate service for training/inference).

---

## 16. Current Caveats and Gotchas

High-impact implementation caveats:

1. **Exchange qualification is partial.** Ticker paths are exchange-aware, but kline aggregation, depth API, trade API, and lakehouse table DDLs still have places that default to or omit `exchange`.
2. **OKX is experimental.** Code exists and producer starts it, but WebSocket subscription handling should be validated before treating OKX as production active-active.
3. **Order book API key mismatch.** Writer uses `orderbook:{exchange}:{symbol}`; API reads `orderbook:{symbol}`.
4. **Trades API key mismatch.** Writer uses `ticker:history:{exchange}:{symbol}`; API reads `ticker:history:{symbol}` and returns ticker-level movements, not real aggregate trades.
5. **Market overview placeholder.** `/api/market/overview` currently returns zero/default data; heatmap/rankings paths query Trino helpers.
6. **Dagster loading should be verified.** Assets/schedules exist, but no explicit `Definitions` object is present in `orchestration/assets.py`.
7. **Single WebSocket endpoint.** Backend exposes `/api/stream/all`; older frontend helper `subscribeCandle()` points to `/api/stream`.

General gotchas:

1. **Time units:** Backend API uses milliseconds; lightweight-charts uses seconds.
2. **Timeframe casing:** UI labels may be uppercase; backend interval keys must be lowercase.
3. **Redis sorted set dedup:** For candles, remove old score with `ZREMRANGEBYSCORE` before `ZADD`.
4. **Ticker freshness:** Only use ticker to enrich live aggregated candles when ticker is newer than source candles.
5. **Influx scroll-left:** Use absolute `range(start: RFC3339, stop: RFC3339)`.
6. **Flink writer env vars:** Read env vars inside `open()` for functions shipped to workers.
7. **Schema changes:** Avro changes require producer, Flink, Spark, and tests to change together.
8. **Nginx dev TLS:** Port 80 redirects to HTTPS; self-signed cert is expected in dev.
9. **Python versions:** Backend/producer/backfill Dockerfiles use Python 3.11. Spark and Flink images install `python3` inside their containers. Do not force Python 3.12+ without validating PyFlink/Spark compatibility.
10. **Do not delete state manually:** Flink checkpoints, InfluxDB data, MinIO/Iceberg objects, Redis volumes, and Kafka volumes need explicit operator approval before destructive changes.

---

## 17. Safe Change Checklist

For backend changes:

- Keep route handlers thin.
- Put business logic in `backend/services/`.
- Use `backend/core/config.py`, `backend/core/constants.py`, and connection singletons.
- Add or update tests for endpoint behavior and service logic.

For frontend changes:

- Keep API calls in `frontend/src/services/*`.
- Keep shared types in `frontend/src/types/index.ts`.
- Use `useI18n()` for user-facing strings.
- Preserve ms-to-seconds conversion at service boundary.
- Run `npm run typecheck` and `npm run build` when touching TypeScript.

For data pipeline changes:

- Keep Avro schemas synchronized end-to-end.
- Preserve `exchange` and `symbol` through keys, state, tables, and APIs.
- Validate Flink serialization behavior.
- Test dedup and out-of-order candle aggregation.

For infrastructure changes:

- Every service must have a `profiles` key or be an extension/template service with `dont-start`.
- Add memory limits and health checks to services that accept connections.
- Validate with `docker compose --profile <profile> config`.

---

## 18. Reference Files

| File | Purpose |
|---|---|
| `docs/SYSTEM.md` | Current system map and technical reference |
| `docs/CHANGELOG.md` | Project history |
| `AGENTS.md` | AI agent workflow and coding rules |
| `README.md` | User-facing overview and setup |
| `docker-compose.yml` | Runtime service graph |
| `.env.example` | Environment variable template |
| `Makefile` | Common operational commands |
| `schemas/*.avsc` | Kafka data contracts |

---

Document version: **4.0**
Maintained by: human contributors and AI coding agents.
