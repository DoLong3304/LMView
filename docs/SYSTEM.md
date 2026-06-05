
# LMView System Documentation

> Current project map for humans and coding agents.
> Last reviewed from code: 2026-06-05.

---

## 1. Project Snapshot

**LMView** is a real-time cryptocurrency technical-analysis platform built around
Lambda Architecture:

- Speed layer: live exchange data through Kafka, Flink, Redis Sentinel, and InfluxDB.
- Batch/lakehouse layer: Spark, Iceberg on MinIO, PostgreSQL catalog, and Trino.
- Serving layer: FastAPI REST/WebSocket APIs with Redis/Influx/Trino/PostgreSQL clients.
- Frontend layer: React 19 trading dashboard with charts, drawings, replay, auth, settings, market/news, and Phase 0 AI Helper surfaces.

Latest project release from `docs/CHANGELOG.md`: **0.15.3**.

Repository facts from this audit:

- Branch: `main`.
- FastAPI app metadata version: `0.15.0`.
- Frontend package version: `0.3.0`.
- Compose source of truth: one `docker-compose.yml` with profiles.
- Compose services from static YAML audit: 38 concrete services plus 2 template services.
- Profile counts from static YAML audit: 27 dev services, 34 dev+monitoring+logging services, 36 prod+monitoring+logging services.
- Python tests in source: 254 test functions across 23 files.
- Frontend hook specs in source: 35 `it(...)` specs across 2 files; no frontend test script is currently declared.

This document describes code as it exists now, including places where implementation and intended architecture differ.

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
| Serving | REST, WebSocket, auth, settings, AI foundation APIs | `backend/app.py`, `backend/api/*`, `backend/services/*` |
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
| `dev` | Core local stack with hot reload/local CORS | 27 |
| `monitoring` | Prometheus, Grafana, exporters | +5 |
| `logging` | Loki, Promtail | +2 |
| `prod` | Production FastAPI/Nginx, SSL automation, DuckDNS helper | 36 with monitoring+logging |
| `dont-start` | Compose template services only | 2 templates |

Core service groups:

| Group | Services |
|---|---|
| Kafka | `zookeeper`, `kafka-1`, `kafka-2`, `kafka-3`, `schema-registry` |
| Storage | `redis-master`, `redis-replica-1`, `redis-replica-2`, three Sentinels, `influxdb`, `minio`, `minio-init`, `postgres`, `trino` |
| Processing | `producer`, `flink-jobmanager`, `flink-taskmanager`, `spark-master`, `spark-worker`, `auto-submit-jobs`, `influx-backfill` |
| API/UI | `fastapi-dev` or `fastapi-prod`, `nginx-dev` or `nginx-prod` |
| Orchestration | `dagster-webserver`, `dagster-daemon` |
| Monitoring/logging | `prometheus`, `grafana`, `redis-exporter`, `kafka-exporter`, `node-exporter`, `loki`, `promtail` |
| Production helpers | `certbot-auto`, `duckdns-auto` |

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
| OKX | `src/exchanges/okx/*` | Producer starts it, but WebSocket subscriptions and message parsing need validation before production use. |

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

---

## 6. Kafka Layer

Kafka uses three `apache/kafka:3.9.0` brokers plus a Zookeeper service still present in compose. Topics use 12 partitions by compose defaults and topic helper script intent.

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

Flink configuration:

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

Current speed-layer gaps:

- `crypto_trades` is produced and written to Iceberg by Spark, but there is no Flink hot-cache trade writer.
- `/api/trades/{symbol}` returns ticker-derived price movements, not a true exchange trade tape.
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

Current caveat:

- Aggregator is keyed by `symbol` only and emitted records do not preserve `exchange`. `KeyDBKlineWriter` and `InfluxDBKlineWriter` then default aggregated records to `binance`.

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
| `indicator:latest:{symbol}` | hash | `indicators.py` | Indicator snapshot; no exchange in Redis key |
| `orderbook:{exchange}:{symbol}` | hash | `keydb_depth.py` and REST fallback | TTL 300s for stream data; REST warm cache TTL 30s |
| `klines_cache:{exchange}:{symbol}:{interval}:{limit}` | string | `backend/api/klines.py` | Short API cache, skipped for `endTime` mode |

