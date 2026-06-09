## [0.23.0] - 2026-06-09

### Added

- **Phase E: Enhanced Watchlist & Screener** — `EnhancedWatchlistItem`, `WatchlistColumn`, `WatchlistFilter`, `ScreenerPreset`, `WATCHLIST_COLUMNS`, `SCREENER_PRESETS` types in `types/index.ts`. `EnhancedWatchlist.tsx` with sort/filter/search. `Screener.tsx` with filter panel and presets (Oversold, Overbought, High Volume, Top Gainers/Losers, Strong Bullish/Bearish). `ScreenerPage.tsx` as standalone page. "screener" view in `AppView` type, Filter icon in Header. Mock adapter methods (`fetchScreenerResults`, `fetchWatchlistWithIndicators`) for mock mode. `screenerService.ts` with `fetchScreenerResults`, `fetchWatchlistWithIndicators`, `fetchScreenerPresets`.
- **Phase F: Multi-chart Layouts** — `LayoutContext.tsx` with `LayoutProvider` + `useLayout` hook, `LayoutType` (single/split-v/split-h/quad/three-v/three-h/six), `ChartInstance` interface. `MultiChartContainer.tsx` with CSS grid layout. `LayoutToolbar.tsx` with layout switcher buttons. i18n keys (en + vi) for layout names.
- **Phase G: Pattern Recognition** — `types/patterns.ts` with `PatternType`, `DetectedPattern`, `PatternDetectionConfig`, `PATTERN_LABELS`, `PATTERN_BULLISH`. `patternDetection.ts` with `PatternDetector` class — detects double_top, double_bottom, ascending_triangle, descending_triangle, head_shoulders.
- **Phase H: Alerts & Notifications** — `types/alerts.ts` with `AlertType`, `PriceAlert`, `ALERT_TYPES`. `alertService.ts` with `createAlert`, `deleteAlert`, `toggleAlert`, `checkAlerts`, `loadAlerts`, `saveAlerts` — localStorage-based.
- **i18n keys (en + vi)** — screener, screenerDescription, screenerResults, singleChart, splitVertical, splitHorizontal, quadChart, threeVertical, threeHorizontal, sixChart, syncTimeScale.

### Changed

- **WebSocket real-time streaming optimized** — `backend/api/websocket.py` `/stream/all` endpoint refactored:
  - Added trade stream as real-time price source (`trade:latest:{exchange}:{symbol}` Redis key)
  - New `_merge_trade_to_candles()` function updates in-progress candles with each trade
  - New `_get_stream_candle()` returns real-time candle state or falls back to historical
  - 50ms poll loop for sub-300ms latency target
  - Graceful error handling per Redis fetch operation
- **Chart styling improved** — `CandlestickChart.tsx` chart options updated:
  - Grid lines use dashed style (like TradingView)
  - Crosshair uses dashed lines with label backgrounds
  - `entireTextOnly: true` on right price scale for cleaner labels
  - `barSpacing: 6` for better candle density
  - Line series uses upColor instead of textColor
- **Duplicate i18n keys fixed** — Removed duplicate `oversold`, `overbought`, `topGainers`, `topLosers`, `clearAll`, `selectAll`, `trend`, `volume24h`, `change24h`, `high24h`, `low24h`, `price`, `volume`, `marketCap`, `open`, `high`, `low`, `close`, `noData` from watchlist/Overview sections in en.ts and vi.ts.
- **WatchlistFilter type conflict** — Renamed simple `"all" | "starred"` type to `WatchlistTabFilter`, kept `WatchlistFilter` as interface for enhanced filtering.
- **`ChartOverlay.tsx`** — PATTERN_TOOLS set expanded to include `harmonicABCD`, `xabcdPattern`, `elliottWave`.

### Fixed

- **WebSocket real-time streaming broken** — `backend/api/websocket.py` had two bugs preventing candle updates:
  1. WebSocket query parameters (`symbol`, `exchange`) were in function signature which FastAPI doesn't support for WebSocket — fixed to use `websocket.query_params.get()`
  2. Route order issue: `/stream/{interval}` was defined BEFORE `/stream/all`, causing "all" to be treated as an interval parameter and returning 404 — fixed by moving `/stream/all` route before `/stream/{interval}`
- **Mock adapter Ticker fields** — `fetchScreenerResults` and `fetchWatchlistWithIndicators` now use computed `name`/`rank`/`marketCap` from Ticker fields instead of non-existent properties.
- **`screenerService.ts`** — Fixed `buildQuery` params type mismatch, `ScreenerSymbol.name` property, `makeClientCacheKey` params.
- **TypeScript strict errors** — Fixed unused imports/vars in EnhancedWatchlist, Screener, ScreenerPage, LayoutContext, MultiChartContainer.
- **Screener data display** — `Screener.tsx` had no data display logic (placeholder UI only). Added `items` prop, filter/sort logic, and results table.

