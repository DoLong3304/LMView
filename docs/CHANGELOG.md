# Changelog — LMView

All notable changes to this project are documented in this file.
This log is maintained by AI agents and human contributors to track project evolution.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [0.14.1] - 2026-05-28 - Frontend Chart Controls and Right Panel UI

### Added

- **Theme support** - Added light and dark theme support through shared CSS tokens, persisted the selected mode in local storage, and refreshed chart colors when the mode changes.
- **Frontend client caching** - Added frontend-side caching for stable symbols, chart history, market overview, movers, news, and short-lived live market snapshots.
- **Chart type selector** - Wired candlestick, bar, line, and area renderers while keeping chart modes synchronized for replay and drawing coordinates.
- **Chart export** - Rebuilt chart export to include chart canvases, visible price/time axes, latest OHLCV metadata, selected chart type, and SVG user drawings.
- **Indicators library** - Expanded the chart indicators panel with TradingView-style search, grouped Trend/Momentum/Volatility/Volume categories, active-state toggles, and client-side calculations for Bollinger Bands, VWAP, Volume MA, MACD, Stochastic, ATR, Ichimoku, Supertrend, and Parabolic SAR.
- **AI assistant panel** - Reworked the right-panel AI Helper into a Copilot-style chat workspace with a compact header, chart context chips, scrollable conversation, suggested prompts, and a fixed composer using mock responses until a backend AI endpoint is available.

### Changed

- **Header shell** - Reworked the header around LMView branding, chart/markets navigation, theme/settings/user controls, and chart-only controls.
- **Developer UI** - Hid developer-facing UI indicators from the header, including the data source badge and system health card, behind a disabled developer-tools flag.
- **App responsiveness** - Improved app shell responsiveness by making the drawing toolbar and overview panel collapsible, defaulting secondary panels closed on compact screens, and keeping the chart area as the primary view.
- **Chart controls** - Replaced the full-width header timeframe row with a compact dropdown in the chart control bar, preserving lowercase timeframe keys for service/API calls while displaying uppercase long-interval labels in the UI.
- **Chart header toolbar** - Consolidated the chart symbol selector, timeframe dropdown, Indicators, History, Export Chart, chart-type buttons, zoom/fullscreen controls, and price/change readout onto a single non-wrapping toolbar row.
- **Chart zoom controls** - Kept Zoom In, Zoom Out, and Fullscreen controls in the primary one-line chart toolbar.
- **Chart action row** - Moved chart-specific controls out of the app header into a dedicated chart toolbar row and deduplicated the chart-area coin selector while preserving current-symbol rendering state.
- **Chart toolbar grouping** - Refined the chart action row into compact timeframe, action, and icon-tool groups with consistent dark-theme button sizing, radius, hover, and active states.
- **Chart tab strip** - Removed the old chart content tab strip so the chart remains the default view, with timeframe and chart-type controls handled from the header and chart toolbar.
- **Right panel** - Reduced the default desktop width and compacted overview, watchlist, order book, and recent trade spacing so the main chart keeps more usable screen area.
- **Right panel tabs** - Split the right panel into top-level Overview and AI Helper tabs, keeping market panels under Overview and adding a dark-theme AI placeholder without backend/API calls.
- **Overview panel placement** - Repositioned Order Book and Recent Trades into the right Overview panel beside Watchlist, using horizontal tabs for all three views.
- **Overview panel controls** - Tightened the Watchlist, Order Book, and Recent Trades segmented buttons to avoid horizontal overflow in the compact right panel.
- **Drawing toolbar restore** - Restored the stable left drawing bar layout from the pre-workspace commit, removing the experimental chart-edge handle, absolute overlay toolbar, and flyout registry from the rendered UI.
- **Drawing deletion** - Removed Delete Selected from the left drawing bar while keeping Delete All guarded by a confirmation modal for the current symbol/timeframe.
- **Drawing lock** - Kept locked-drawing edit/delete guards when using drawing selection and deletion flows.
- **Indicators control** - Highlighted the chart Indicators button and expanded the existing indicator panel to expose SMA20, SMA50, EMA12, and EMA26 controls.
- **News filters** - Scaled down the Markets & News search/filter controls to reduce header height while preserving existing filtering behavior.
- **Markets & News** - Improved Markets & News with 10-item pagination, list/grid view toggle, better scroll containment, and full-card external article links.
- **Symbol metadata** - Reworked symbol metadata to always expose symbol, name, and icon fields, with a bundled default icon when exchange or CoinGecko metadata is missing.
- **Mock market data** - Expanded mock ticker coverage so mock-mode watchlist, order book, trades, and chart candles line up with the bundled mock data generator.
- **Frontend preview** - Built and relaunched a frontend-only Vite preview from a mock-mode production bundle during frontend validation.

### Fixed