Important behaviors:

- Candle writes remove an existing sorted-set member at the same timestamp before adding the replacement.
- Backend order book and trade APIs now try exchange-qualified keys first, then Binance/OKX fallback, then legacy keys where applicable.
- Backend `get_redis()` returns a replica client for reads; writes should use `get_redis_master()`.

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
| `indicators` | `indicators.py` | SMA/EMA metrics; writer currently tags exchange as `binance` |

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
| `coin_ticker` | `crypto_ticker` | `s3a://cryptoprice/checkpoints/crypto_ticker_v1` |
| `coin_trades` | `crypto_trades` | `s3a://cryptoprice/checkpoints/crypto_trades_v1` |
| `coin_klines` | `crypto_klines` | `s3a://cryptoprice/checkpoints/crypto_klines_v1` |

Current caveat:

- Avro payloads contain `exchange`, but `src/lakehouse/pipeline.py` table DDLs and stream writes omit `exchange`. Multi-exchange historical analytics need table/schema alignment before exchange-level lakehouse results are trusted.

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

These modules are intended to back market overview, heatmap, ranking, news sentiment, and future AI features, but runtime loading and table freshness must be verified per deployment.

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

Current caveats:

- `assets.py` declares assets and schedules but does not expose a Dagster `Definitions` object.
- `assets.py` imports `news.multi_source_scraper.MultiSourceNewsScraper`, but current `src/news/` contains `enhanced_scraper.py` and `sentiment_analyzer.py`; validate Dagster code-location loading before relying on schedules.

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
| WS | `/api` + `/stream/all` | Redis | Single all-timeframe WebSocket |
| GET | `/api/orderbook/{symbol}` | Redis, ticker-derived, Binance REST fallback | Includes source/freshness metadata |
| GET | `/api/orderbook/{symbol}/summary` | Order book endpoint | Compact AI context summary |
| GET | `/api/trades/{symbol}` | Redis ticker history | Ticker-derived price ticks, not true trades |
| GET | `/api/trades/{symbol}/summary` | Redis ticker history | Compact AI context summary |
| GET | `/api/symbols` | Redis scan | Supports legacy and exchange-qualified ticker keys |
| GET | `/api/indicators/supported` | Static catalog | Supported backend indicator names |
| GET | `/api/indicators/{symbol}` | Redis | Indicator snapshot |
| GET | `/api/indicators/{symbol}/summary` | Redis | Compact AI context summary |
| GET | `/api/market/overview` | Placeholder/default object | Includes `metadata.is_placeholder = true` |
| GET | `/api/market/heatmap` | Trino gold helpers | Route from `market_overview.py` |
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
| GET | `/api/ai/health` | PostgreSQL health check | No LLM call |
| POST | `/api/ai/chat` | PostgreSQL + mock service | Auth required; deterministic Phase 0 response |
| GET/POST | `/api/ai/sessions` | PostgreSQL | Session list/create |
| GET | `/api/ai/sessions/{session_id}/messages` | PostgreSQL | User-owned session messages |
| POST | `/api/ai/chart-context` | PostgreSQL | Store chart context snapshot |
| POST | `/api/ai/chart-actions/validate` | Validator | Validate proposed chart actions only |
| POST | `/api/ai/chart-actions/record` | Acknowledgement | Records approval/execution state shape |
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

### Background Tasks

| Task | File | Interval | Notes |
|---|---|---:|---|
| Market fetcher | `backend/tasks/market_fetcher.py` | 300s | Queries Trino `coin_ticker` and updates in-memory market cache |
| News fetcher | `backend/tasks/news_fetcher.py` | 300s | Uses `EnhancedMultiSourceScraper`, VADER sentiment, in-memory news cache |

In-memory caches reset on FastAPI restart. Production hardening should move these caches to Redis or lakehouse-backed queries.

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
- Live chart uses the all-timeframe WebSocket helper (`subscribeAllTimeframes`).
- Legacy single-candle WebSocket helper still exists in service code but should be treated as stale unless backend route support is added.

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
- Backend `/api/ai/*` endpoints persist sessions/messages/snapshots and return deterministic Phase 0 responses.
- Local LMView Help mode exists for mock/unavailable behavior.
- There is no production LLM, RAG, inference model, or autonomous chart execution yet.

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