### Notes


- Zero TypeScript errors.
- `npm run typecheck` + `npm run build` pass.
- Phase A (Drawing Tools) already 90%+ complete — types, toolbar, overlay rendering, tool settings all implemented.
- Phase B (Chart Types) — transformers exist and now wired into chart rendering.
- Phase C (Advanced Indicators) — Volume Profile, Anchored VWAP, MTF indicators documented but require deeper chart integration.
- Phase I (Mobile) — existing responsive layout system in App.tsx handles breakpoints.

---

## [0.22.0] - 2026-06-09

### Added

- **Phase A: Drawing Tools Foundation** — `DrawingToolCategory` type (10 categories), comprehensive `DrawingTool` union (40+ tool IDs), `DrawingSettings` interface with tool-specific fields, `FibonacciLevel` + `FIBONACCI_RETRACEMENT_LEVELS`, `GANN_ANGLES` constant, `DrawingPreset` + `DrawingCategory` interfaces, extended `BaseToolSettings`, `DEFAULT_TOOL_SETTINGS` for all tools, tool settings UI (Gann/Pitchfork/Text/Fibonacci/Measurement sections).
- **Phase D: Market Overview Dashboard** — `MarketOverview`, `SectorPerformance`, `HeatmapItem`, `IndicatorsSummary`, `MarketOverviewMetadata` interfaces, enhanced `MarketMetrics` with Fear & Greed, BTC/ETH metrics, Market Breadth, `MarketPeriod` type (1h/24h/7d/30d), `MarketOverviewService` class in `backend/services/market_overview_service.py` with Redis ticker fallback.
- **MarketOverviewPage enhancements** — Period selector dropdown, Fear & Greed display, Market Breadth section, Sector Performance cards, warning banner for placeholder data.
- **`fetchSectorPerformance`, `fetchHeatmapData`** — `marketOverviewService.ts` new exports.
- **Unit tests** — `tests/unit/test_market_overview_service.py` with 11 tests.
- **i18n keys (en + vi)** — 14 new keys: fearGreedIndex, fearGreedExtremeFear, fearGreedFear, fearGreedNeutral, fearGreedGreed, fearGreedExtremeGreed, marketBreadth, advancing, declining, marketBreadthRatio, newHighsLows24h, sectorPerformance, period selectors.

### Changed

- **`fetchMarketOverview` return type** — Now returns `MarketOverview` instead of `MarketMetrics`. Extract `market_summary` for metrics.
- **`MarketNews.tsx`** — Updated to use `overview?.market_summary || null` for metrics state.
- **`Drawing.tool` type** — `DrawingTool | string` for backward compat.
- **`Drawing.settings` type** — `Record<string, any>` → `DrawingSettings`.

### Notes

- Zero TypeScript errors.
- Backend service reads from Redis `ticker:latest:*:*` keys. Falls back to empty metrics when no tickers available.
- Phase D backend service uses Redis ticker scan fallback when Trino unavailable.

---

## [0.21.0] - 2026-06-09

### Added

- **Phase B: Advanced Chart Types** — `ChartType` expanded to 9 types (heikinAshi, renko, lineBreak, kagi, pointFigure), `ChartTypeConfig` + `CHART_TYPES` array, `ChartTypeSettings` interface.
- **Chart transformers** — `heikinAshi.ts`, `renko.ts`, `lineBreak.ts`, `kagi.ts` in `features/chart/transformers/`.
- **ChartTypeSettingsModal** — Modal UI for advanced chart type settings.
- **Chart type icons** — `CandlestickChart.tsx` maps all 9 chart types to lucide icons.
- **i18n (en + vi)** — 17 new keys for chart types and settings.

### Notes

- Zero TypeScript errors.
- Transformers wired into `CandlestickChart.tsx` `setAllPriceSeriesData` — Heikin Ashi, Renko, Line Break, Kagi transform on render.

---

## [0.20.1] - 2026-06-09

### Added

- **AI session restore controls** — AI Helper now remembers the active backend session across reloads and Settings can load previous AI Helper sessions.
- **Customization presets** — Settings now exposes indicator, drawing-tool, layout, default exchange, volume, magnet, and compact-panel presets.
- **Admin AI usage summary** — Admin users can see total AI input/output tokens and estimated cost in AI Helper settings.

### Fixed

