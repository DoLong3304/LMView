
# LMView System Documentation

> Current project map for humans and coding agents.
> Last reviewed from code: 2026-06-07.

---

## 1. Project Snapshot

**LMView** is a real-time cryptocurrency technical-analysis platform built around
Lambda Architecture:

- Speed layer: live exchange data through Kafka, Flink, Redis Sentinel, and InfluxDB.
- Batch/lakehouse layer: Spark, Iceberg on MinIO, PostgreSQL catalog, and Trino.
- Serving layer: FastAPI REST/WebSocket APIs with Redis/Influx/Trino/PostgreSQL clients.
- Frontend layer: React 19 trading dashboard with charts, drawings, replay, auth, settings, market/news, and Phase 1 AI Ask Mode surfaces.

Latest project release from `docs/CHANGELOG.md`: **0.18.0**.

Repository facts from this audit:

- Branch: `main`.
- FastAPI app metadata version: `0.18.0`.
- Frontend package version: `0.3.0`.
- Compose source of truth: one `docker-compose.yml` with profiles.
- Core compose services from static YAML audit: 40 concrete services plus 2 template services.
- Core profile counts from static YAML audit: 29 dev services, 36 dev+monitoring+logging services, 38 prod+monitoring+logging services.
- Optional AI compose overlay: 3 services; `ai-api` starts 2 services and `ai-local` starts 2 services.
- Python tests in source: 341 test functions across 27 files.
- Frontend hook specs in source: 35 `it(...)` specs across 2 files; no frontend test script is currently declared.

This document describes code as it exists now.

---

## 2. Architecture Overview

```text
Exchange WebSockets / REST
  -> src/producer/main.py
  -> Avro serialization + Kafka topics
  -> Flink speed layer
       -> Redis Sentinel hot cache
       -> InfluxDB warm time-series data
  -> Spark batch/lakehouse layer
       -> Iceberg tables on MinIO
       -> Trino serving queries
  -> FastAPI REST + WebSocket serving layer
  -> Nginx reverse proxy
  -> React frontend
```

Primary runtime paths:

| Path | Purpose | Main files |
|---|---|---|
| Ingestion | Exchange ticker, kline, trade, and depth data to Kafka | `src/producer/main.py`, `src/exchanges/*` |
| Speed processing | Hot tickers, candles, order books, and indicators | `src/processing/pipeline.py`, `src/processing/writers/*` |
| Warm storage | Recent time-series analytics | InfluxDB writers and backfill jobs |
| Cold storage | Historical/lakehouse analytics | `src/lakehouse/pipeline.py`, `src/batch/*`, MinIO, Iceberg, Trino |
| Serving | REST, WebSocket, auth, settings, Phase 1 AI Ask Mode APIs | `backend/app.py`, `backend/api/*`, `backend/services/*` |
| UI | Trading dashboard, drawings, replay, auth, settings, AI Helper, market/news | `frontend/src/*` |
| Operations | Compose, Nginx, monitoring, logging, job scripts | `docker-compose.yml`, `docker/*`, `config/*`, `scripts/*` |

---

## 3. Repository Map

```text
backend/
  app.py                    FastAPI app, lifespan, migrations, router registration
  api/                      Thin route handlers
  core/                     Config, constants, DB clients, Redis Sentinel, auth deps
  migrations/               Ordered PostgreSQL SQL migrations
  models/                   Pydantic response/request models
  services/                 Business logic for auth, AI, market data, settings, caches
  tasks/                    Background market/news fetchers

src/
  common/                   Shared config, Kafka client, Avro serializer, logging
  exchanges/                Exchange abstraction plus Binance and OKX clients
  producer/                 Exchange WebSocket -> Kafka producer
  processing/               Flink speed-layer pipeline
  processing/writers/       Redis, InfluxDB, indicator, and kline aggregation writers
  lakehouse/                Spark streaming and Bronze/Silver/Gold helpers
  batch/                    Backfill, retention, maintenance, metrics, unified medallion jobs
  news/                     Multi-source news scraping and VADER sentiment

frontend/
  src/App.tsx               Main dashboard state orchestration
  src/@types/               Vite/global TypeScript declarations
  src/components/layout/    Header and app shell components
  src/components/ui/        Shared providers/widgets
  src/constants/            Env, market, timeframe constants
  src/data/                 Static data and mock adapters/generators
  src/features/             Feature modules: ai, auth, chart, drawing, market, replay, settings, watchlist
  src/hooks/                Reusable hooks and source-only hook specs
  src/i18n/                 English/Vietnamese translation modules
  src/pages/                Route-level market/news pages
  src/routes/               Local view definitions
  src/services/             API clients and service functions
  src/types/                Shared TypeScript types
  src/utils/                Storage and error helpers

orchestration/              Dagster asset and workspace definitions
schemas/                    Avro contracts for Kafka payloads
docker/                     Dockerfiles and service configs
config/                     Prometheus, Loki, Promtail, Spark, JMX, Grafana
scripts/                    Job submission, topic creation, certbot/DuckDNS helpers
tests/                      Pytest unit/integration/e2e/security/performance suites
docs/                       Current system docs, changelog, diagram, archived old doc
```

---

## 4. Runtime Services

`docker-compose.yml` is the runtime source of truth.

Profiles:

| Profile | Role | Static service count |
|---|---|---:|
| `dev` | Core local stack with hot reload/local CORS | 29 |
| `monitoring` | Prometheus, Grafana, exporters | +5 |
| `logging` | Loki, Promtail | +2 |
| `prod` | Production FastAPI/Nginx, SSL automation, DuckDNS helper | 38 with monitoring+logging |
| `dont-start` | Compose template services only | 2 templates |
| `ai-api` | Optional `docker-compose.ai.yml` overlay for LiteLLM/API-provider path | 2 overlay services |
| `ai-local` | Optional `docker-compose.ai.yml` overlay for local vLLM path | 2 overlay services |

Core service groups:

| Group | Services |
|---|---|
| Kafka | `zookeeper`, `kafka-1`, `kafka-2`, `kafka-3`, `schema-registry` |
| Storage | `redis-master`, `redis-replica-1`, `redis-replica-2`, three Sentinels, `influxdb`, `minio`, `minio-init`, `postgres`, `trino` |
| Processing | `producer`, `flink-jobmanager`, `flink-taskmanager`, `spark-master`, `spark-worker`, `spark-worker-2`, `auto-submit-jobs`, `job-watchdog`, `influx-backfill` |
| API/UI | `fastapi-dev` or `fastapi-prod`, `nginx-dev` or `nginx-prod` |
| Orchestration | `dagster-webserver`, `dagster-daemon` |
| Monitoring/logging | `prometheus`, `grafana`, `redis-exporter`, `kafka-exporter`, `node-exporter`, `loki`, `promtail` |
| Production helpers | `certbot-auto`, `duckdns-auto` |
| Optional AI overlay | `ai-service`, `litellm`, `vllm` |