- **Drawing toolbar restore** - Restored the left drawing bar from the stable pre-workspace layout, removed the new flyout registry from the rendered sidebar, and kept fixed-height top-aligned buttons so fullscreen no longer stretches tool spacing.
- **Drawing toolbar delete actions** - Removed the Delete Selected toolbar button from drawing toolbars while keeping Delete All Drawings behind the existing confirmation modal.
- **Left drawing bar layout** - Moved the left drawing bar into the chart body as a floating fixed-size toolbar with an iPhone-style collapse handle, separating it from the top chart toolbar and preserving spacing in fullscreen.
- **Chart toolbar grouping** - Placed the live price/change indicator beside the symbol selector and pushed timeframe, indicators, history, export, chart type, and zoom controls into the right-side toolbar group.
- **Chart toolbar overflow** - Fixed chart action row overflow by letting control groups wrap inside the chart container and anchoring Indicators/History dropdowns from the left with viewport-bounded widths.
- **Chart symbol/timeframe controls** - Restored a single chart `MarketSelector` in the chart header and left-anchored the timeframe dropdown inside the chart toolbar container to prevent left-side overflow.
- **Chart autoscale reset** - Improved chart autoscale reset so it restores the intended initial candle window and price scaling instead of dumping the full loaded history into view.
- **Drawing selection** - Fixed drawing selection and delete-selected by letting cursor mode hit-test drawings and by recording toolbar deletes in the drawing command history.
- **Chart zoom/fullscreen layout** - Kept chart toolbar rows and drawing controls at fixed UI dimensions while zooming or entering/exiting fullscreen, resizing only the chart viewport.
- **Drawing tool rendering** - Filled in visible rendering and hit-testing for text, rectangle, circle, triangle, ruler, horizontal line, and trendline drawing tools using data-space anchors.
- **Replay mode startup** - Fixed replay mode startup so it begins from the selected candle, hides future candles, blocks live refresh races, and uses correct playback speed values.
- **Chart overlay navigation** - Fixed chart time navigation while drawing/replay overlays are active by forwarding wheel zoom/scroll and adding overlay-level pan handling for captured pointer states.

---

## [0.14.0] - 2026-05-22 - Frontend Structure Refactor

### Changed

- **Frontend folder structure** - Reorganized `frontend/src` into standard Vite React TypeScript folders, including `@types`, `constants`, `data`, `features`, `components/layout`, `components/ui`, and `routes`.
- **Frontend services** - Centralized API helpers, environment constants, timeframe constants, market/news data services, and health checks outside React components.
- **UI shell** - Merged the top toolbar behavior into the canonical `Header` component and removed redundant toolbar/replay/watchlist/news files.
- **Chart feature** - Flattened `features/chart` by removing the redundant nested `components/chart` directories and adding a concise feature barrel export.
- **Styling and i18n** - Moved theme tokens into `index.css`, removed the old theme module, and expanded translations for the refactored market/news/header UI.
- **Project docs** - Updated `docs/SYSTEM.md` and `AGENTS.md` to match the new frontend folder structure and hot spot paths.

---

## [0.13.1] — 2026-05-22 — Bug Fixes: Data Pipeline & Backend APIs

### Fixed

- **Kafka Topics** — Resolved `Unrecognized partition` errors in the Python producer by recreating `crypto_ticker`, `crypto_klines`, `crypto_trades`, and `crypto_depth` topics with the correct 12 partitions. Data ingestion is now stable.
- **Orderbook API** — Fixed an HTTP 500 `ReadOnlyError` in `/api/orderbook/{symbol}` by routing the fallback cache expiration write (`expire`) to the Redis Master node instead of a read-only Sentinel replica.
- **Exchange Fallback Logic** — Updated `/api/trades` and `/api/orderbook` to correctly parse new exchange-aware Redis keys. Implemented Binance-first lookup with automatic fallback to OKX (and then legacy keys) to fully utilize OKX as a redundant backup source.

---

## [0.13.0] — 2026-05-22 — Dev HTTP / Prod HTTPS Nginx Routing

### Changed

- **Nginx dev mode** — Switched from self-signed HTTPS to plain HTTP (port 80 only). No more browser certificate warnings in development.
- **Nginx prod mode** — HTTPS via certbot with any domain (DuckDNS, custom, etc.), not limited to DuckDNS. Self-signed cert still used as fallback until certbot issues a real certificate.
- **Nginx config split** — Single `nginx.conf` replaced with `nginx-dev.conf` (HTTP-only) and `nginx-prod.conf` (HTTPS). Entrypoint selects config via `NGINX_MODE` env var.
- **`init_certbot.sh`** — Now domain-agnostic; DuckDNS auto-detection is optional, not assumed. Only starts `duckdns-auto` if `DUCKDNS_TOKEN` is configured.
- **`certbot_auto.sh`** — Removed DuckDNS-specific sentinel domain check.
- **`.env.example`** — Generalized HTTPS automation section; `CERTBOT_DOMAIN` default changed from DuckDNS to `example.com`.
- **`docker-compose.yml`** — `nginx-dev` exposes port 80 only; `nginx-prod` exposes 80+443 with letsencrypt/certbot volumes. Ports and volumes moved from base template to concrete services.

---

## [0.12.3] — 2026-05-21 — Charting Library Upgrade

### Changed

- **Dependencies** — Upgraded `lightweight-charts` to `5.2.0` in `frontend/package.json`.

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

-->