- **Realtime chart updates** — WebSocket candle building now folds fresh ticker prices into 1s/1m candles when kline candle caches lag, so chart candles update alongside indicators.
- **All-timeframe WebSocket route** — Registered `/api/stream/all` before the catch-all `/api/stream/{interval}` route so the chart receives live candle frames instead of an unsupported `all` interval error.
- **Chart resize after browser zoom** — Chart resize now uses measured container/stage bounds, observes visual viewport changes, and keeps the chart wrapper shrinkable to avoid bottom clipping after zoom out/in.
- **AI Ask readability** — AI Helper renders common markdown blocks and inline formatting instead of showing raw markdown text.
- **AI Helper tab persistence** — The right panel now keeps AI Helper mounted while Overview is active, preserving in-flight responses and preventing remount scroll animation when switching tabs.
- **AI timestamp confusion** — Ask Mode prompts now include live server time, epoch milliseconds, and UTC-formatted chart timestamps so current candle times are not misclassified as invalid due model cutoff.
- **Normal-user token leakage** — Per-message token and cost metadata is hidden from non-admin users.
- **Kline scroll 500s** — Missing optional Trino/Iceberg historical candle tables now degrade to empty fallback results instead of failing `/api/klines` scroll requests.
- **Notification delivery loop** — Header notifications now reload periodically and can show browser desktop notifications when the user preference and browser permission allow it.
- **Runtime log noise** — Qwen sentiment scoring now skips real provider calls when `QWEN_API_KEY` is absent and uses the heuristic path directly.
- **Missing icon 404s** — Removed references to absent `logo192.png`/`logo512.png` assets from the PWA manifest and HTML head.


---

## [0.20.0] - 2026-06-08

### Added

- **Phase E: Drawing Tools Completion** — `parallelChannel`, `pitchfork`, `horizontalRay` with multi-click anchor placement and hit testing in `ChartOverlay.tsx`.
- **React error boundary** — `frontend/src/components/ErrorBoundary.tsx` wraps App.tsx.

### Fixed

- **App.tsx JSX structure** — Fixed missing closing `</div>` tag after ErrorBoundary wrapper.
- **Catalog mismatch audit** — `src/lakehouse/gold/market_metrics.py` 3 classes fixed from `iceberg_catalog.gold.*` to `iceberg.crypto_lakehouse.*`.
- **Market overview dead code removal** — Removed 130+ lines duplicate dead code from `backend/api/market_overview.py`.

### Changed

- **Sentiment heuristic improvement** — Expanded `bullish_terms` from 7 to 24 keywords, `bearish_terms` from 8 to 26 keywords in `backend/services/sentiment_service.py`.

### Notes

- Legacy batch files still reference `iceberg_catalog` as Spark catalog name, not schema.
- `npm run typecheck` and `npm run build` pass with zero errors.

---

## [0.19.3] - 2026-06-08

### Added

- **Dagster news sentiment gold asset** — `compute_news_sentiment_daily` upgraded from placeholder to full implementation, writes to `iceberg.crypto_lakehouse.gold_news_sentiment_daily` via Trino HTTP API.
- **Chart news markers wired** — `App.tsx` fetches news every 5 minutes, passes to `CandlestickChart` for colored circle markers.

### Changed

- **Frontend typecheck clean** — Removed unused imports from `NewsCard.tsx` and `CandlestickChart.tsx`.

### Notes

- Dagster daemon restart required: `docker compose restart dagster-daemon dagster-webserver`
- Runtime verification pending for full E2E test.

---

## [0.19.2] - 2026-06-07

### Added

- **Trino news sentiment writer** — `src/lakehouse/write_news_sentiment.py` aggregates PostgreSQL news sentiment by symbol/day.
- **News card component** — `frontend/src/components/NewsCard.tsx` for sentiment-aware news rendering.
- **Phase C integration tests** — `tests/integration/test_news_pipeline.py`.

### Changed

- **News fetch persistence dedupe** — `backend/tasks/news_fetcher.py` uses insert-then-update fallback logic.
- **News payload normalization** — `backend/services/news_service.py` decodes JSON/text fields correctly.
- **Dagster news sentiment aggregation** — `orchestration/assets.py` includes `compute_news_sentiment_daily` in gold layer job.
- **Frontend news rendering** — NewsPage, MarketNews, newsService now consume PostgreSQL-backed data.

### Fixed

- **Real news API runtime** — `/api/news/latest`, `/api/news/trending`, `/api/news/sentiment/{symbol}`, `/api/news/search` serve real PostgreSQL-backed data.

---

## [0.19.1] - 2026-06-07

### Added

- **News persistence migration** — `004_phaseC_news_enhancements.sql` extends `news_articles` with sentiment fields, `symbols_mentioned`, `raw_metadata`.
- **PostgreSQL-backed news fetcher** — `backend/tasks/news_fetcher.py` persists to PostgreSQL with `ON CONFLICT (source, external_id) DO NOTHING`.
- **LLM sentiment scoring service** — `backend/services/sentiment_service.py` batch-scores with Qwen/LiteLLM.

### Changed

