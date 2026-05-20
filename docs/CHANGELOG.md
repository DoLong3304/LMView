# Changelog — LMView

All notable changes to this project are documented in this file.
This log is maintained by AI agents and human contributors to track project evolution.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.12.2] — 2026-05-20 — Frontend Mock Data Isolation & Service Refactor

### Added
- **Mock Data Enhancement** — Added `NewsItem` type and dynamic mock data simulation for order books, trades, and tickers to simulate real-time data flow on frontend.
- **Mock Mode Toggle** — Implemented `VITE_DATA_SOURCE` env variable to toggle between 'mock' and 'api' data sources.
- **UI Mode Indicator** — Added visual badge in `Header.tsx` indicating current data source (MOCK vs API).

### Changed
- **Mock Data Refactor** — Extracted all inline mock data generation out of `marketDataService.ts` and `MarketNews.tsx` into a dedicated `mock/mockDataGenerator.ts` file. 
- **Market Overview Service** — Created `marketOverviewService.ts` to act as a controller for news, gainers, losers, and overview metrics, smoothly switching between API and mock data without clustering component logic.

### Fixed
- **TypeScript Overlap Error** — Resolved type comparison error for `DATA_SOURCE` constant in `marketDataService.ts`.

---

## [0.12.1] — 2026-05-19 — Integration Tests & API Routing

### Changed
- **Integration Test Suite** — Modernized test infrastructure to support Redis Sentinel HA by replacing legacy `get_redis` mocks with `get_redis_master`/`get_redis_replica`. Added global fixtures to mock FastAPI background tasks during testing.
- **API Routing** — Reordered FastAPI router inclusions in `backend/app.py` to prioritize new `market_overview` routes over legacy `market` overlapping routes.

### Added
- **API Tests** — Added mandatory integration tests for `market_overview` (`/api/market/overview`, `/api/market/heatmap`, `/api/market/rankings`) and `news` (`/api/news/latest`, `/api/news/trending`, `/api/news/search`) endpoints.

---

## [0.12.0] — 2026-05-19 — Market Overview & News Features (merged from `feature/viet-work`)

### Added
- **Market Overview API** — `backend/api/market_overview.py` and `backend/services/heatmap_service.py` to serve comprehensive market aggregations and heatmap data via Trino.
- **News API** — Background fetcher and endpoints for aggregating sentiment-driven news.
- **Background Tasks** — `market_fetcher.py` and `news_fetcher.py` integrated into FastAPI lifespan to continuously fetch necessary external data.
- **Frontend Components** — Added `LeftSidebar`, `RightPanel`, `TopToolbar`, `MarketOverviewPage`, `NewsPageRedesigned`, and `MarketNews` for an enriched UI.
- **Spark Metrics** — JMX metrics exporting via `metrics.properties` for Spark clusters.
- **Redis Monitoring** — Added `redis-exporter` to the monitoring stack.

### Changed
- **Integration Test Suite** — Modernized test infrastructure to support Redis Sentinel HA by replacing legacy `get_redis` mocks with `get_redis_master`/`get_redis_replica`. Added global fixtures to mock FastAPI background tasks during testing.
- **API Routing** — Reordered FastAPI router inclusions in `backend/app.py` to prioritize new `market_overview` routes over legacy `market` overlapping routes.
- **Dagster** — Version upgraded to `1.8.10`.
- **Nginx** — Version upgraded to `1.31.0`.
- **Certbot** — Version upgraded to `v5.6.0`.
- **Trino** — Added JMX javaagent opts for Prometheus scraping.

### Added
- **API Tests** — Added mandatory integration tests for `market_overview` (`/api/market/overview`, `/api/market/heatmap`, `/api/market/rankings`) and `news` (`/api/news/latest`, `/api/news/trending`, `/api/news/search`) endpoints.

---

## [0.11.0] — 2026-05-16 — Monitoring & Logging Nginx Routing