Important ports:

| Service | Host port | Notes |
|---|---:|---|
| Nginx frontend/proxy (dev) | 80 | Plain HTTP only |
| Nginx frontend/proxy (prod) | 80, 443 | HTTP plus HTTPS/certbot automation |
| FastAPI | 8080 | `/docs`, `/api/health` |
| Flink UI | 8081 | JobManager UI |
| Spark master UI | 8082 | Host maps Spark master UI |
| Trino UI | 8083 | Query engine UI |
| InfluxDB | 8086 | Warm time-series store |
| Dagster | 3000 | Orchestration UI |
| Grafana direct | 3001 | Also proxied under `/grafana/` |
| Prometheus direct | 9090 | Also proxied under `/prometheus/` |
| MinIO API/console | 9000/9001 | Object storage |
| Loki direct | 3100 | Also proxied under `/loki/` |

---

## 5. Ingestion Layer

### Exchange Abstraction

Exchange clients implement `src/exchanges/base.py`.

| Exchange | Main files | State |
|---|---|---|
| Binance | `src/exchanges/binance/*` | Primary path. REST and combined-stream URL builders match current generic producer logic. |
| OKX | `src/exchanges/okx/*` | REST symbols/candles plus WebSocket subscription-frame helpers for `tickers`, `trades`, `candle{bar}`, and `books{level}`. Producer startup is gated by `ENABLE_OKX`, which is `false` in compose. |

Producer entry point: `src/producer/main.py`.

Default producer tuning:

| Setting | Default |
|---|---:|
| `MAX_SYMBOLS` | 200 per exchange client |
| `SYMBOLS_PER_CONNECTION` | 25 |
| `SYMBOLS_PER_DEPTH_CONN` | 15 |
| `KLINE_INTERVAL` | `1m` in code, `1s` in compose producer env |
| `DEPTH_LEVEL` | `20` |
| `DEPTH_UPDATE_MS` | `100` |
| `TICKER_HEARTBEAT_SEC` | 5 seconds |

Producer topics:

| Stream | Kafka topic | Schema |
|---|---|---|
| All ticker / mini ticker | `crypto_ticker` | `schemas/ticker.avsc` |
| Aggregate trades | `crypto_trades` | `schemas/trade.avsc` |
| Klines | `crypto_klines` | `schemas/kline.avsc` |
| Depth snapshots | `crypto_depth` | `schemas/depth.avsc` |

Schema Registry endpoint:

```text
http://schema-registry:8080/apis/ccompat/v7
```

Kafka wire format:

```text
0x00 magic byte + 4-byte schema id + Avro binary payload
```

All market Avro schemas include an `exchange` field with default `binance`.

### OKX Current Path

OKX code path:

| Component | File/function | Current behavior |
|---|---|---|
| REST symbols | `OKXClient.fetch_symbols()` | Fetches live spot instruments from `https://www.okx.com/api/v5/public/instruments` and normalizes `BTC-USDT` to `BTCUSDT` |
| REST klines | `OKXClient.fetch_klines()` | Fetches from `/api/v5/market/candles`; OKX returns newest-first batches |
| WebSocket URL | `OKXClient.build_ticker_stream_url()` and `build_combined_stream_url()` | Uses `wss://ws.okx.com:8443/ws/v5/public` |
| Subscription frame | `OKXClient.build_subscribe_frame()` | Sends `{"op":"subscribe","args":[...]}` |
| Ticker channels | `build_ticker_channels()` | Uses `tickers` with `instId` such as `BTC-USDT` |
| Trade channels | `build_trade_channels()` | Uses `trades` with `instId` |
| Kline channels | `build_kline_channels()` | Uses `candle1m`, `candle1H`, `candle1D` by interval |
| Depth channels | `build_depth_channels()` | Uses `books{level}` such as `books5` |
| Producer handler | `_handle_okx_message()` | Dispatches `tickers`, `trades`, `candle*`, and `books*` to Kafka topics |

Compose producer environment sets `ENABLE_OKX: "false"`. When enabled, producer filters OKX symbols to well-known USDT pairs and uses `1m` minimum klines.

---

## 6. Kafka Layer

Kafka uses three `apache/kafka:3.9.0` brokers plus a Zookeeper service still present in compose. Topics use 12 partitions by compose defaults and topic helper script intent.

Topics used by code:

| Topic | Produced by | Consumed by |
|---|---|---|
| `crypto_ticker` | Producer | Flink speed layer, Spark lakehouse |
| `crypto_klines` | Producer | Flink speed layer, Spark lakehouse |
| `crypto_trades` | Producer | Flink trade hot cache, Spark lakehouse |
| `crypto_depth` | Producer | Flink speed layer |
| `crypto_news_sentiment` | Dagster/news path | News/lakehouse path, partially wired |
| `reference_prices` | Price-change stream | `src/processing/price_change_stream.py` |

Topic creation helper: `scripts/create_kafka_topics.sh`.

---

## 7. Speed Layer: Flink + Redis + InfluxDB

Main job: `src/processing/pipeline.py`.

Flink configuration:

- Image: `flink:1.18.1-java11` with `apache-flink==1.18.1`.
- Parallelism default: `FLINK_PARALLELISM=12`.
- State backend: `HashMapStateBackend`.
- Checkpoint interval: 120 seconds.
- Checkpoint mode: `EXACTLY_ONCE`.
- Unaligned checkpoints enabled.
- Checkpoint path: `s3://flink-checkpoints/flink-checkpoints`.

Pipeline branches:

| Branch | Input | Output |
|---|---|---|
| Ticker | `crypto_ticker` | Redis latest/history, InfluxDB `market_ticks` |
| Raw kline | `crypto_klines` | Redis `candle:1s:*`, InfluxDB closed `1m` candles only |
| Kline aggregation | `crypto_klines` 1s rows | Flink state aggregation to 1m, Redis, InfluxDB, indicators |
| Indicators | Closed 1m candles | Redis `indicator:latest:*`, InfluxDB `indicators` |
| Depth | `crypto_depth` | Redis order book hashes |
| Trades | `crypto_trades` | Redis `trade:latest:{exchange}:{symbol}` hot cache |