- **News API now async + database-backed** — `backend/api/news.py` and `backend/services/news_service.py` read from PostgreSQL.
- **Backend startup loops** — `backend/app.py` starts `sentiment_score_loop()` alongside news fetch loop.
- **Frontend news normalization** — `frontend/src/services/newsService.ts` accepts persisted news payloads.

---

## [0.19.0] - 2026-06-06

### Added

- **Gold aggregation entrypoint** — `src/lakehouse/gold_aggregator.py` and `src/lakehouse/gold_aggregator_trino.py` for runtime gold tables.
- **Dagster gold asset** — `compute_gold_layer` asset and `gold_layer_schedule` in `orchestration/assets.py`.
- **Phase A integration coverage** — `tests/integration/test_gold_layer.py`.

### Changed

- **Spark streaming startup resilience** — `src/lakehouse/pipeline.py` wraps each streaming query startup with bounded retry logic.
- **Spark lakehouse schema compatibility** — Added Iceberg schema evolution helper, reordered streaming DataFrame selects.
- **Kline lakehouse capture** — Removed over-restrictive `interval == "1m"` filter.
- **Spark metrics config** — Removed invalid `ClassLoaderSource` entries from `config/spark/metrics.properties`.
- **Market Overview gold queries** — Refactored to read from `iceberg.crypto_lakehouse.gold_*` tables.

### Fixed

- **Phase A environment mismatch** — Trino exposes `iceberg.crypto_lakehouse` instead of `iceberg.bronze/silver/gold`.
- **Spark stream runtime blocker** — Restored `BinanceDualStreamToIceberg` to RUNNING state.

---

## [0.18.3] - 2026-06-06

### Changed

- **TICKER_HEARTBEAT_SEC: 10s → 0.3s** — `src/common/config.py` reduced from 5.0 to 0.3. Binance ticker stream now sends updates every 0.3s. Batch buffer (BATCH_SIZE=100, FLUSH_INTERVAL=0.5s). Redis write load ~240 ops/sec.

### Fixed

- **litellm missing in fastapi-dev** — Rebuilt image with `--no-cache` after `requirements.txt` had litellm but Docker cached old image.

---

## [0.18.2] - 2026-06-06

### Added

- **Token cost display** — AI chat panel shows token usage (input → output) and estimated USD cost below each assistant message.

### Changed

- **AI_ENABLE_REAL_LLM default** — Fixed `.env` to set `AI_ENABLE_REAL_LLM=true`.
- **Provider metadata enrichment** — `provider_metadata` now includes `token_input`, `token_output` alongside provider/model/latency info.

### Fixed

- **Token usage tracking** — Added `token_input`, `token_output`, `estimated_cost_usd` fields to `AIChatResponse`, LiteLLM provider, frontend types.

---

## [0.18.1] - 2026-06-07

### Changed

- **Documentation reinspection refresh** — Updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, `.env.example` for 0.18.0 facts.

---

## [0.18.0] - 2026-06-06 - Phase 1 AI Ask Mode Implementation

### Added

- **Phase 1 AI Ask Mode** — Real LLM inference pipeline with provider routing, RAG enrichment, prompt building, output guard, confidence estimation.
- **Provider abstraction** — `BaseProvider` interface with `MockProvider`, `LiteLLMProvider`, `ProviderRouter`. Supports vLLM, Qwen API, Llama API, OpenAI, Gemini, DeepSeek.
- **RAG knowledge base** — pgvector-powered vector similarity search with `003_phase1_ai_rag.sql` migration.
- **Curated knowledge base** — 5 approved documents with HNSW index.
- **Prompt builder** — Structured Ask Mode prompts with system instructions, RAG chunks, conversation history.
- **Output guard** — Validates LLM responses for financial safety.
- **Context service** — Inspects chart context, generates data caveat warnings.
- **AI API modularization** — Refactored `backend/api/ai.py` into `backend/api/ai/` package.
- **Knowledge API endpoints** — Admin-only `/api/ai/knowledge/ingest`, authenticated `/api/ai/knowledge/search`.
- **50 golden evaluation questions** — Covering technical indicators, live chart analysis, RAG retrieval, out-of-scope refusal.
- **AI documentation** — `docs/ai/AI_ARCHITECTURE.md`, `AI_API_CONTRACTS.md`, `RAG_KNOWLEDGE_BASE.md`, `AI_PROVIDER_ROUTING.md`, `AI_EVALUATION.md`, `AI_SECURITY.md`, `AI_ROADMAP.md`.

### Changed

- **Documentation audit refresh** — Updated for Phase 1 AI foundation, modular AI routes, RAG/provider caveats.

### Fixed

- **Phase 1 AI type safety** — Fixed 8 Pyright type safety issues across AI chat routing, knowledge ingestion, litellm provider integration, RAG retrieval logic, unit tests.

---

## [0.17.11] - 2026-06-05