### Added
- **Nginx reverse proxy for monitoring** — Grafana (`/grafana/`), Prometheus (`/prometheus/`), Loki (`/loki/`) routed through nginx
- **Basic Auth for Prometheus/Loki** — htpasswd generated at container startup from `MONITORING_USER`/`MONITORING_PASSWORD` env vars (default: admin/admin)
- **Grafana WebSocket proxy** — `/grafana/api/live/` for live dashboard updates
- **Rate limiting** — `monitoring_limit` zone (10r/s per IP) applied to all monitoring endpoints

### Changed
- **Grafana subpath** — Configured `GF_SERVER_SERVE_FROM_SUB_PATH=true` with `GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s/grafana/`
- **Prometheus subpath** — Added `--web.external-url=/prometheus/` and `--web.route-prefix=/prometheus/`
- **Grafana Prometheus datasource** — Updated URL to `http://prometheus:9090/prometheus`
- **Nginx Dockerfile** — Added `apache2-utils` for htpasswd generation
- **`.env.example`** — Added `MONITORING_USER`, `MONITORING_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`

### Agent
- Agent: Gemini (Antigravity)
- Files modified: 6 (nginx.conf, Dockerfile, entrypoint.sh, docker-compose.yml, .env.example, datasources.yml)

---

## [0.10.0] — 2026-05-16

### Changed
- **Documentation system rewrite** — Replaced all project documentation with a new standardized system:
  - `docs/SYSTEM.md` — Complete system documentation (architecture, data flow, tech stack, setup, testing)
  - `docs/CHANGELOG.md` — Structured changelog (this file), migrated from `docs/TRACKING.md`
  - `docs/AGENTS.md` — AI agent coding instructions following the agents.md open standard
  - `README.md` — User-facing project overview following banesullivan/README template
- **Project renamed** from "Lambda Architecture for TradingView-Style Platform" to **LMView**
- **Documentation language** standardized to English (previously mixed Vietnamese/English)

---

## [0.9.0] — 2026-05-14 — High Availability Infrastructure

### Changed
- **Monitoring stack integration** — Merged Flink infrastructure refactor with monitoring/logging stack
- **Redis Sentinel entrypoint** — Fixed entrypoint scripts for correct Sentinel initialization
- **Node-exporter volumes** — Corrected volume mount paths for host metrics collection
- **Grafana provisioning** — Fixed rule hierarchy in provisioning configuration
- **Configuration types** — Resolved file type mismatches in monitoring configs

---

## [0.8.0] — 2026-05-09 — HA Architecture Migration

### Changed
- **Kafka HA** — Migrated from single Kafka node to 3-node KRaft cluster (`kafka-1`, `kafka-2`, `kafka-3`) with replication factor 3
- **Redis Sentinel HA** — Replaced standalone KeyDB with Redis cluster: 1 Master, 2 Replicas, 3 Sentinels
- **Backend Redis client** — Implemented `RedisSentinelManager` in `backend/core/redis_sentinel.py` with auto-discovery, failover, and read/write splitting

### Known Issues
- PyFlink writers still use `keydb_` prefix in filenames (e.g., `keydb_ticker.py`, `KeyDBKlineWriter`) while connections use Sentinel config
- `src/common/config.py` retains default `REDIS_HOST = "keydb"`, overridden by HA environment variables

---

## [0.7.0] — 2026-05-05 — Multi-Timeframe Candles & Historical Mode

### Added
- **Historical mode** — Full date range picker (`DateRangePicker.tsx`) with request ID tracking to prevent race conditions
- **Interval helpers** — `normalize_interval()`, `interval_to_seconds()`, `interval_to_ms()` in `candle_service.py`
- **Integration tests** — 4 new tests for candle merge quality and staleness checks (`test_candle_idempotency.py`)
- **Unit tests** — 14 new tests covering normalization, aggregation, and merge logic

### Fixed
- **Aggregate function (CRITICAL)** — Now sorts by timestamp before determining open/close. Previously used input order which produced wrong results with out-of-order data.
- **Ticker enrichment staleness** — Backend now verifies ticker freshness against sub-candle data before enriching
- **Interval normalization** — Frontend normalizes uppercase intervals (`1H` → `1h`) before all API calls

---

## [0.6.0] — 2026-05-02 — Comprehensive Test Suite