Current speed-layer behavior:

- `/api/trades/{symbol}` reads the true Redis trade cache first, then falls back to ticker-derived price movements when no trade cache exists.
- `/api/trades/{symbol}/summary` checks `trade:latest:*` first but parses members as ticker-history `price:volume` strings and returns ticker-derived metadata fields.
- Depth table input has `exchange`, but `src/processing/pipeline.py` omits it in the depth select/dict, so `DepthWriter` defaults depth records to `binance`.

### Kline Aggregation

`src/processing/writers/kline_aggregator.py` performs in-flight `1s -> 1m` aggregation.

Behavior:

- Stores 1s candles in keyed Flink `MapState`.
- Deduplicates by `kline_start`.
- Emits previous minute when a new minute appears.
- Has a 65-second processing-time safety timer.
- Forward-fills missing seconds from last close.
- Emits closed 1m candles with OHLCV and trade count.

Current behavior:

- Pipeline keys the aggregator by `exchange:symbol`.
- Aggregator stores and emits `exchange`, so 1m Redis/Influx writes preserve exchange when upstream records carry it.
- OKX kline WebSocket mapping emits `interval: "1s"` for array-format candles before the producer sends Kafka records, even when subscribed to `candle1m`; compose keeps OKX disabled with `ENABLE_OKX=false`.

### Redis Sentinel Hot Cache

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

Main key patterns:

| Key | Type | Writer/Owner | Notes |
|---|---|---|---|
| `ticker:latest:{exchange}:{symbol}` | hash | `keydb_ticker.py` | Latest price, bid/ask, volume, change, event time |
| `ticker:history:{exchange}:{symbol}` | sorted set | `keydb_ticker.py` | Ticker-level history, TTL 600s |
| `candle:1s:{exchange}:{symbol}` | sorted set | `keydb_kline.py` | 1s candles, TTL default 1 day |
| `candle:1m:{exchange}:{symbol}` | sorted set | `keydb_kline.py` | 1m candles, TTL default 7 days |
| `candle:latest:{exchange}:{symbol}` | hash | `keydb_kline.py` | Latest non-1s candle snapshot |
| `indicator:latest:{exchange}:{symbol}:{interval}` | hash | `indicators.py` | Primary indicator snapshot |
| `indicator:latest:{exchange}:{symbol}` | hash | `indicators.py` | Legacy current-interval indicator snapshot |
| `indicator:history:{exchange}:{symbol}:{interval}` | sorted set | `indicators.py` | Indicator history, TTL from env |
| `orderbook:{exchange}:{symbol}` | hash | `keydb_depth.py` and REST fallback | TTL 300s for stream data; REST warm cache TTL 30s |
| `trade:latest:{exchange}:{symbol}` | sorted set | `keydb_trades.py`, direct Redis bypass | True aggregate trades, TTL 600s, newest 200 entries per symbol |
| `klines_cache:{exchange}:{symbol}:{interval}:{limit}` | string | `backend/api/klines.py` | Short API cache, skipped for `endTime` mode |

Important behaviors:

- Candle writes remove an existing sorted-set member at the same timestamp before adding the replacement.
- Backend order book and trade APIs try exchange-qualified keys first, then Binance/OKX fallbacks, then ticker-derived or legacy keys where applicable.
- Backend `get_redis()` returns a replica client for reads; write paths use `get_redis_master()`.

### Direct Redis Bypass and Producer Health Monitor

Direct Redis writer: `src/exchanges/binance/redis_writer.py`.

Written key families:

| Method | Key | TTL |
|---|---|---:|
| `write_ticker()` | `ticker:latest:{exchange}:{symbol}` | 300s |
| `write_kline()` | `candle:{interval}:{exchange}:{symbol}` | 86400s |
| `write_trade()` | `trade:latest:{exchange}:{symbol}` | 600s |
| `write_depth()` | `orderbook:{exchange}:{symbol}` | 300s |

Health monitor: `src/producer/health_monitor.py`.

| Setting | Default | Current use |
|---|---:|---|
| `HEALTH_CHECK_INTERVAL_SEC` | 30 | Kafka/Flink health poll interval |
| `FAILOVER_THRESHOLD_SEC` | 60 | Duration with Kafka and Flink both down before direct Redis state turns on |
| `RECOVERY_THRESHOLD_SEC` | 120 | Duration with Kafka or Flink recovered before direct Redis state turns off |
| `FLINK_JM_URL` | `http://flink-jobmanager:8081` | Flink `/jobs` health URL |

Producer path state:

- Binance ticker handler checks `health_monitor.is_direct_redis_active()`.
- Binance kline/trade/depth and OKX direct writes check static `ENABLE_DIRECT_REDIS`.
- Compose sets `ENABLE_DIRECT_REDIS: "false"` on the producer service.

### InfluxDB Warm Storage

InfluxDB 2.7 stores recent analytical data.

| Setting | Default |
|---|---|
| URL | `http://influxdb:8086` |
| Org | `vi` |
| Bucket | `crypto` |
| 1m retention constant | `INFLUX_1M_RETENTION_DAYS=90` |

Measurements used by code:

| Measurement | Writer | Notes |
|---|---|---|
| `market_ticks` | `influxdb_ticker.py`, backfill path | Ticker samples tagged by symbol/exchange |
| `candles` | `influxdb_kline.py`, backfill path | Closed 1m candles and historical OHLCV |
| `indicators` | `indicators.py` | SMA/EMA/RSI/MACD/Bollinger/ATR metrics tagged by symbol and exchange |

Flux historical scroll queries must use absolute RFC3339 ranges for `endTime` mode. Relative ranges break scroll-left semantics.

---

## 8. Batch and Lakehouse Layer

### Spark Structured Streaming

Main job: `src/lakehouse/pipeline.py`.

Purpose:

- Read Kafka topics.
- Strip Confluent Avro wire header.
- Decode payloads with `from_avro`.
- Write append streams to Iceberg tables.

Tables created in `iceberg_catalog.crypto_lakehouse`:

| Table | Source topic | Checkpoint |
|---|---|---|
| `coin_ticker` | `crypto_ticker` | `s3://cryptoprice/checkpoints/crypto_ticker_v1` |
| `coin_trades` | `crypto_trades` | `s3://cryptoprice/checkpoints/crypto_trades_v1` |
| `coin_klines` | `crypto_klines` | `s3://cryptoprice/checkpoints/crypto_klines_v1` |

Current table behavior:

- `src/lakehouse/pipeline.py` table DDLs now include `exchange`, and kline dedup includes `exchange`.
- Ticker streaming still deduplicates by `["symbol", "event_timestamp"]` instead of `["exchange", "symbol", "event_timestamp"]`, so same-symbol same-timestamp records from multiple exchanges can collapse before Iceberg write.

### Batch Jobs

| File | Role |
|---|---|
| `src/batch/backfill.py` | Binance historical import and gap fill for InfluxDB/Iceberg |
| `src/batch/aggregate.py` | 1m retention and aggregation maintenance |
| `src/batch/maintenance.py` | Iceberg compaction, manifest optimization, orphan cleanup |
| `src/batch/calculate_all_metrics.py` | Gold metrics orchestration |
| `src/batch/calculate_indicators.py` | Momentum indicator calculations |
| `src/batch/bronze_to_silver.py`, `silver_to_gold.py` | Older medallion jobs |
| `src/batch/unified/*` | Consolidated medallion jobs for ticker, kline, news, indicators, daily aggregation |

### Medallion Helpers

Bronze/Silver/Gold helper modules exist under `src/lakehouse/`.

| Layer | Examples |
|---|---|
| Bronze | Raw ticker/kline/news writers |
| Silver | `ticker_unified`, `kline_multi_timeframe`, `news_enriched` |
| Gold | `market_overview`, `symbol_stats_daily`, `sector_performance`, `market_dominance`, `volatility_ranking`, `movers_ranking`, `momentum_indicators`, `news_sentiment_daily` |

These modules back market overview, heatmap, rankings, news sentiment, and AI context data when their Spark/Dagster jobs populate the matching Iceberg tables.

### Dagster

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

Current Dagster behavior:

- `assets.py` now exposes `defs = Definitions(...)` and lazy-imports `news.enhanced_scraper.MultiSourceNewsScraper`.
- Dagster Spark session config uses a Hadoop Iceberg catalog and `s3a://lakehouse/warehouse`.
- Streaming lakehouse pipeline uses a JDBC Iceberg catalog and `s3://cryptoprice/iceberg`.
- News and Kafka dependencies are imported lazily inside the news asset; runtime asset execution imports those dependencies inside the Dagster container.

---

## 9. Serving Layer: FastAPI

FastAPI entry point: `backend/app.py`.

Lifecycle:

1. Initialize async PostgreSQL pool.
2. Run ordered SQL migrations when `RUN_MIGRATIONS` is true.
3. Ensure a default admin account exists when no active admin exists and `DEFAULT_ADMIN_*` env vars are configured.
4. Start background news and market fetchers.
5. On shutdown, stop fetchers and close Redis/Influx/PostgreSQL clients.

Router inclusion order:

```text
health, ticker, klines, historical, orderbook, trades, symbols,
indicators, websocket, market_overview, market, news, auth, ai, settings, admin
```

Order matters: `market_overview` is registered before legacy `market`, so overlapping `/api/market/overview` and `/api/market/heatmap` paths resolve to `backend/api/market_overview.py`.

### PostgreSQL Auth/AI/Settings Store

PostgreSQL is used both as the Iceberg JDBC catalog database and as the app persistence store for auth, AI, settings, notifications, and admin controls.

Migrations:

| Migration | Role |
|---|---|
| `001_phase0_schema.sql` | Users, sessions, preferences, AI sessions/messages/chart snapshots/tool actions, news articles, AI knowledge docs |
| `002_phase1_readiness.sql` | Profile fields, forced password-change fields, JSON settings, notifications, app settings, watchlist activity, AI context/action columns |
| `003_phase1_ai_rag.sql` | pgvector extension, knowledge sources/chunks/embeddings, HNSW index, retrieval audit logs |

Default admin bootstrap:

- Runs at FastAPI startup after migrations.
- Only acts when no active admin exists.
- Uses `DEFAULT_ADMIN_EMAIL`, `DEFAULT_ADMIN_INITIAL_PASSWORD`, `DEFAULT_ADMIN_DISPLAY_NAME`, and `DEFAULT_ADMIN_USERNAME`.
- Marks system-created/recovered admins with `must_change_password = TRUE`.
- Does not log credentials.

### API Endpoints