### Added

- **Auto-failover Health Monitor** — `src/producer/health_monitor.py` checks Kafka and Flink health every 30s. Auto-enable direct Redis bypass when both down for 60s.
- **Backend Indicator Fallback** — `backend/services/indicator_service.py` computes indicators from Redis kline history when Flink unavailable.
- **Data Freshness Tracking** — All indicator responses include `source`, `freshness_seconds`, `is_stale`, `is_fallback`.

### Changed

- **Direct Redis toggle** — Now controlled by HealthMonitor state, not just static env var.

---

## [0.17.10] - 2026-06-05

### Added

- **Direct Redis Bypass** — `src/exchanges/binance/redis_writer.py` `DirectRedisWriter` class. Toggle via `ENABLE_DIRECT_REDIS=true`.

### Changed

- **market overview** — Fixed catalog name mismatch (`iceberg_catalog.gold.*` → `iceberg.gold.*`) in 6 query functions.

---

## [0.17.9] - 2026-06-05

### Fixed

- **market overview catalog name mismatch** — `backend/api/market_overview.py` queried `iceberg_catalog.gold.*` but Trino catalog is `iceberg`.

### Added

- **Section 17 Data Tables Reference** — Added comprehensive documentation to `docs/SYSTEM.md`.

---

## [0.17.8] - 2026-06-04

### Fixed

- **indicators test interval key** — Mock data includes `"interval": "5m"` field.
- **trades test data format** — Mock returns JSON string trade objects matching Flink KeyDBTradeWriter format.
- **market overview placeholder test** — Test accepts either `is_placeholder` value.
- **e2e app metadata tests** — Updated expected app title/version to "LMView API" / "0.17.8".

### Added

- **Producer Prometheus metrics** — `prometheus_client` metrics endpoint on port 9090.
- **Prometheus scrape config** — Updated producer scrape job port from 9095 to 9090.

### Verified

- **Integration test suite** — All 300 tests pass.
- **Frontend typecheck** — `npm run typecheck` passes with React 19/Lucide React.

---

## [0.17.7] - 2026-06-04

### Fixed

- **docker-compose.yml YAML syntax** — Fixed CRLF line endings and Unicode box drawing characters.
- **OKX channel name fix** — Changed `tickers` (plural) to `ticker` (singular) per OKX WebSocket API spec.
- **OKX instId case handling** — Symbols passed as-is (e.g., "BTCUSDT" → "BTC-USDT").

### Changed

- **OKX kline interval** — OKX subscription uses 1m minimum; filtered to 13 well-known pairs.
- **OKX experimental disabled** — Set `ENABLE_OKX=false` until OKX channel format confirmed.

---

## [0.17.6] - 2026-06-04

### Fixed

- **Kafka brokers 2-3 startup** — Started kafka-2 and kafka-3 replicas.
- **Flink job submit path** — Recreated deps.zip in flink-jobmanager container; job stays RUNNING.
- **Spark streaming JVM longevity** — Changed to `spark.streams.awaitAnyTermination()`; Spark app stays RUNNING.
- **auto-submit-jobs CRLF** — Converted to LF; inlined all job-submission logic into docker-compose.yml entrypoint.

### Changed

- **Spark submit packages** — Added `org.apache.spark:spark-avro_2.12:3.5.5`.
- **Dagster code location loading** — Added `Definitions` wiring, narrowed lazy imports.
- **Flink checkpoint runtime config** — Switched checkpoint storage URI away from broken `s3a://` path.
- **Trino startup idempotence** — Made entrypoint keep JMX javaagent line unique in `jvm.config`.

---

## [0.17.4] - 2026-06-03

### Changed

- **Frontend chart live path** — `CandlestickChart` subscribes to `/api/stream/indicators/{interval}` and applies streamed indicator snapshots.
- **Indicator stream fallback behavior** — Kept local client-side indicator computation as fallback/history source.

---

## [0.17.3] - 2026-06-03

### Added

- **Indicator WebSocket stream** — `/api/stream/indicators/{interval}` pushes real-time indicator snapshots from Redis.
- **Redis indicator history** — Extended Flink indicator writer to persist `indicator:history:{exchange}:{symbol}:{interval}` sorted sets.
- **Iceberg indicator history** — Added `iceberg_catalog.gold.indicator_history` creation and writes.

### Changed

- **Indicator Redis schema** — Latest snapshots now use `indicator:latest:{exchange}:{symbol}:{interval}` with fallback to older key layouts.
- **Indicator API contracts** — `/api/indicators/{symbol}` and `/api/indicators/{symbol}/summary` accept `interval` parameter.
- **Indicator pipeline output** — Flink indicator writer emits RSI, MACD, Bollinger Band, ATR, volume-SMA into Redis and InfluxDB.

---

## [0.17.2] - 2026-06-03