### Added
- **161 total tests** across 5 categories:
  - Unit: 80 tests (constants, binance mappers/client, models, candle service)
  - Integration: 39 tests (health, ticker, symbols, trades, indicators, klines, historical APIs)
  - Security: 17 tests (SQL injection, XSS, path traversal, CORS, oversized queries)
  - Performance: 9 benchmarks (aggregation, merging, validation with time limits)
  - E2E: 6 tests (route registration, OpenAPI schema, docs endpoint)
- **Test infrastructure** — `tests/integration/`, `tests/e2e/`, `tests/performance/` packages

---

## [0.5.0] — 2026-04-28 — Infrastructure & Pipeline Restoration

### Fixed
- **Producer image** — Downgraded from Python 3.14-slim to 3.11-slim (fastavro C-extension compatibility)
- **Nginx port conflict** — Removed duplicate port 3000 binding between dagster-webserver and nginx
- **Binance WebSocket** — Switched `!ticker@arr` to `!miniTicker@arr` (lighter payload, no timeout)
- **Flink module resolution** — Fixed `--pyFiles /app/src` in job submission script

---

## [0.4.0] — 2026-04-28 — Frontend TypeScript Migration

### Changed
- **Complete TypeScript migration** — All 27 frontend files migrated from `.jsx`/`.js` to `.tsx`/`.ts`
- **React 18 → 19** upgrade
- **Type system** — 18 shared TypeScript interfaces in `types/index.ts`
- **Error handling** — Centralized `AppError` hierarchy + `useApiCall` hook + `ToastProvider`
- **Symbol metadata** — Dynamic CoinGecko API + 24h localStorage cache + fallback data (~90 symbols)
- **i18n** — ~130 translation keys (English + Vietnamese), all hardcoded strings replaced
- **Nginx** — Updated asset caching from `/static/` to `/assets/` (Vite output path)

---

## [0.3.0] — 2026-04-25 — Data Processing Layer Refactoring

### Changed
- **Exchange abstraction** — `ExchangeClient` base class + `BinanceClient` implementation in `src/exchanges/`
- **Shared infrastructure** — Centralized `src/common/` (config, kafka_client, avro_serializer, logging)
- **Producer rewrite** — 632-line monolith → ~250-line exchange-agnostic orchestrator
- **Flink pipeline split** — 996-line monolith → `pipeline.py` + 7 individual writer modules
- **Batch jobs** — Renamed and refactored maintenance/backfill jobs

---

## [0.2.0] — 2026-04-25 — Full Project Refactoring

### Changed
- **Backend MVC** — Migrated `serving/` → `backend/` with `api/`, `services/`, `models/`, `core/` structure
- **Pydantic models** — Created response models for candle, ticker, health endpoints
- **Shared service** — `candle_service.py` (280 lines) for all OHLCV business logic
- **Dev/Prod switching** — `docker-compose.override.yml` (dev) + `docker-compose.prod.yml` (prod) + Makefile
- **Docker optimization** — Memory limits on all 14 services, pinned Python dependencies
- **Security** — Nginx rate limiting (30r/s API, 5r/s WS), security headers (HSTS, X-Frame-Options, etc.)

### Added
- **Testing framework** — pytest with 40 initial tests (unit, model, security)
- **Vite migration** — CRA → Vite, all 21 components renamed to `.jsx`
- **Backend Python** — Upgraded to Python 3.14-slim (later reverted to 3.11)

---

## [0.1.0] — 2026-04-25 — Initial Documentation

### Added
- **TRACKING.md** — AI assistant working document
- **DOCUMENTATION.md** — Technical documentation (Vietnamese)
- **.gitignore** — Updated exclusion list

---

<!-- TEMPLATE FOR NEW ENTRIES:

## [X.Y.Z] — YYYY-MM-DD — Title

### Added
- **Feature name** — Description of what was added

### Changed
- **Component** — Description of what changed and why

### Fixed
- **Bug description** — What was wrong and how it was fixed

### Removed
- **Component** — What was removed and why

### Known Issues
- Description of any remaining issues

### Agent
- Agent: [Agent name/model]
- Session duration: [approximate]
- Files modified: [count]

-->