| Method | Path | Main source | Notes |
|---|---|---|---|
| GET | `/api/health` | Redis, InfluxDB, Trino | Does not include PostgreSQL in this endpoint |
| GET | `/api/ticker/{symbol}` | Redis | Exchange-specific or aggregated ticker |
| GET | `/api/ticker` | Redis scan | All tickers, optional exchange filter, activity ordering |
| GET | `/api/klines` | Redis -> InfluxDB -> Trino | Live/recent candles and `endTime` scroll-left mode |
| GET | `/api/klines/historical` | InfluxDB + Trino | Range query, max 1 year |
| WS | `/api` + `/stream/{interval}` | Redis | Single-timeframe candle stream for `1s` through `1w` |
| WS | `/api` + `/stream/indicators/{interval}` | Redis | Single-timeframe indicator snapshot stream |
| WS | `/api` + `/stream/all` | Redis | All-timeframe candle stream |
| GET | `/api/orderbook/{symbol}` | Redis, ticker-derived, Binance REST fallback | Includes source/freshness metadata |
| GET | `/api/orderbook/{symbol}/summary` | Order book endpoint | Compact AI context summary |
| GET | `/api/trades/{symbol}` | Redis trade cache -> ticker history fallback | Real exchange-trade JSON when `trade:latest:*` exists; ticker-derived fallback otherwise |
| GET | `/api/trades/{symbol}/summary` | Redis trade cache -> ticker history fallback | Parses payloads as ticker-history `price:volume` and returns ticker-derived metadata fields |
| GET | `/api/symbols` | Redis scan | Supports legacy and exchange-qualified ticker keys |
| GET | `/api/indicators/supported` | Static catalog | Supported backend indicator names |
| GET | `/api/indicators/{symbol}` | Redis | Indicator snapshot |
| GET | `/api/indicators/{symbol}/summary` | Redis | Compact AI context summary |
| GET | `/api/market/overview` | Trino gold -> Redis ticker fallback | Fallback source is `ticker_derived` and marks `metadata.is_placeholder = true` |
| GET | `/api/market/heatmap` | Trino gold helpers | Route from `market_overview.py`; helper still has one `iceberg_catalog.gold` join |
| GET | `/api/market/rankings/{category}` | Trino gold helpers | `gainers`, `losers`, `volume`, `volatile` |
| GET | `/api/market/metrics` | In-memory cache | Updated by market fetcher |
| GET | `/api/market/gainers` | In-memory cache | Updated by market fetcher |
| GET | `/api/market/losers` | In-memory cache | Updated by market fetcher |
| GET | `/api/market/symbol/{symbol}` | In-memory cache | Single-symbol market cache lookup |
| GET | `/api/news/latest` | In-memory news cache | Optional source/symbol/hour filters |
| GET | `/api/news/sources` | Static source list | 12 configured sources |
| GET | `/api/news/trending` | In-memory news cache | Trending articles and symbols |
| GET | `/api/news/sentiment/{symbol}` | In-memory news cache | Symbol sentiment summary |
| GET | `/api/news/search` | In-memory news cache | Keyword search |
| POST | `/api/auth/register` | PostgreSQL | Creates user and bearer session |
| POST | `/api/auth/login` | PostgreSQL | Creates bearer session |
| POST | `/api/auth/logout` | PostgreSQL | Revokes current session |
| GET | `/api/auth/me` | PostgreSQL | User plus preferences |
| PATCH | `/api/auth/preferences` | PostgreSQL | Legacy user preference patch |
| PATCH | `/api/auth/profile` | PostgreSQL | Profile fields |
| POST | `/api/auth/change-password` | PostgreSQL | Password update |
| DELETE | `/api/auth/account` | PostgreSQL | Account deactivation after confirmation |
| GET | `/api/ai/health` | PostgreSQL + provider/RAG checks | Reports AI mode, RAG, pgvector, providers, knowledge source count |
| POST | `/api/ai/chat` | PostgreSQL + scope gate + RAG + provider router | Auth required; real LLM path when enabled/configured, mock fallback always available |
| GET/POST | `/api/ai/sessions` | PostgreSQL | Session list/create |
| GET | `/api/ai/sessions/{session_id}/messages` | PostgreSQL | User-owned session messages |
| POST | `/api/ai/chart-context` | PostgreSQL | Store chart context snapshot |
| POST | `/api/ai/chart-actions/validate` | Validator | Validate proposed chart actions only |
| POST | `/api/ai/chart-actions/record` | Acknowledgement | Records approval/execution state shape |
| POST | `/api/ai/knowledge/ingest` | PostgreSQL + pgvector | Admin-only markdown ingestion; defaults to approved knowledge base dir |
| POST | `/api/ai/knowledge/search` | PostgreSQL + pgvector | Authenticated vector search |
| GET | `/api/ai/knowledge/sources` | PostgreSQL | Authenticated knowledge source listing |
| GET | `/api/ai/knowledge/health` | PostgreSQL + pgvector | Authenticated knowledge base health |
| GET | `/api/settings` | PostgreSQL | Bundled user settings |
| PATCH | `/api/settings/notifications` | PostgreSQL | Notification preferences |
| PATCH | `/api/settings/customization` | PostgreSQL | UI/chart defaults |
| PATCH | `/api/settings/ai` | PostgreSQL | AI Helper settings |
| PATCH | `/api/settings/alerts` | PostgreSQL | Alert settings |
| GET | `/api/notifications` | PostgreSQL | User notifications and unread count |
| POST | `/api/notifications/read` | PostgreSQL | Mark one or all notifications read |
| GET | `/api/admin/users` | PostgreSQL | Admin-only user list/search |
| PATCH | `/api/admin/users/{user_id}` | PostgreSQL | Admin-only role/active-state update |
| POST | `/api/admin/users/{user_id}/force-password-change` | PostgreSQL | Admin-only flag update |
| GET | `/api/admin/app-settings` | PostgreSQL | Admin-only app settings |
| PATCH | `/api/admin/app-settings/{key}` | PostgreSQL | Admin-only app setting update |

### WebSocket Serving Logic

Backend WebSocket routes live in `backend/api/websocket.py`.

| Route | Frontend service helper | Payload source | Loop interval |
|---|---|---|---:|
| `/api/stream/{interval}` | `subscribeCandle()` | Redis candles plus ticker enrichment for `5m+` | 0.05s |
| `/api/stream/indicators/{interval}` | `subscribeIndicatorStream()` | Redis `indicator:latest:{exchange}:{symbol}:{interval}` with fallbacks | 0.05s |
| `/api/stream/all` | `subscribeAllTimeframes()` | Redis candles for all supported intervals plus shared ticker lookup | 0.05s |

Supported WebSocket intervals:

```text
1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w
```

`/api/stream/all` returns a map keyed by interval. It sends only when at least one interval payload changes.

### Candle Serving Logic

`backend/api/klines.py` and `backend/services/candle_service.py` are the core candle serving path.

Live `/api/klines`:

1. Normalize symbol, exchange, interval, and limit.
2. Use short cache unless `endTime` is provided.
3. For `1s`, read Redis `candle:1s:{exchange}:{symbol}`.
4. For `1m+`, read Redis `candle:1m:{exchange}:{symbol}` first.
5. If Redis is sparse, fall back to InfluxDB and then Trino as needed.
6. Aggregate 1m rows into target interval for `5m+`.
7. For live `5m+`, enrich latest candle with ticker only when ticker is fresher than source sub-candle.
8. Cache result briefly.

Historical `/api/klines/historical`:

1. Validate range, max 1 year.
2. Use InfluxDB for recent 1m data.
3. Use Trino/Iceberg for older 1m data.
4. Fall back to hourly cold table for long intervals when needed.
5. Aggregate to requested interval.

### Indicator Serving Logic

Backend indicator routes live in `backend/api/indicators.py`; business logic lives in `backend/services/indicator_service.py`.

Supported indicator catalog includes:

```text
sma20, sma50, ema12, ema26, rsi, macd, bollinger_bands, bb,
vwap, atr, volume_ma, volumeMa, stochastic, mfi, ichimoku,
supertrend, psar, volume, support_resistance, whale_alert
```

Read order for `/api/indicators/{symbol}`:

1. `indicator:latest:{exchange}:{symbol}:{interval}`
2. `indicator:latest:{exchange}:{symbol}`
3. `indicator:latest:{symbol}`
4. Redis-derived computation from `candle:1m:{exchange}:{symbol}` when precomputed values are absent or older than 120 seconds.

Indicator responses include `source`, `freshness_seconds`, `is_stale`, and `is_fallback`.

### Trade Serving Logic

Backend trade routes live in `backend/api/trades.py`.

`/api/trades/{symbol}` read order:

1. `trade:latest:{exchange}:{symbol}`
2. `trade:latest:binance:{symbol}`
3. `trade:latest:okx:{symbol}`
4. `ticker:history:{exchange}:{symbol}`
5. `ticker:history:binance:{symbol}`
6. `ticker:history:okx:{symbol}`

When a `trade:latest:*` key is found, response metadata uses `data_type: "exchange_trade"` and `is_true_trade_tape: true`. When ticker history is used, response metadata uses `data_type: "ticker_derived"` and `is_true_trade_tape: false`.

`/api/trades/{symbol}/summary` uses the same key order but parses response members as ticker-history strings and returns `data_type: "ticker_derived"`.

### Background Tasks

| Task | File | Interval | Notes |
|---|---|---:|---|
| Market fetcher | `backend/tasks/market_fetcher.py` | 300s | Queries Trino `coin_ticker` and updates in-memory market cache |
| News fetcher | `backend/tasks/news_fetcher.py` | 300s | Uses `EnhancedMultiSourceScraper`, VADER sentiment, in-memory news cache |

In-memory market/news caches are process-local and reset on FastAPI restart.

---

## 10. Frontend

Stack from `frontend/package.json`:

- React `19.1.0`
- TypeScript `5.8.3`
- Vite `6.3.3`
- TailwindCSS `3.4.4`
- lightweight-charts `5.2.0`
- lucide-react `0.396.0`

Scripts:

| Script | Command |
|---|---|
| `dev` | `vite` |
| `build` | `tsc --noEmit && vite build` |
| `preview` | `vite preview` |
| `typecheck` | `tsc --noEmit` |

`frontend/tsconfig.json` uses strict TypeScript, `moduleResolution: bundler`, `@/*` alias, and excludes `src/**/__tests__`.

### Source Organization

| Folder | Role |
|---|---|
| `@types/` | Global TypeScript/Vite declarations |
| `components/layout/` | App shell layout |
| `components/ui/` | Shared providers/widgets |
| `constants/` | Env, timeframe, market constants |
| `data/` | Static fallback data and mock API adapters |
| `features/` | Feature-owned UI and logic |
| `hooks/` | Reusable hooks and source-only specs |
| `i18n/` | Locale provider plus `locales/en.ts` and `locales/vi.ts` |
| `pages/` | Route-level market/news screens |
| `routes/` | Local route/view definitions |
| `services/` | API clients and service functions |
| `types/` | Shared app types |
| `utils/` | Generic storage/error helpers |

### Main UI Areas

| Area | Files |
|---|---|
| App shell | `App.tsx`, `components/layout/Header.tsx`, `components/layout/LeftSidebar.tsx`, `features/watchlist/components/RightPanel.tsx` |
| Chart | `features/chart/CandlestickChart.tsx`, `DateRangePicker.tsx`, `MarketSelector.tsx`, `IndicatorPanel.tsx`, `OHLCVBar.tsx`, `OscillatorPane.tsx`, `OverviewChart.tsx` |
| Drawing tools | `features/drawing/components/*`, `services/chartStorageService.ts` |
| Market/news | `pages/MarketOverviewPage.tsx`, `pages/NewsPage.tsx`, `features/market/components/*`, market/news services |
| Replay | `features/replay/components/ReplayControls.tsx`, `hooks/useReplayMode.ts` |
| Auth | `features/auth/AuthContext.tsx`, `features/auth/AuthModal.tsx`, `services/authService.ts` |
| Settings/admin | `features/settings/SettingsModal.tsx`, `services/settingsService.ts` |
| AI Helper | `features/ai/components/AiAssistantPanel.tsx`, `features/ai/hooks/useAiChat.ts`, `services/aiService.ts` |

### Data Mode

Frontend data source:

```text
VITE_DATA_SOURCE=mock | api
VITE_API_BASE_URL=/api
```

Behavior:

- `api` is the default and calls FastAPI through `/api`.
- `mock` uses API-shaped adapters under `frontend/src/data/mock/`.
- API-mode placeholder/mock-tagged payloads are treated as unavailable/empty instead of generating fake live data.
- User-facing UI must not expose internal data-source or debug labels outside admin-only debug surfaces.

### Chart and Time Conventions

Supported timeframes:

```text
1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w
```

Rules:

- Backend timestamps are epoch milliseconds.
- lightweight-charts uses epoch seconds.
- Convert at service boundary: `openTime / 1000`.
- UI may display uppercase labels such as `1H`, `4H`, `1D`, `1W`; API params must use lowercase interval keys.
- Main chart uses `subscribeAllTimeframes()`.
- `marketDataService.ts` also exposes `subscribeCandle()` for `/api/stream/{interval}` and `subscribeIndicatorStream()` for `/api/stream/indicators/{interval}`.

### Auth, Settings, and Notifications

- Bearer session token is stored by `authService.ts` in localStorage.
- API mode uses PostgreSQL-backed auth endpoints.
- Mock mode stores local mock users/settings/notifications in localStorage.
- Settings modal includes Account, Notifications, Customization, AI Helper, About, Debug, and Admin Accounts surfaces.
- Debug and Admin Accounts tabs are admin-only.
- Header notification popup uses `fetchNotifications()` and `markNotificationsRead()`.

### AI Helper

Current state:

- Frontend AI Helper requires login in API mode.
- Backend `/api/ai/*` endpoints persist sessions/messages/snapshots and support Phase 1 Ask Mode.
- Ask Mode path is: scope gate -> session persistence -> optional RAG retrieval -> prompt builder -> provider router -> output guard -> message persistence.
- `AI_MODE=mock` or `AI_ENABLE_REAL_LLM=false` keeps deterministic mock behavior.
- `AI_ENABLE_REAL_LLM=true` with `AI_MODE=api|local|auto`, provider keys, and runtime dependencies can route to LiteLLM/vLLM-compatible providers; mock remains final fallback.
- Local LMView Help mode exists for mock/API-fallback behavior.
- Knowledge ingestion/search uses PostgreSQL + pgvector after migration `003_phase1_ai_rag.sql` and embedding dependencies are present.
- `docker-compose.ai.yml` adds optional `litellm` and `vllm` services. Its `ai-service` container uses an `echo` command and exits; Phase 1 logic runs inside core FastAPI.

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
- Schema changes require producer, Flink, Spark, backend, frontend types where relevant, and tests to be coordinated.
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

Prometheus scrape jobs include FastAPI metrics, exporters, Kafka JMX, Flink, MinIO, Trino JMX, Redis, and Spark endpoints.

Grafana dashboards in `config/grafana/dashboards`: **22** JSON dashboards.