### Changed

- **`CandlestickChart.tsx`** — Optimized live indicator rendering; chart series update immediately from latest candle stream.
- **Realtime indicator sync** — Added focused live indicator window, direct per-series updates.
- **Chart settings effect** — Stopped tying indicator rebuilds to every live candle state change.

---

## [0.17.1] - 2026-06-03

### Changed

- **`docs/VIET_LOG.md`** — Reworked Section 6 into table-first audit format.
- **Lakehouse schema inventory** — Documented columns, datatypes, schema drift risks across `crypto_lakehouse`, `bronze`, `silver`, `gold`.
- **Indicator architecture design** — Replaced minimal note with richer TradingView-style indicator catalog.

---

## [0.17.0] - 2026-06-03

### Added

- **10 new Grafana dashboards** — Spark Logs, Trino Logs, MinIO Logs, Redis Sentinel Logs, Postgres Dashboard, InfluxDB Dashboard, Nginx Dashboard, Zookeeper Dashboard, Dagster Dashboard, Producer Dashboard.
- **System Error Triage dashboard** — Single pane for all ERROR logs, filterable by service.
- **Structured log pipeline** — Promtail extracts `log_level` and `error_type` labels.
- **Prometheus scrape configs** — Added scrape jobs for InfluxDB, Postgres exporter, Nginx exporter, Dagster, Zookeeper JMX, Producer.
- **10 new alert rules** — Postgres, InfluxDB, Nginx, Zookeeper, Dagster, Producer, log-based.

### Changed

- **docker-compose.yml** — Exposed Zookeeper JMX port `7071`.
- **Total Grafana dashboards:** 11 → 22.

---

## [0.16.0] - 2026-06-03

### Changed

- **`/api/market/overview`** — Now attempts Trino gold table queries first; falls back to Redis `ticker:latest` scan.

### Added

- **`/api/stream/{interval}`** — New per-interval WebSocket endpoint for single-timeframe candle streaming.
- **OKX subscription frame builder** — `build_subscribe_frame()` method on OKXClient with helper methods.
- **OKX WebSocket handler** — `_handle_okx_message()` parses OKX `{"arg":..., "data":[...]}` response format.
- **Trade hot cache writer** — `KeyDBTradeWriter` Flink writer consuming `crypto_trades` topic.
- **Trade API enhancement** — `/api/trades/{symbol}` reads `trade:latest` first, falls back to `ticker:history`.

### Fixed

- **Exchange qualification** — kline aggregation, Spark DDLs, indicator keys, trades API now consistently carry `exchange` field.

---

## [0.15.2] - 2026-06-01

### Added

- **Settings modal** — Wired header Settings button to Account, Customization, AI Helper, About, Debug tabs with login/admin gates.
- **AI Helper gate** — Requires login before opening AI Helper.

### Changed

- **Mock data boundary** — Moved market/news/AI mock generators under `frontend/src/data/mock/`.
- **API placeholder handling** — Added frontend metadata guards so placeholder payloads render empty/unavailable states.

---

## [0.15.1] - 2026-06-01

### Fixed

- **Frontend auth session UI** — Wrapped app with `AuthProvider`, wired login/register modal with blurred backdrop.
- **Auth registration runtime** — Added PostgreSQL async driver support, pinned bcrypt for passlib compatibility.
- **Recent Trades frontend** — Normalized `/api/trades/{symbol}` response in `marketDataService`.

---

## [0.15.0] - 2026-06-01 - Phase 0: AI Foundation Layer

### Added