Grafana dashboards in `config/grafana/dashboards`: **11** JSON dashboards.

Alerting rules in `config/grafana/provisioning/alerting/rules.yml`: **8** rules across Flink, Kafka, API, and system health.

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
| `tests/unit/` | Constants, models, auth/AI, mappers, candle service |
| `tests/integration/` | FastAPI endpoints with mocked dependencies |
| `tests/e2e/` | App route registration and OpenAPI checks |
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

If local host has no `python` shim, use `python3` or the project virtualenv explicitly.

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run build
```

Current frontend hook specs exist under `frontend/src/hooks/__tests__`, but `frontend/package.json` has no `test` script and no explicit Jest/Vitest dependency.

Known test caveats from this audit:

- Focused auth/AI unit tests passed with `python3`: 54 tests.
- E2E collection on the inspected host could not run because host Python lacks project dependency `redis`.
- Some e2e expectations appear stale relative to current FastAPI metadata and WebSocket route shape.

---

## 15. AI/ML Extension Points

Current AI state is **Phase 0 foundation**, not production model inference:

- Authenticated AI API routes exist.
- Chat sessions, messages, chart snapshots, and action records are persisted in PostgreSQL.
- Scope gate and chart-action validator are deterministic local services.
- Responses are deterministic mock responses from `ai_mock_service.py`.
- Frontend AI Helper and settings surfaces are wired.

Not implemented yet:

- Real LLM provider integration.
- RAG/knowledge retrieval.
- Autonomous chart action execution.
- Model training/inference service.
- Model artifact storage and observability.

Recommended future pattern:

1. Define data contract first: input window, target, prediction horizon, latency, freshness.
2. Store durable training data and labels in Iceberg.
3. Keep online features reproducible from offline feature logic.
4. Version model artifacts and model outputs.
5. Add observability for freshness, latency, null rate, drift, and model version.
6. Keep inference boundaries explicit: backend service for API logic, separate `src/ml` or service module for training/inference.

---

## 16. Current Caveats and Gotchas

High-impact implementation caveats:

1. **OKX is experimental.** Producer starts OKX, but subscription frames and parser behavior need verification.
2. **Exchange propagation is incomplete.** Ticker paths are exchange-aware; kline aggregation, depth processing, indicators, and lakehouse DDLs still drop/default exchange in places.
3. **True hot trade cache is absent.** `crypto_trades` goes to Spark/Iceberg, but `/api/trades/{symbol}` is ticker-derived.
4. **Market overview placeholder.** `/api/market/overview` returns zero/default data with placeholder metadata; heatmap/rankings query Trino helpers.
5. **Dagster loading needs repair/verification.** `assets.py` lacks `Definitions` and imports a missing scraper module path.
6. **Single active WebSocket shape.** Frontend chart uses all-timeframe streaming; legacy single-candle helper is stale.
7. **PostgreSQL health is separate.** `/api/health` checks Redis, InfluxDB, and Trino; `/api/ai/health` reports PostgreSQL readiness for AI foundation.
8. **Tests need dependency alignment.** Full local pytest requires project dependencies; e2e route expectations need refresh.

General gotchas:

1. Backend API timestamps are milliseconds; lightweight-charts expects seconds.
2. UI labels may be uppercase; backend interval keys must be lowercase.
3. Candle sorted-set dedup must remove the old score before `ZADD`.
4. Ticker enrichment should only override live aggregated candles when ticker is newer than source candles.
5. Influx scroll-left mode must use absolute `range(start: RFC3339, stop: RFC3339)`.
6. PyFlink writer classes should read worker-specific environment values in `open()` when serialization requires it.
7. Schema changes require coordinated producer, Flink, Spark, backend, frontend, and tests.
8. Dev Nginx uses plain HTTP on port 80. Prod uses HTTPS on 443 with certbot automation and a fallback certificate path.
9. Backend/producer/backfill Dockerfiles use Python 3.11. Do not require Python 3.12+ without validating PyFlink/Spark compatibility.
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
- Services that accept connections need health checks.
- Services need memory limits where Compose supports them.
- Validate Compose changes with profile-specific config commands.

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

Document version: **5.0**
Maintained by: human contributors and AI coding agents.