Alerting rules in `config/grafana/provisioning/alerting/rules.yml`: **18** rules across Flink, Kafka, API, system, Postgres, InfluxDB, Nginx, Zookeeper, Dagster, producer, and log-derived health.

Producer Prometheus metrics run on port `9090` in `src/producer/main.py`.

| Metric | Type | Labels |
|---|---|---|
| `producer_ws_threads_running` | Gauge | none |
| `producer_kafka_messages_sent_total` | Counter | `topic` |
| `producer_kafka_send_errors_total` | Counter | `topic` |
| `producer_heartbeat_timestamp_seconds` | Gauge | `thread_name` |
| `producer_ws_reconnects_total` | Counter | `stream` |
| `producer_ticker_throttle_skipped_total` | Counter | none |

Promtail label extraction:

| Label | Source pattern |
|---|---|
| `log_level` | Timestamped Python-style log lines with bracketed level |
| `error_type` | Case-insensitive `Exception`, `Error`, `Fatal`, `Traceback`, `panic`, `OOM`, or `timeout` |
| `service` | Docker compose service label |

Dashboard coverage includes system overview, system error triage, FastAPI logs, Kafka health/JVM/logs, Flink monitoring/logs, Spark dashboards/logs, Redis dashboards/logs, MinIO dashboards/logs, Trino dashboards/logs, Nginx, Postgres, Zookeeper, Dagster, InfluxDB, and producer metrics.

Nginx proxy routes:

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
# Edit .env: set strong tokens/passwords, API keys, monitoring credentials, and default admin values.
make dev
```

Nginx dev mode serves plain HTTP on port 80. Access the app at `http://localhost`.

For production HTTPS, set `CERTBOT_DOMAIN` and `CERTBOT_EMAIL` in `.env` and run `scripts/init_certbot.sh <domain> <email>`. DuckDNS is optional.

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
| `docker-compose.yml` | Re-run compose config validation and affected profile |

---

## 14. Testing

Pytest config: `pyproject.toml`.

Test directories:

| Directory | Role |
|---|---|
| `tests/unit/` | Constants, models, auth/AI, mappers, candle service; 211 source-scanned test functions |
| `tests/integration/` | FastAPI endpoints with mocked dependencies; 61 source-scanned test functions |
| `tests/e2e/` | App route registration and OpenAPI checks; 6 source-scanned test functions |
| `tests/security/` | Injection, validation, CORS/path checks; 18 source-scanned test functions |
| `tests/performance/` | Aggregation, merge, conversion benchmarks; 9 source-scanned test functions |
| `tests/ai/` | Phase 1 AI provider/RAG/prompt/safety tests; 36 source-scanned test functions |

Commands:

```bash
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. python -m pytest tests/ -m "unit or integration" -v
PYTHONPATH=. python -m pytest tests/ --cov=backend --cov-report=term-missing
make test
make test-all
make test-cov
```