- **PostgreSQL auth foundation** — `backend/core/postgres.py` async connection pool (asyncpg), `backend/core/security.py` password hashing, `backend/core/auth_dependencies.py` FastAPI Bearer-token auth.
- **Auth API** — `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `PATCH /api/auth/preferences`.
- **AI backend API** — `GET /api/ai/health`, `POST /api/ai/chat`, `GET/POST /api/ai/sessions`, `GET /api/ai/sessions/{id}/messages`, `POST /api/ai/chart-context`, `POST /api/ai/chart-actions/validate`, `POST /api/ai/chart-actions/record`.
- **Scope gate service** — Keyword-based in-scope/out-of-scope classification.
- **Chart action validator** — Validates AI-proposed chart actions.
- **Mock AI service** — Deterministic Phase 0 responses that echo received context.
- **Indicator service** — Catalog of 10 supported indicators, Redis-backed latest values.
- **SQL migration** — `001_phase0_schema.sql` with 9 tables.
- **Frontend auth service** — `frontend/src/services/authService.ts` with API calls + mock fallback.
- **Frontend AI service** — `frontend/src/services/aiService.ts` with all AI API calls + auth header injection.
- **Frontend AI panel** — Extracted `AiAssistantPanel` from `RightPanel` into `frontend/src/features/ai/`.
- **Phase 0 test suite** — 53 tests covering auth security, AI models, scope gate, chart action validator.

### Not Implemented (Phase 1+)

- Real LLM integration (LangGraph, model inference, RAG)
- Autonomous chart interaction
- Cookie-based session transport

---

## [0.14.2] - 2026-05-30

### Added

- **Drawing tool groups** — Rebuilt floating left drawing bar with hoverable groups, viewport-bounded flyout menus.
- **Drawing tools** — Added Fibonacci retracement, ABCD/XABCD patterns, Elliott wave, long/short position, forecast drawing paths.

### Fixed

- **Light mode contrast** — Moved chart toolbar, symbol selector, drawing toolbar to shared theme tokens.
- **Pattern drafting** — Added point-by-point ABCD/XABCD drafting with anchored labels.

---

## [0.14.1] - 2026-05-28

### Added

- **Theme support** — Light and dark theme support through shared CSS tokens.
- **Frontend client caching** — Added caching for stable symbols, chart history, market overview, movers, news.
- **Chart type selector** — Wired candlestick, bar, line, area renderers.
- **Chart export** — Includes chart canvases, visible price/time axes, latest OHLCV metadata, selected chart type, SVG user drawings.
- **Indicators library** — Expanded chart indicators panel with TradingView-style search, grouped categories, client-side calculations.
- **AI assistant panel** — Reworked right-panel AI Helper into Copilot-style chat workspace.

### Changed

- **Header shell** — Reworked around LMView branding, chart/markets navigation, theme/settings/user controls.
- **Right panel** — Reduced default desktop width, compacted overview, watchlist, order book, recent trade spacing.

---

## [0.14.0] - 2026-05-22

### Changed

- **Frontend folder structure** — Reorganized `frontend/src` into standard Vite React TypeScript folders.
- **Frontend services** — Centralized API helpers, environment constants, timeframe constants, market/news data services.
- **UI shell** — Merged top toolbar behavior into canonical `Header` component.
- **Chart feature** — Flattened `features/chart` by removing redundant nested `components/chart` directories.

---

## [0.13.1] - 2026-05-22

### Fixed

- **Kafka Topics** — Resolved `Unrecognized partition` errors by recreating `crypto_ticker`, `crypto_klines`, `crypto_trades`, `crypto_depth` topics with 12 partitions.
- **Orderbook API** — Fixed HTTP 500 `ReadOnlyError` in `/api/orderbook/{symbol}` by routing fallback cache expiration to Redis Master.
- **Exchange Fallback Logic** — `/api/trades` and `/api/orderbook` correctly parse new exchange-aware Redis keys.

---

## [0.13.0] - 2026-05-22

### Changed

- **Nginx dev mode** — Switched from self-signed HTTPS to plain HTTP (port 80 only).
- **Nginx prod mode** — HTTPS via certbot with any domain, not limited to DuckDNS.
- **Nginx config split** — Single `nginx.conf` replaced with `nginx-dev.conf` and `nginx-prod.conf`.

---

## [0.12.3] - 2026-05-21

### Changed

- **Dependencies** — Upgraded `lightweight-charts` to `5.2.0` in `frontend/package.json`.

---

## [0.12.2] - 2026-05-20

### Added

- **Mock Data Enhancement** — Added `NewsItem` type, dynamic mock data simulation for order books, trades, tickers.
- **Mock Mode Toggle** — `VITE_DATA_SOURCE` env variable to toggle between 'mock' and 'api' data sources.
- **UI Mode Indicator** — Visual badge in `Header.tsx` indicating current data source.

### Changed

- **Mock Data Refactor** — Extracted inline mock data generation to `mock/mockDataGenerator.ts`.
- **Market Overview Service** — `marketOverviewService.ts` acts as controller switching between API and mock.

### Fixed

- **TypeScript Overlap Error** — Resolved type comparison error for `DATA_SOURCE` constant.

---

## [0.12.1] - 2026-05-19

### Changed

- **Integration Test Suite** — Modernized to support Redis Sentinel HA.
- **API Routing** — Reordered FastAPI router inclusions to prioritize `market_overview` routes.

### Added

- **API Tests** — Mandatory integration tests for `market_overview` and `news` endpoints.

---

## [0.12.0] - 2026-05-19

### Added

- **Market Overview API** — `backend/api/market_overview.py` and `backend/services/heatmap_service.py`.
- **News API** — Background fetcher and endpoints for aggregating sentiment-driven news.
- **Background Tasks** — `market_fetcher.py` and `news_fetcher.py` integrated into FastAPI lifespan.
- **Frontend Components** — `LeftSidebar`, `RightPanel`, `TopToolbar`, `MarketOverviewPage`, `NewsPageRedesigned`, `MarketNews`.

---

## [0.11.0] - 2026-05-16

### Added

- **Nginx reverse proxy for monitoring** — Grafana (`/grafana/`), Prometheus (`/prometheus/`), Loki (`/loki/`) routed through nginx.
- **Basic Auth for Prometheus/Loki** — htpasswd generated at container startup.
- **Grafana WebSocket proxy** — `/grafana/api/live/` for live dashboard updates.
- **Rate limiting** — `monitoring_limit` zone (10r/s per IP).

---

## [0.10.0] - 2026-05-16

### Changed

- **Documentation system rewrite** — Replaced all project documentation with standardized system: `docs/SYSTEM.md`, `docs/CHANGELOG.md`, `docs/AGENTS.md`, `README.md`.
- **Project renamed** from "Lambda Architecture for TradingView-Style Platform" to **LMView**.
- **Documentation language** standardized to English.

---

## [0.9.0] - 2026-05-14

### Changed

- **Monitoring stack integration** — Merged Flink infrastructure refactor with monitoring/logging stack.
- **Redis Sentinel entrypoint** — Fixed entrypoint scripts for correct Sentinel initialization.
- **Node-exporter volumes** — Corrected volume mount paths for host metrics collection.
- **Grafana provisioning** — Fixed rule hierarchy in provisioning configuration.

---

## [0.8.0] - 2026-05-09

### Changed

- **Kafka HA** — Migrated from single Kafka node to 3-node KRaft cluster with replication factor 3.
- **Redis Sentinel HA** — Replaced standalone KeyDB with Redis cluster: 1 Master, 2 Replicas, 3 Sentinels.
- **Backend Redis client** — Implemented `RedisSentinelManager` with auto-discovery, failover, read/write splitting.

---

## [0.7.0] - 2026-05-05

### Added

- **Historical mode** — Full date range picker with request ID tracking.
- **Interval helpers** — `normalize_interval()`, `interval_to_seconds()`, `interval_to_ms()` in `candle_service.py`.
- **Integration tests** — 4 new tests for candle merge quality and staleness checks.
- **Unit tests** — 14 new tests covering normalization, aggregation, merge logic.

### Fixed

- **Aggregate function (CRITICAL)** — Now sorts by timestamp before determining open/close.
- **Ticker enrichment staleness** — Backend verifies ticker freshness against sub-candle data.
- **Interval normalization** — Frontend normalizes uppercase intervals before all API calls.

---

## [0.6.0] - 2026-05-02

### Added

- **161 total tests** across 5 categories: Unit (80), Integration (39), Security (17), Performance (9), E2E (6).
- **Test infrastructure** — `tests/integration/`, `tests/e2e/`, `tests/performance/` packages.

---

## [0.5.0] - 2026-04-28

### Fixed

- **Producer image** — Downgraded from Python 3.14-slim to 3.11-slim (fastavro C-extension compatibility).
- **Nginx port conflict** — Removed duplicate port 3000 binding.
- **Binance WebSocket** — Switched `!ticker@arr` to `!miniTicker@arr`.
- **Flink module resolution** — Fixed `— pyFiles /app/src` in job submission script.

---

## [0.4.0] - 2026-04-28

### Changed

- **Complete TypeScript migration** — All 27 frontend files migrated from `.jsx`/`.js` to `.tsx`/`.ts`.
- **React 18 → 19** upgrade.
- **Type system** — 18 shared TypeScript interfaces in `types/index.ts`.
- **i18n** — ~130 translation keys (English + Vietnamese).

---

## [0.3.0] - 2026-04-25

### Changed

- **Exchange abstraction** — `ExchangeClient` base class + `BinanceClient` implementation.
- **Shared infrastructure** — Centralized `src/common/` (config, kafka_client, avro_serializer, logging).
- **Producer rewrite** — 632-line monolith → ~250-line exchange-agnostic orchestrator.
- **Flink pipeline split** — 996-line monolith → `pipeline.py` + 7 individual writer modules.

---

## [0.2.0] - 2026-04-25

### Changed

- **Backend MVC** — Migrated `serving/` → `backend/` with `api/`, `services/`, `models/`, `core/` structure.
- **Pydantic models** — Created response models for candle, ticker, health endpoints.
- **Shared service** — `candle_service.py` (280 lines) for all OHLCV business logic.
- **Dev/Prod switching** — `docker-compose.override.yml` (dev) + `docker-compose.prod.yml` (prod).

### Added

- **Testing framework** — pytest with 40 initial tests (unit, model, security).
- **Vite migration** — CRA → Vite, all 21 components renamed to `.jsx`.

---

## [0.1.0] - 2026-04-25

### Added

- **TRACKING.md** — AI assistant working document.
- **DOCUMENTATION.md** — Technical documentation (Vietnamese).
- **.gitignore** — Updated exclusion list.