If local host has no `python` shim, use `python3` or the project virtualenv explicitly.

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run build
```

Current frontend hook specs exist under `frontend/src/hooks/__tests__`, but `frontend/package.json` has no `test` script and no explicit Jest/Vitest dependency.

Current source test inventory:

- 341 pytest test functions across 27 Python test files.
- 35 frontend hook `it(...)` specs across 2 TypeScript files.
- Frontend hook specs are source-only under `frontend/src/hooks/__tests__`; `frontend/package.json` has no `test` script and no explicit Jest/Vitest dependency.

Local verification state:

- Full pytest requires project dependencies installed on the host or inside the intended container image.
- Docs-only audits use static checks. Backend/frontend behavior changes use focused tests.

---

## 15. AI Ask Mode Current State

Current AI state is **Phase 1 Ask Mode**.

### Backend AI Package

| Area | Files | Current behavior |
|---|---|---|
| Router package | `backend/api/ai/__init__.py` | Registers `/api/ai` child routers for health, chat, sessions, chart context, chart actions, and knowledge |
| Chat route | `backend/api/ai/chat.py` | Runs scope gate, session management, message storage, mock or real LLM path, output guard, confidence estimate, and assistant message storage |
| Sessions | `backend/api/ai/sessions.py` | Lists/creates user-owned sessions and reads session messages |
| Chart context | `backend/api/ai/chart_context.py` | Stores chart context snapshots for authenticated users |
| Chart actions | `backend/api/ai/chart_actions.py` | Validates and records chart-action payloads |
| Knowledge | `backend/api/ai/knowledge.py` | Admin ingest plus authenticated search/sources/health endpoints |
| Legacy compatibility | `backend/api/ai_legacy.py` | Preserved legacy route module; `backend/app.py` imports the modular package |

### AI Services

| Service | File | Current behavior |
|---|---|---|
| Scope gate | `backend/services/scope_gate_service.py` | Rule-based topic and prompt-injection classification before model/RAG calls |
| Chat persistence | `backend/services/ai_chat_service.py` | PostgreSQL sessions/messages access |
| Mock response | `backend/services/ai_mock_service.py`, `backend/services/ai/mock_provider.py` | Deterministic response path and provider fallback |
| Provider interface | `backend/services/ai/base_provider.py` | Shared provider protocol |
| Provider router | `backend/services/ai/provider_router.py` | Provider order from env, lazy provider registration, mock fallback |
| LiteLLM provider | `backend/services/ai/litellm_provider.py` | Lazy `litellm` import and async completion calls |
| Prompt builder | `backend/services/ai/prompt_builder.py` | System prompt, chart context, RAG chunks, conversation history, data caveats, user message |
| Context service | `backend/services/ai/context_service.py` | Data caveat list from chart/market/trade/orderbook/news/OKX context |
| Output guard | `backend/services/ai/output_guard.py` | Financial-safety validation, code-block removal, disclaimer handling |
| Knowledge service | `backend/services/ai/knowledge_service.py` | Markdown chunking, content hash, embedding generation, PostgreSQL storage |
| Retrieval service | `backend/services/ai/retrieval_service.py` | pgvector cosine search, filters, retrieval audit logging |

### Provider and RAG Configuration

| Setting | Default in code/env | Current effect |
|---|---|---|
| `AI_MODE` | `mock` | `mock`, `api`, `local`, or `auto` provider ordering |
| `AI_ENABLE_REAL_LLM` | `false` | Enables real provider path when true and `AI_MODE != "mock"` |
| `AI_ENABLE_RAG` | `true` | Enables retrieval attempt in real LLM path |
| `AI_PROVIDER_ORDER` | `local_vllm,qwen_api,llama_api,mock` | Local/auto provider priority |
| `AI_TEST_PROVIDER_ORDER` | `qwen_api,llama_api,local_vllm,mock` | API-mode provider priority |
| `AI_ENABLE_PROVIDER_FALLBACK` | `true` | Tries next provider when one fails |
| `AI_RAG_TOP_K` | `6` | Retrieval result limit |
| `AI_RAG_MIN_SCORE` | `0.25` | Minimum similarity score |
| `AI_KB_APPROVED_ONLY` | `true` | Limits retrieval to approved sources |

Runtime dependency state from repository files:

- `docker/fastapi/requirements.txt` includes `asyncpg`, auth dependencies, FastAPI, Redis, InfluxDB, Trino, and news scraping packages.
- `docker/fastapi/requirements.txt` does not include `litellm` or `sentence-transformers`.
- `backend/services/ai/litellm_provider.py` imports `litellm` lazily.
- `backend/services/ai/knowledge_service.py` imports `sentence_transformers` lazily.
- `backend/migrations/003_phase1_ai_rag.sql` creates pgvector-backed knowledge sources, chunks, embeddings, HNSW index, and retrieval logs.

---

## 16. Current Runtime Constraints

High-impact current behaviors:

1. **OKX is opt-in.** Subscription-frame builders and handlers have unit coverage, compose keeps `ENABLE_OKX=false`, and OKX kline Kafka records carry `interval: "1s"` for array-format `candle1m` messages.
2. **Exchange propagation has split behavior.** Ticker, kline aggregation, indicators, and trade cache are exchange-aware. Depth processing drops `exchange` before `DepthWriter`, and lakehouse ticker dedup omits `exchange`.
3. **Trades are mixed-source.** `/api/trades/{symbol}` reads true Redis trade tape first, then ticker-derived fallback. `/api/trades/{symbol}/summary` checks true trade keys first but parses members as ticker-history strings and returns ticker-derived metadata fields.
4. **Market overview has fallback semantics.** `/api/market/overview` tries Trino gold tables, then derives from Redis ticker cache and marks placeholder metadata. Heatmap helper still contains one `iceberg_catalog.gold` join while other gold queries use `iceberg.gold`.
5. **Dagster uses a separate catalog shape.** `defs = Definitions(...)` and lazy news imports exist; Dagster Spark assets use a different Iceberg catalog/warehouse config than the main streaming lakehouse job.
6. **AI Phase 1 real path depends on runtime extras.** Core FastAPI requirements do not include `litellm` or `sentence-transformers`, and pgvector must be installed in PostgreSQL for RAG embeddings/search.
7. **AI overlay support services are separate from embedded FastAPI AI.** `docker-compose.ai.yml` starts LiteLLM/vLLM support services, while `ai-service` exits after an echo command. Phase 1 runs embedded in core FastAPI.
8. **Direct Redis auto-failover covers one hot path.** Health monitor can toggle the global direct writer state; Binance ticker checks `health_monitor.is_direct_redis_active()` when static `ENABLE_DIRECT_REDIS=false`; kline/trade/depth paths gate on the static env flag.
9. **WebSocket routes have three shapes.** Backend exposes `/api/stream/{interval}`, `/api/stream/indicators/{interval}`, and `/api/stream/all`. Main chart uses `/api/stream/all`.
10. **PostgreSQL health is separate.** `/api/health` checks Redis, InfluxDB, and Trino; `/api/ai/health` reports PostgreSQL/AI/RAG/provider readiness.
11. **Test execution depends on environment.** Full local pytest requires project dependencies; the source inventory contains 341 pytest functions.

General invariants:

1. Backend API timestamps are milliseconds; lightweight-charts expects seconds.
2. UI labels may be uppercase; backend interval keys must be lowercase.
3. Candle sorted-set dedup must remove the old score before `ZADD`.
4. Ticker enrichment overrides live aggregated candles only when ticker is newer than source candles.
5. Influx scroll-left mode must use absolute `range(start: RFC3339, stop: RFC3339)`.
6. PyFlink writer classes read worker-specific environment values in `open()` when serialization requires it.
7. Schema changes require coordinated producer, Flink, Spark, backend, frontend, and tests.
8. Dev Nginx uses plain HTTP on port 80. Prod uses HTTPS on 443 with certbot automation and a fallback certificate path.
9. Backend/producer/backfill Dockerfiles use Python 3.11.
10. Do not manually delete Flink checkpoints, InfluxDB data, MinIO/Iceberg objects, Redis volumes, or Kafka volumes without explicit operator approval.

---

## 17. Safe Change Checklist

Backend:

- Keep route handlers thin.
- Put business logic in `backend/services/`.
- Use `backend/core/config.py`, `backend/core/constants.py`, and connection singletons.
- Add/update tests for endpoint behavior and service logic.
- Keep auth/admin/settings changes aligned with PostgreSQL migrations.

Frontend:

- Keep API calls in `frontend/src/services/*`.
- Keep shared types in `frontend/src/types/index.ts`.
- Keep shell/UI components in `components/layout` or `components/ui`.
- Keep feature UI under `frontend/src/features/<feature>/`.
- Keep mock/static data under `frontend/src/data/`.
- Use `useI18n()` for user-facing strings.
- Preserve ms-to-seconds conversion at service boundary.
- Run `npm run typecheck` and `npm run build` when touching TypeScript.

Data pipeline:

- Keep Avro schemas synchronized end-to-end.
- Preserve `exchange`, `symbol`, and event timestamps through keys, state, tables, and APIs.
- Validate Flink serialization behavior.
- Test dedup and out-of-order candle aggregation.

Infrastructure:

- Every concrete service must have a `profiles` key.
- Template services may use `profiles: ["dont-start"]`.
- Services that accept connections have health checks.
- Services have memory limits where Compose supports them.
- Validate Compose changes with profile-specific config commands.

---

## 18. Reference Files

| File | Purpose |
|---|---|
| `docs/SYSTEM.md` | Current system map and technical reference |
| `docs/CHANGELOG.md` | Project history |
| `AGENTS.md` | AI agent workflow and coding rules |
| `README.md` | User-facing overview and setup |
| `docs/ai/*.md` | Phase 1 AI architecture, contracts, provider routing, RAG, evaluation, and security documentation |
| `docker-compose.yml` | Runtime service graph |
| `.env.example` | Environment variable template |
| `Makefile` | Common operational commands |
| `schemas/*.avsc` | Kafka data contracts |

---

Document version: **5.0**
Maintained by: human contributors and AI coding agents.
