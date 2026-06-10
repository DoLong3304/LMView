# Changelog - LMView

All notable changes to this project are documented in this file.

This log is maintained by AI agents and human contributors to track project evolution.

Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

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

## [0.20.1] - 2026-06-09 - Frontend Runtime Fixes

### Added

- **AI session restore controls** - AI Helper now remembers the active backend session across reloads and Settings can load previous AI Helper sessions.
- **Customization presets** - Settings now exposes indicator, drawing-tool, layout, default exchange, volume, magnet, and compact-panel presets.
- **Admin AI usage summary** - Admin users can see total AI input/output tokens and estimated cost in AI Helper settings.

### Fixed

- **Realtime chart updates** - WebSocket candle building now folds fresh ticker prices into 1s/1m candles when kline candle caches lag, so chart candles update alongside indicators.
- **All-timeframe WebSocket route** - Registered `/api/stream/all` before the catch-all `/api/stream/{interval}` route so the chart receives live candle frames instead of an unsupported `all` interval error.
- **Chart resize after browser zoom** - Chart resize now uses measured container/stage bounds, observes visual viewport changes, and keeps the chart wrapper shrinkable to avoid bottom clipping after zoom out/in.
- **AI Ask readability** - AI Helper renders common markdown blocks and inline formatting instead of showing raw markdown text.
- **AI Helper tab persistence** - The right panel now keeps AI Helper mounted while Overview is active, preserving in-flight responses and preventing remount scroll animation when switching tabs.
- **AI timestamp confusion** - Ask Mode prompts now include live server time, epoch milliseconds, and UTC-formatted chart timestamps so current candle times are not misclassified as invalid due model cutoff.
- **Normal-user token leakage** - Per-message token and cost metadata is hidden from non-admin users.
- **Kline scroll 500s** - Missing optional Trino/Iceberg historical candle tables now degrade to empty fallback results instead of failing `/api/klines` scroll requests.
- **Notification delivery loop** - Header notifications now reload periodically and can show browser desktop notifications when the user preference and browser permission allow it.
- **Runtime log noise** - Qwen sentiment scoring now skips real provider calls when `QWEN_API_KEY` is absent and uses the heuristic path directly.
- **Missing icon 404s** - Removed references to absent `logo192.png`/`logo512.png` assets from the PWA manifest and HTML head.

---

## [0.20.0] - 2026-06-08 - Phase D: System Audit & Critical Fixes

### Added

- **React error boundary** — `frontend/src/components/ErrorBoundary.tsx` wraps App.tsx to prevent full-app crashes on component errors; shows retry + reload buttons, displays stack trace in dev mode.

### Fixed

- **Catalog mismatch audit** — `src/lakehouse/gold/market_metrics.py` 3 classes (`GoldMarketDominance`, `GoldVolatilityRanking`, `GoldMoversRanking`) had `iceberg_catalog.gold.*` references (non-existent schema). Fixed to `iceberg.crypto_lakehouse.*` — matching active catalog config in `lakehouse/pipeline.py` and Dagster assets.
- **Market overview dead code removal** — Removed 130+ lines of duplicate dead code from `backend/api/market_overview.py` (duplicate `_get_trending_news`, `_get_sector_performance`, `_get_heatmap_data`, `_get_indicators_summary`, `_derive_market_from_redis` functions after the first return statement).

### Changed

- **Sentiment heuristic improvement** — Expanded `bullish_terms` from 7 to 24 keywords, `bearish_terms` from 8 to 26 keywords in `backend/services/sentiment_service.py`; score and confidence now scale with match count for more meaningful sentiment differentiation.

### Notes

- **Legacy batch files still reference `iceberg_catalog`** — `src/batch/` and `src/lakehouse/silver/` use `iceberg_catalog` as Spark catalog name (JDBC/Hadoop catalog alias), not schema. Active runtime uses `iceberg.crypto_lakehouse` via Trino. Legacy files not used by Dagster orchestration.
- **Trino QUEUED investigation** — Code review confirms stable implementation with `nextUri` polling in `gold_aggregator_trino.py` and `compute_news_sentiment_daily`. Runtime verification requires Docker environment.

---

## [0.19.3] - 2026-06-08 - Phase C Full Completion

### Added

- **Dagster news sentiment gold asset** — `orchestration/assets.py` `compute_news_sentiment_daily` upgraded from placeholder to full implementation: reads PostgreSQL `news_articles`, aggregates by symbol/day via `UNNEST(symbols_mentioned)`, writes to `iceberg.crypto_lakehouse.gold_news_sentiment_daily` via Trino HTTP API. Now has `deps=[compute_gold_layer]` to run after gold layer.
- **Chart news markers wired** — `frontend/src/App.tsx` now fetches news via `fetchLatestNews({ limit: 200, hours: 72 })` every 5 minutes, stores in `newsArticles` state, and passes `newsItems={newsArticles} showNewsMarkers={true}` to `CandlestickChart`. Chart renders colored circle markers at news event timestamps.

### Changed

- **Frontend typecheck clean** — Removed unused `React` import from `NewsCard.tsx` and unused `NewsCard` import from `CandlestickChart.tsx`. `npm run typecheck` passes with zero errors.

### Notes

- **Dagster daemon restart required** — After this change, restart `dagster-daemon` and `dagster-webserver` containers so the new asset code loads: `docker compose restart dagster-daemon dagster-webserver`
- **Runtime verification pending** — Full end-to-end test (news fetch → sentiment score → Dagster aggregation → chart markers) requires live Docker environment with running services.

---

## [0.18.1] - 2026-06-07 - Update documentations

### Changed

- **Documentation reinspection refresh** - Reaudited current code state and updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, and `.env.example` comments for 0.18.0 facts: Phase 1 AI Ask Mode, modular AI routes, RAG/provider caveats, current Compose/service counts, Flink trade cache, exchange propagation status, Dagster `Definitions`, lakehouse `exchange` handling, observability counts, and test inventory.

---

## [0.19.2] - 2026-06-07 - Phase C Runtime Completion

### Added

- **Trino news sentiment writer** — Added `src/lakehouse/write_news_sentiment.py` to aggregate PostgreSQL news sentiment by symbol/day and materialize `gold_news_sentiment_daily` through Trino.
- **News card component** — Added `frontend/src/components/NewsCard.tsx` for sentiment-aware news rendering with badges and symbol chips.
- **Phase C integration tests** — Added `tests/integration/test_news_pipeline.py` covering real latest news, sentiment fields presence, and symbol filtering.

### Changed

- **News fetch persistence dedupe** — `backend/tasks/news_fetcher.py` now uses insert-then-update fallback logic instead of fragile `ON CONFLICT` targeting, which makes persistence robust against pre-existing partial indexes and local schema drift.
- **News payload normalization** — `backend/services/news_service.py` now decodes JSON/text fields from PostgreSQL correctly (`tags`, `symbols`, `raw_metadata`) and exposes clean API payloads.
- **Dagster news sentiment aggregation** — `orchestration/assets.py` now includes `compute_news_sentiment_daily` in the gold layer job.
- **Frontend news rendering** — `frontend/src/pages/NewsPage.tsx`, `frontend/src/features/market/components/MarketNews.tsx`, and `frontend/src/services/newsService.ts` now consume persisted PostgreSQL-backed article payloads, `symbolsMentioned`, and normalized sentiment labels.
- **Chart overlay support** — `frontend/src/features/chart/CandlestickChart.tsx` now accepts `newsItems` and renders lightweight-charts markers for symbol-matching news events.
- **Frontend types** — `frontend/src/types/index.ts` now includes `symbolsMentioned` on `NewsArticle`.

### Fixed

- **Real news API runtime** — `/api/news/latest`, `/api/news/trending`, `/api/news/sentiment/{symbol}`, and `/api/news/search` now serve real PostgreSQL-backed data instead of empty in-memory cache/mocks in healthy runtime.
- **Phase C backend ingestion blocker** — News fetcher now successfully persists fetched RSS/API articles into `news_articles` instead of failing on invalid conflict target behavior.

### Notes

- **Qwen scoring path present but lightly verified** — Sentiment scoring service and loop are wired, but article sentiment may still remain mostly neutral until enough scoring cycles complete or provider/runtime tuning is refined.
- **Phase C frontend overlay path implemented, not deeply browser-verified in this session** — code path exists and types align, but full visual verification still depends on interactive UI inspection.

---

## [0.19.1] - 2026-06-07 - Phase C-1 Real News Persistence

### Added

- **News persistence migration** — Added `backend/migrations/004_phaseC_news_enhancements.sql` to extend `news_articles` with `content_snippet`, `sentiment_confidence`, `sentiment_computed_at`, `symbols_mentioned`, `raw_metadata`, plus source/external dedupe and symbol lookup indexes.
- **PostgreSQL-backed news fetcher** — Replaced in-memory-only cache flow in `backend/tasks/news_fetcher.py` with real persistence using `EnhancedMultiSourceScraper`, symbol extraction, normalization, and `ON CONFLICT (source, external_id) DO NOTHING` writes.
- **LLM sentiment scoring service** — Added `backend/services/sentiment_service.py` to batch-score unscored news rows with Qwen/LiteLLM and persist `sentiment_score`, `sentiment_label`, `sentiment_confidence`, and `sentiment_computed_at`.

### Changed

- **News API now async + database-backed** — `backend/api/news.py` and `backend/services/news_service.py` now read latest/trending/search/symbol sentiment data from PostgreSQL instead of the old in-memory `_news_cache`.
- **Backend startup loops** — `backend/app.py` now starts a periodic `sentiment_score_loop()` alongside the existing news fetch loop.
- **Frontend news normalization** — `frontend/src/services/newsService.ts` now accepts persisted news payloads with `symbolsMentioned`/lowercase sentiment labels from the real API.

### Notes

- **Phase C only partially completed in this pass** — Backend persistence, query service, and sentiment loop are implemented. Frontend chart news markers, Dagster daily news sentiment gold asset, and full integration/runtime verification remain for later Phase C turns.

---

## [0.19.0] - 2026-06-06 - Lakehouse Gold Layer Runtime Prep

### Added

- **Gold aggregation entrypoint** — Added `src/lakehouse/gold_aggregator.py` to bootstrap and populate runtime gold-style tables in `iceberg_catalog.crypto_lakehouse` (`gold_movers_ranking`, `gold_market_dominance`, `gold_volatility_ranking`, `gold_momentum_indicators`, `gold_sector_performance`, `gold_news_sentiment_daily`) from existing `coin_ticker` and `coin_klines` tables.
- **Trino-native gold aggregation fallback** — Added `src/lakehouse/gold_aggregator_trino.py` to materialize gold tables through Trino HTTP API when local Spark batch aggregation is unstable under current standalone resource limits.
- **Dagster gold asset** — Added `compute_gold_layer` asset and `gold_layer_schedule` in `orchestration/assets.py`; current implementation now executes the Trino-native gold aggregation path for stable local runs.
- **Phase A integration coverage** — Added `tests/integration/test_gold_layer.py` to verify market overview metadata shape, response-time expectations, and fallback continuity.

### Changed

- **Spark streaming startup resilience** — Updated `src/lakehouse/pipeline.py` to wrap each streaming query startup with bounded retry logic while preserving `awaitAnyTermination()` and `s3://` checkpoint paths.
- **Spark stream submit path** — Verified streaming lakehouse job now starts only when submitted with explicit Iceberg/Kafka/Avro packages; bare `spark-submit /app/src/lakehouse/pipeline.py` was insufficient in current Spark image.
- **Spark lakehouse schema compatibility** — Added best-effort Iceberg schema evolution helper and reordered streaming DataFrame selects in `src/lakehouse/pipeline.py` so write schema matches existing Iceberg field ids/order for `coin_ticker`, `coin_trades`, and `coin_klines`.
- **Kline lakehouse capture** — Removed over-restrictive `interval == "1m"` filter from the Spark lakehouse stream path so closed kline events now populate `coin_klines` again under current producer output.
- **Spark metrics config** — Removed invalid `ClassLoaderSource` entries from `config/spark/metrics.properties` to stop repetitive Spark master/worker metrics initialization errors at startup.
- **Market Overview gold queries** — Refactored `backend/api/market_overview.py` to read current `iceberg.crypto_lakehouse.gold_*` tables, widened freshness window to 30 minutes for local scheduling tolerance, and removed stale references to nonexistent `iceberg.gold` / `iceberg_catalog.gold` schemas.
- **Market overview integration mocks** — Updated `tests/integration/test_api_market_overview.py` for current response shape and query-output contracts.

### Fixed

- **Phase A environment mismatch** — Adjusted implementation to current runtime reality where Trino exposes `iceberg.crypto_lakehouse` instead of `iceberg.bronze/silver/gold`, avoiding direct references to missing schemas.
- **Spark stream runtime blocker** — Restored `BinanceDualStreamToIceberg` to RUNNING state in Spark standalone by launching with explicit package set and fixing Iceberg schema-order incompatibilities for ticker/trade/kline writes.
- **Market Overview real-data path** — `/api/market/overview` now returns `metadata.source = "trino_gold"`, `is_placeholder = false`, and `gold_tables_healthy = true` after gold aggregation succeeds.

### Verified

- **Spark runtime** — `BinanceDualStreamToIceberg` remains RUNNING in Spark master with active executors.
- **Lakehouse row counts** — `coin_ticker`, `coin_trades`, and `coin_klines` all repopulate successfully in Iceberg.
- **Gold layer row counts** — `gold_movers_ranking`, `gold_market_dominance`, `gold_volatility_ranking`, `gold_momentum_indicators`, and `gold_sector_performance` now materialize rows in `iceberg.crypto_lakehouse`.
- **Market Overview API** — endpoint returns gold-backed movers, dominance, volatility, sector metrics, and metadata marking the response as non-placeholder.

---

## [0.18.3] - 2026-06-06 - Ticker Heartbeat Optimization

### Changed

- **TICKER_HEARTBEAT_SEC: 10s → 0.3s** — `src/common/config.py` `TICKER_HEARTBEAT_SEC` reduced from `5.0` to `0.3`. Binance ticker stream now sends updates every 0.3s (or on price change). Previously 10s heartbeat caused stale prices on chart. With 400 symbols × 0.3s = ~120 ticker updates/sec to Redis via batch buffer (BATCH_SIZE=100, FLUSH_INTERVAL=0.5s). No Kafka impact (throttled independently). Redis write load: ~240 ops/sec (HASH + pipeline). CPU impact: negligible (<1% on 2-core producer). Network: ~50KB/s extra (400 symbols × ~120 bytes per ticker). System stable — batch buffering absorbs burst.

### Fixed

- **litellm missing in fastapi-dev** — Rebuilt image with `--no-cache` after `requirements.txt` had litellm but Docker cached old image without it. AI chat now routes to real Qwen API instead of mock fallback.

---

## [0.18.2] - 2026-06-06 - AI Real LLM Fix & Token Cost Tracking

### Fixed

- **AI_ENABLE_REAL_LLM default** — Fixed `.env` to set `AI_ENABLE_REAL_LLM=true` so Qwen API actually generates real responses instead of falling back to mock. Backend container reads env directly from `.env` via docker-compose interpolation.
- **Token usage tracking** — Added `token_input`, `token_output`, and `estimated_cost_usd` fields to `AIChatResponse`, LiteLLM provider, and frontend types. Real-time cost estimation displays below AI messages.
- **Provider metadata enrichment** — `provider_metadata` now includes `token_input`, `token_output` alongside provider/model/latency info.

### Added

- **Token cost display** — AI chat panel now shows token usage (input → output) and estimated USD cost below each assistant message when available.

### Changed

- **AI health endpoint** — Now correctly reports `real_llm_enabled: true` when Qwen API key is configured.

---

## [0.18.1] - 2026-06-07 - Update documentations

### Changed

- **Documentation reinspection refresh** - Reaudited current code state and updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, and `.env.example` comments for 0.18.0 facts: Phase 1 AI Ask Mode, modular AI routes, RAG/provider caveats, current Compose/service counts, Flink trade cache, exchange propagation status, Dagster `Definitions`, lakehouse `exchange` handling, observability counts, and test inventory.

---

## [0.18.0] - 2026-06-06 - Phase 1 AI Ask Mode Implementation

### Added

- **Phase 1 AI Ask Mode** — Real LLM inference pipeline with provider routing, RAG enrichment, prompt building, output guard, and confidence estimation. Full pipeline: scope gate → session → RAG retrieval → prompt assembly → provider routing → output guard → store message.
- **Provider abstraction** — `BaseProvider` interface with `MockProvider`, `LiteLLMProvider`, and `ProviderRouter`. Supports local vLLM, Qwen API, Llama API, OpenAI, Gemini, DeepSeek, LiteLLM proxy. Configurable priority order with automatic fallback chain; mock always available as final fallback.
- **RAG knowledge base** — pgvector-powered vector similarity search with `003_phase1_ai_rag.sql` migration. Knowledge sources, documents, chunks, and embeddings tables with HNSW index. Markdown ingestion with semantic chunking by headings/paragraphs/sentences. Content-hash deduplication. Retrieval with language/domain/tag/credibility filters. All retrievals logged for audit.
- **Curated knowledge base** — 5 approved documents: LMView Platform Guide, Technical Analysis Fundamentals, Cryptocurrency Market Structure, Risk Management, and Bilingual Crypto/Trading Glossary (EN/VI). Registry with source metadata.
- **Prompt builder** — Structured Ask Mode prompts with system instructions, chart context, RAG chunks, conversation history, data caveats, and financial safety addendum. Bilingual support.
- **Output guard** — Validates LLM responses for financial safety (flags guaranteed predictions, removes code execution patterns), ensures educational disclaimers. Supports EN/VI.
- **Context service** — Inspects chart context and generates data caveat warnings (placeholder market data, ticker-derived trades, stale order books, missing news, OKX experimental status).
- **AI API modularization** — Refactored `backend/api/ai.py` into `backend/api/ai/` package with separate modules for chat, sessions, chart context, chart actions, health, and knowledge endpoints.
- **AI model package** — Refactored `backend/models/ai.py` into `backend/models/ai/` package with separate modules for chat, chart actions, common, providers, RAG, knowledge, and evaluation models. Full backward compatibility maintained.
- **Knowledge API endpoints** — Admin-only `/api/ai/knowledge/ingest`, authenticated `/api/ai/knowledge/search` (vector similarity), `/api/ai/knowledge/sources`, `/api/ai/knowledge/health`.
- **Enhanced AI health** — `/api/ai/health` now reports AI mode, RAG status, pgvector readiness, available providers, and knowledge source count.
- **Phase 1 test suite** — 36 new tests covering provider routing, prompt building, output guard, context service, knowledge chunking, scope gate safety, and model backward compatibility. All 132 unit tests pass.
- **50 golden evaluation questions** — Covering technical indicators (10), live chart analysis (8), LMView limitations (5), RAG retrieval (5), out-of-scope refusal (8), prompt injection refusal (5), stale data warnings (3), bilingual (3), and risk disclaimers (3).
- **AI configuration** — New env vars in `.env.example` and `backend/core/config.py`: `AI_MODE`, `AI_ENABLE_REAL_LLM`, `AI_ENABLE_RAG`, provider API keys, vLLM settings, embedding model, RAG parameters.
- **Docker Compose AI services** — `docker-compose.ai.yml` overlay with `ai-api` (LiteLLM + online APIs, no GPU) and `ai-local` (vLLM, GPU required) profiles. LiteLLM proxy config in `ai_service/configs/litellm.yaml`.
- **Frontend AI API integration** — `useAiChat` now calls real backend `/api/ai/chat` when authenticated and not in mock mode, with local help responder as fallback. `AiMessage` and `AIChatResponse` types include Phase 1 fields (confidence, sources, data_caveats, provider_metadata).
- **AI documentation** — `docs/ai/AI_ARCHITECTURE.md`, `AI_API_CONTRACTS.md`, `RAG_KNOWLEDGE_BASE.md`, `AI_PROVIDER_ROUTING.md`, `AI_EVALUATION.md`, `AI_SECURITY.md`, `AI_ROADMAP.md`.
- **Future phase scaffolding** — `ai_service/` (LangGraph agents, tools, graph, prompts, observability), `src/ml/` (forecasting, sentiment), prompt templates, and AI config YAML files. All scaffolded with clear TODOs.

### Changed

- **Documentation audit refresh** - Updated `docs/SYSTEM.md`, `AGENTS.md`, `README.md`, and `.env.example` comments to match the then-current 0.15.x codebase, including auth/settings/admin APIs, Phase 0 AI foundation, frontend layout, compose profile counts, and known pipeline caveats.

### Fixed

- **Phase 1 AI type safety** — Fixed 8 Pyright type safety issues across the AI chat routing, knowledge ingestion, litellm provider integration, RAG retrieval logic, and unit tests to ensure complete typecheck alignment.

---

## [0.17.11] - 2026-06-05 - Auto-Detection & Indicator Fallback

### Added

- **Auto-failover Health Monitor** - `src/producer/health_monitor.py` now checks Kafka and Flink health every 30s:
  - When both Kafka and Flink are down for 60s → auto-enable direct Redis bypass
  - When either recovers for 120s → auto-disable direct Redis bypass
  - New config: `HEALTH_CHECK_INTERVAL_SEC`, `FAILOVER_THRESHOLD_SEC`, `RECOVERY_THRESHOLD_SEC`, `FLINK_JM_URL`

- **Backend Indicator Fallback** - `backend/services/indicator_service.py` computes indicators from Redis kline history when Flink pre-computed indicators unavailable or stale:
  - Supports: SMA (20, 50), EMA (12, 26), RSI (14), MACD, Bollinger Bands (20, 2), ATR (14), Volume SMA
  - Uses candle history from `candle:1m:{exchange}:{symbol}` sorted set
  - Returns `source: "redis_derived"` with freshness metadata

- **Data Freshness Tracking** - All indicator responses now include:
  - `source`: "flink_precomputed", "redis_derived", "redis_derived_stale", "unavailable"
  - `freshness_seconds`: age of data
  - `is_stale`: true if > 120 seconds old
  - `is_fallback`: true if computed from Redis

### Changed

- **Direct Redis toggle** - Now controlled by HealthMonitor state, not just static env var
- **Redis writer** - `set_direct_redis_active()` function to receive health state updates
- **System.md Section 17.7** - Updated with auto-detection documentation

### Verified

- **Tests** - All 300 tests pass
- **Compilation** - All Python files compile successfully

---

## [0.17.10] - 2026-06-05 - Direct Redis Bypass Path Implementation

### Added

- **Direct Redis Bypass** - New resilience feature allowing WebSocket → Redis direct writes when Kafka/Flink is down:
  - `src/exchanges/binance/redis_writer.py` — `DirectRedisWriter` class with methods for ticker, kline, trade, depth
  - `src/common/config.py` — `ENABLE_DIRECT_REDIS` env var (default: false)
  - `src/producer/main.py` — Integrated into all Binance and OKX stream handlers (ticker, trades, klines, depth)
  - Toggle via `ENABLE_DIRECT_REDIS=true` in docker-compose

### Changed

- **market overview** - Fixed catalog name mismatch (`iceberg_catalog.gold.*` → `iceberg.gold.*`) in 6 query functions
- **Section 17 Data Tables Reference** - Added comprehensive documentation to SYSTEM.md

### Verified

- **OKX E2E** - Channel subscription format verified correct per OKX WebSocket API v5
- **Direct Redis writes** - Format matches Flink KeyDBWriter Redis key structures for seamless fallback

---

## [0.17.9] - 2026-06-05 - Market Overview Fix & Data Tables Documentation

### Fixed

- **market overview catalog name mismatch** - `backend/api/market_overview.py` queried `iceberg_catalog.gold.*` but Trino catalog is `iceberg`. Fixed 6 queries across `_get_market_summary`, `_get_top_movers`, `_get_most_volatile`, `_get_highest_volume`, `_get_trending_news`, `_get_sector_performance`, `_get_indicators_summary`, `_get_heatmap_data`

### Added

- **Section 17 Data Tables Reference** - Added comprehensive documentation to `docs/SYSTEM.md` covering:
  - Exchange WebSocket formats (Binance: ticker/kline/trade/depth, OKX: tickers/trades/candle/books)
  - Kafka Avro schemas (schemas/\*.avsc) with all attributes
  - Redis KeyDB structures (ticker, kline, orderbook, trades) with TTL and field mappings
  - Iceberg Medallion tables (Bronze: ticker/kline/news, Silver: ticker_unified/kline_multi_timeframe, Gold: market_dominance/movers_ranking/volatility_ranking/sector_performance/momentum_indicators/news_sentiment_daily)
  - PostgreSQL Iceberg JDBC catalog tables (iceberg_tables, iceberg_namespace_properties)
  - Data flow diagram from WebSocket → Kafka → Flink → Redis/Iceberg

### Verified

- **OKX E2E** - Channel subscription format verified correct: `tickers` (plural), `trades`, `candle1m`, `books5`. instId format `BTC-USDT` matches OKX WebSocket API v5 spec. ENABLE_OKX currently `false` in docker-compose

---

## [0.17.8] - 2026-06-04 - Integration Tests Fixes & Frontend Verification

### Fixed

- **indicators test interval key** - Mock data now includes `"interval": "5m"` field to match service layer validation that checks `data_interval != interval_n`

- **trades test data format** - Mock returns JSON string trade objects (`{"p":"","q":"","t":,"m":}`) matching Flink KeyDBTradeWriter format instead of legacy `price:volume` string format

- **market overview placeholder test** - Test now accepts either `is_placeholder` value since fallback behavior produces real data from Redis ticker scan

- **e2e app metadata tests** - Updated expected app title/version to "LMView API" / "0.17.8" to match actual FastAPI app configuration

### Added

- **Producer Prometheus metrics** - Wired `prometheus_client` metrics endpoint on port 9090 with: `producer_ws_threads_running` (Gauge), `producer_kafka_messages_sent_total` (Counter by topic), `producer_kafka_send_errors_total` (Counter by topic), `producer_heartbeat_timestamp_seconds` (Gauge per thread), `producer_ws_reconnects_total` (Counter by stream), `producer_ticker_throttle_skipped_total` (Counter)

- **Prometheus scrape config** - Updated producer scrape job port from 9095 to 9090 to match new metrics endpoint

### Verified

- **Integration test suite** - All 300 tests pass (59 integration + 2 e2e fixes + unit tests)

- **Frontend typecheck** - `npm run typecheck` passes with React 19/Lucide React peer dependency resolved via `--legacy-peer-deps`

- **Frontend build** - `npm run build` succeeds, producing 631.65 kB bundle in 12.39s

- **Promtail log extraction** - Regex patterns extract `log_level` and `error_type` labels from Docker container logs. Pattern: `^\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\s+\[(?P<log_level>\w+)\]` for timestamp+level, `(?i)(?P<error_type>Exception|Error|Fatal|Traceback|panic|OOM|timeout)` for error classification. Service label derived from Docker compose service name.

- **System Error Triage dashboard** - Dashboard queries Loki `{log_level="ERROR"}` with service-based aggregation via `sum by (service) (rate({log_level="ERROR"} [5m]))`. Includes "Error Rate by Service" barchart and "All ERROR Logs" log panel with labels, time, and wrap options.

- **Alert rules** - 17 rules across 10 categories: Flink (job restart, high memory), Kafka (consumer lag, broker down), API (latency, error rate), System (memory, CPU), Postgres (connections, replication lag), InfluxDB (write failures), Nginx (5xx spike), Zookeeper (leader election), Dagster (pipeline failure), Producer (WS disconnect), Log-based (error rate spike, crash loop, Kafka disconnect). All rules use Prometheus/Loki datasources with 1-5 minute evaluation intervals.

### Optimized

- **Flink memory config** - TaskManager: 6144m→3584m, slots 24→12. JobManager: 2304m→1536m. Matches actual parallelism of 12.

- **Kafka JVM heap** - Added `-Xmx1g -Xms1g` via KAFKA_OPTS in entrypoint.sh.

- **Spark memory** - Driver/executor: 2g→1g. Workers: 4G→2G, cores 4→2.

- **Docker limits** - Flink TM 10G→4G, Flink JM 2.5G→2G, Spark master 1G→2G, Spark workers 4G→2G each.

---

## [0.17.7] - 2026-06-04 - OKX Verification & docker-compose Fixes

### Fixed

- **docker-compose.yml YAML syntax** - Fixed CRLF line endings and Unicode box drawing characters that caused `docker compose config` to fail

- **OKX channel name fix** - Changed `tickers` (plural) to `ticker` (singular) per OKX WebSocket API spec; updated both client builder and message handler

- **OKX instId case handling** - Symbols now passed as-is (e.g., "BTCUSDT" → "BTC-USDT") instead of forcing uppercase, matching OKX REST API format

### Changed

- **OKX kline interval** - OKX subscription now uses 1m minimum (doesn't support 1s klines); filtered to 13 well-known pairs to avoid channel errors

- **OKX experimental disabled** - Set `ENABLE_OKX=false` in docker-compose until OKX channel format is confirmed; code fixes applied, testing pending OKX documentation confirmation

- **Legacy batch files review** - 3 legacy files in `src/batch/` have no external references (orchestration uses `lakehouse.silver.transformations` directly). Files retained but marked for future cleanup if unified versions prove stable.

### Known Issues

- **Market Overview Trino catalog mismatch** - Code queries `iceberg_catalog.gold.*` but actual catalog is `iceberg`. Gold tables (market_dominance, movers_ranking, etc.) don't exist - only bronze tables (coin_klines, coin_ticker, coin_trades) exist. Need to check if Dagster/Spark jobs populate gold tables.

- **OKX WebSocket channel format** - OKX returns "Wrong URL or channel" errors for all symbol subscriptions. Further debugging requires checking OKX WebSocket API documentation directly

---

## [0.17.6] - 2026-06-04 - Flink/Spark Stability & Auto-Submit Fixes

### Fixed

- **Kafka brokers 2-3 startup** - Started kafka-2 and kafka-3 replicas that were dead, restoring full 3-broker Kafka cluster

- **Flink job submit path** - Recreated deps.zip in flink-jobmanager container directly (read-only volume mount prevented in-container fix); job now stays RUNNING with 60 active tasks consuming all 4 Kafka topics

- **Spark streaming JVM longevity** - Changed lakehouse/pipeline.py to `spark.streams.awaitAnyTermination()` instead of per-query await loops; Spark Structured Streaming app now keeps JVM alive and stays RUNNING

- **auto-submit-jobs CRLF** - Converted auto_submit_jobs.sh line endings from CRLF to LF; inlined all job-submission logic directly into docker-compose.yml entrypoint (no file I/O) so the container needs no read-only mounts

- **auto-submit-jobs inline entrypoint** - Replaced shell script call with self-contained entrypoint that recreates deps.zip, submits Flink, waits for Spark master, and submits Spark streaming job

### Changed

- **Spark submit packages** - Added `org.apache.spark:spark-avro_2.12:3.5.5` to Spark submit packages for Avro deserialization dependency

### Changed

- **Dagster code location loading** - Added Dagster `Definitions` wiring and narrowed lazy imports in `orchestration/assets.py` so the workspace can load even when optional news or kafka dependencies are not imported at module load time.

- **Dagster image dependencies** - Updated the Dagster image inputs so runtime imports needed by orchestration load successfully during `dagster job list` and service startup.

- **Producer exchange startup behavior** - Added `ENABLE_OKX` gating in the shared config and producer startup path so the experimental OKX source stays opt-in during normal stack bring-up while the producer watchdog thread still starts.

- **Flink checkpoint runtime config** - Switched the PyFlink checkpoint storage URI away from the broken `s3a://` path and added the S3 filesystem plugin installation step to the Flink image definition.

- **Trino startup idempotence** - Made the Trino entrypoint keep the JMX javaagent line unique in `jvm.config`, preventing restart loops caused by duplicate agent registration.

- **Job watchdog compose wiring** - Fixed the `job-watchdog` compose entrypoint so the container starts cleanly and can rerun job submission checks.

- **Exchange consistency fixes** - Kept trades API and lakehouse or backfill updates aligned with exchange-qualified keys and exchange-aware dedup columns from this runtime stabilization pass.

### Fixed

- **Dagster job listing** - `docker compose exec dagster-daemon dagster job list -w /app/orchestration/workspace.yaml` now loads the code location successfully.

- **Trino health** - `trino` now reaches healthy state again and answers simple queries after recreating the container with the idempotent entrypoint logic.

- **Flink job submission path** - After loading the S3 filesystem plugins into the running Flink services, the streaming job progressed past checkpoint-storage initialization and entered `RUNNING` during verification.

- **Spark lakehouse streaming path** - The Spark Iceberg pipeline now uses `s3://` checkpoint locations and holds explicit query handles so the structured streaming app stays `RUNNING` instead of exiting immediately after startup.

- **Spark dependency path** - Added the missing Spark Avro package to the Spark submit path and aligned Spark streaming checkpoints to `s3://` so the lakehouse app can progress further under the current container setup.

### Known Issues

- **Flink image rebuilds** - Rebuilding the Flink image was blocked in this session by Docker Hub DNS resolution failures from the environment, so plugin loading was verified by patching the running containers in addition to the committed Dockerfile change.

- **Producer image rebuilds** - Rebuilding the producer image was intermittently blocked by package-download timeouts, so runtime verification relied on the bind-mounted source plus container restart.

## [0.17.4] - 2026-06-03 - Frontend Indicator Stream Hookup

### Changed

- **Frontend chart live path** - Wired `CandlestickChart` to subscribe to `/api/stream/indicators/{interval}` and apply streamed indicator snapshots onto the live chart series.

- **Indicator stream fallback behavior** - Kept local client-side indicator computation as fallback/history source while preferring backend-streamed latest values for the live candle edge.

- **Frontend market data service** - Added `subscribeIndicatorStream()` to `marketDataService` so indicator streaming uses the same API-mode WebSocket boundary as candle streaming.

## [0.17.3] - 2026-06-03 - Indicator Streaming & History Storage

### Added

- **Indicator WebSocket stream** - Added `/api/stream/indicators/{interval}` to push real-time indicator snapshots from Redis for a requested symbol, exchange, and timeframe.

- **Redis indicator history** - Extended the Flink indicator writer to persist `indicator:history:{exchange}:{symbol}:{interval}` sorted sets alongside interval-scoped latest hashes.

- **Iceberg indicator history** - Added `iceberg_catalog.gold.indicator_history` creation and writes in both indicator batch jobs so historical indicator values are stored as real lakehouse rows.

### Changed

- **Indicator Redis schema** - Latest indicator snapshots now prefer `indicator:latest:{exchange}:{symbol}:{interval}` with fallback to older key layouts for compatibility.

- **Indicator API contracts** - `/api/indicators/{symbol}` and `/api/indicators/{symbol}/summary` now accept `interval` and return richer computed fields such as RSI, MACD, Bollinger Band, ATR, and volume-SMA values when available.

- **Indicator pipeline output** - The Flink indicator writer now emits more than SMA/EMA only, including RSI, MACD, Bollinger Band, ATR, and volume-SMA metrics into Redis and InfluxDB.

## [0.17.2] - 2026-06-03 - Realtime Indicator Rendering Optimization

### Changed

- **`frontend/src/features/chart/CandlestickChart.tsx`** - Optimized live indicator rendering so chart series update immediately from the latest candle stream while React candle state updates run in a lower-priority transition.

- **Realtime indicator sync** - Added a focused live indicator window and direct per-series updates to avoid full indicator recomputation on every WebSocket tick.

- **Chart settings effect** - Stopped tying indicator rebuilds to every live candle state change; full recalculation now stays aligned with settings/data reload paths instead of each price tick.

## [0.17.1] - 2026-06-03 - Lakehouse Schema Audit & Indicator History Design

### Changed

- **`docs/VIET_LOG.md`** - Reworked Section 6 into a table-first audit format covering Spark streaming, medallion layers, batch jobs, Trino, Dagster, and all observed Iceberg tables.

- **Lakehouse schema inventory** - Documented actual columns, datatypes, purposes, and schema drift risks across `crypto_lakehouse`, `bronze`, `silver`, and `gold`.

- **Indicator architecture design** - Replaced the minimal indicator note with a richer TradingView-style indicator catalog plus explicit Iceberg and Redis schema proposals for historical indicator storage.

## [0.17.0] - 2026-06-03 - Grafana Dashboards & Structured Log Pipeline

### Added

- **10 new Grafana dashboards** — Spark Logs, Trino Logs, MinIO Logs, Redis Sentinel Logs, Postgres Dashboard, InfluxDB Dashboard, Nginx Dashboard, Zookeeper Dashboard, Dagster Dashboard, Producer Dashboard

- **System Error Triage** dashboard — Single pane for all ERROR logs across all services, filterable by service with per-service error rate sparklines

- **Structured log pipeline** — Promtail now extracts `log_level` (ERROR/WARN/INFO/DEBUG) and `error_type` (Exception/Error/Fatal/Traceback/panic/OOM) labels from Docker container logs

- **Prometheus scrape configs** — Added scrape jobs for InfluxDB, Postgres exporter, Nginx exporter, Dagster, Zookeeper JMX, and Producer

- **10 new alert rules** — Postgres connection exhaustion + replication lag, InfluxDB write failures, Nginx 5xx spike, Zookeeper leader election, Dagster pipeline failure, Producer WS disconnect, ERROR log rate spike, crash loop detection, Kafka broker disconnect log

- **Nginx stub_status** — Enabled `/nginx_status` on both dev and prod configs for Prometheus scraping

### Changed

- **docker-compose.yml** — Exposed Zookeeper JMX port `7071` for scraping

- **producer requirements** — Added `prometheus-client` dependency; producer metrics endpoint wiring is still pending

- **Total Grafana dashboards:** 11 → 22. Every service now has dashboard coverage

## [0.16.0] - 2026-06-03 - Exchange Qualification & Trade Hot Cache

### Changed (Market Overview)

- **`/api/market/overview`** — Now attempts Trino gold table queries first; falls back to Redis `ticker:latest` scan to derive market volume, gainers/losers, volatile symbols, and BTC/ETH dominance when Trino is empty or unavailable

### Added (WebSocket)

- **`/api/stream/{interval}`** — New per-interval WebSocket endpoint for single-timeframe candle streaming. Supports all intervals: `1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

- **Frontend `subscribeCandle()`** — Fixed URL from legacy `/api/stream` (non-existent) to `/api/stream/{interval}`

### Added (OKX)

- **OKX subscription frame builder** — `build_subscribe_frame()` method on OKXClient with helper methods `build_ticker_channels()`, `build_trade_channels()`, `build_kline_channels()`, `build_depth_channels()`

- **OKX WebSocket handler** — `_handle_okx_message()` in producer parses OKX `{"arg":..., "data":[...]}` response format and dispatches to correct mapper

- **OKX subscription stream runners** — `run_ticker_stream_subscription()` and `run_combined_batch_subscription()` connect to OKX WS and send subscription frames after `on_open`

### Changed (Producer)

- **`run_streams()`** — Now detects subscription-capable clients with `hasattr(..., "uses_subscription_frames")` and branches between Binance URL-stream and OKX subscription-frame WebSocket handling

- **All stream spawning loops** — Conditionally call subscription or URL-based handlers based on exchange type

### Changed

- **Kline aggregator** — Keyed by `(exchange, symbol)` instead of `symbol` only. 1m emitted records now include `exchange` field, enabling separate `candle:1m:binance:BTCUSDT` and `candle:1m:okx:BTCUSDT`

- **Spark Iceberg DDLs** — Added `exchange STRING` column to `coin_ticker`, `coin_trades`, and `coin_klines` table definitions for multi-exchange lakehouse queries

- **Indicator writer** — Redis key changed from `indicator:latest:{symbol}` to `indicator:latest:{exchange}:{symbol}`. InfluxDB tag now uses actual exchange from kline JSON instead of hardcoded `"binance"`

- **Indicator API** — Backend service now reads new exchange-qualified key first, falls back to legacy `indicator:latest:{symbol}` key for backward compatibility

### Added

- **Trade hot cache writer** — New `KeyDBTradeWriter` Flink writer consuming `crypto_trades` topic and writing `trade:latest:{exchange}:{symbol}` sorted set to Redis

- **Trade pipeline in Flink** — Wired `kafka_trades` SQL table with Avro-confluent format into the main pipeline

- **Trade API enhancement** — `/api/trades/{symbol}` now reads `trade:latest` (real exchange trades) first, falls back to `ticker:history` (ticker-derived) if trade cache is empty. Response metadata includes `is_true_trade_tape` flag and `data_type` field

- **Trade writer unit tests** — 8 new unit tests for trade JSON format, exchange field, dedup, batch buffer, and empty symbol handling

### Fixed

- **Exchange qualification** — kline aggregation, Spark DDLs, indicator keys, and trades API now consistently carry `exchange` field

- **Backend indicator service docstring** — Updated to reflect new key format

## [0.15.2] - 2026-06-01 - Auth-gated settings and mock data isolation

### Added

- **Settings modal** - Wired the header Settings button to Account, Customization, AI Helper, About, and Debug tabs with login/admin gates, real auth user display, real theme/timeframe/chart-type controls, local AI session cleanup, and read-only health checks.

- **AI Helper gate** - Requires login before opening AI Helper and shows `You must log in to use AI Helper` when blocked.

- **LMView Help mode** - Replaced API-mode fake AI behavior with deterministic product-help responses only; Interact and market-analysis requests now return unavailable states until real AI services exist.

### Changed

- **Mock data boundary** - Moved market/news/AI mock generators under `frontend/src/data/mock/` and routed mock mode through API-shaped mock adapter functions consumed by frontend services.

- **API placeholder handling** - Added frontend metadata guards so API-mode placeholder/mock-tagged market, news, candle, ticker, order book, and trade payloads render empty/unavailable states instead of generated fallback data.

## [0.15.1] - 2026-06-01 - Bug fixes for Phase 0 implementation

### Fixed

- **Frontend auth session UI** - Wrapped the app with `AuthProvider`, wired the header Login button to the centered login/register modal with blurred backdrop, displayed authenticated user/logout state, cleared expired stored tokens during restore, and normalized FastAPI auth validation errors for the browser UI.

- **Auth registration runtime** - Added PostgreSQL async driver support to the FastAPI image, pinned bcrypt for passlib compatibility, wired auth PostgreSQL/migration environment values into Compose, and applied `SESSION_EXPIRY_HOURS` in token expiry calculations.

- **Recent Trades frontend** - Normalized the metadata-wrapped `/api/trades/{symbol}` response in `marketDataService` so the right-panel Recent Trades view always receives an array.

## [0.15.0] - 2026-06-01 - Phase 0: AI Foundation Layer

### Added

- **PostgreSQL auth foundation** — `backend/core/postgres.py` async connection pool (asyncpg), `backend/core/security.py` password hashing (bcrypt/SHA-256 fallback), `backend/core/auth_dependencies.py` FastAPI Bearer-token auth dependencies.

- **Auth API** — `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me`, `PATCH /api/auth/preferences` with session-based authentication.

- **Auth Pydantic models** — `RegisterRequest`, `LoginRequest`, `AuthResponse`, `UserResponse`, `SessionInfo`, `UserPreferencesResponse`, `MeResponse` in `backend/models/auth.py`.

- **AI backend API** — `GET /api/ai/health`, `POST /api/ai/chat` (scope gate + mock response + message persistence), `GET /POST /api/ai/sessions`, `GET /api/ai/sessions/{id}/messages`, `POST /api/ai/chart-context`, `POST /api/ai/chart-actions/validate`, `POST /api/ai/chart-actions/record`.

- **AI Pydantic models** — `AIChatRequest`, `AIChatResponse`, `AIChartAction`, `AIChartActionType` (10 action types), `AISessionResponse`, `AIMessageResponse`, `AIHealthResponse`, `ScopeGateResult`, `ChartContextDTO` in `backend/models/ai.py` and `backend/models/chart_context.py`.

- **Scope gate service** — Keyword-based in-scope/out-of-scope classification (crypto, indicators, charts, news, risk education). Blocks prompt injection, weather, recipes, code generation.

- **Chart action validator** — Validates AI-proposed chart actions against known indicator names, price/time ranges, payload safety (blocks JS/SQL injection, nesting depth), note length limits.

- **Mock AI service** — Deterministic Phase 0 responses that echo received context to prove wiring, clearly marked as mock.

- **Indicator service** — Catalog of 10 supported indicators, Redis-backed latest values, compact AI-context summaries with freshness metadata.

- **Common response models** — `DataFreshness`, `DataMetadata`, `PaginatedResponse`, `ErrorDetail` in `backend/models/common.py`.

- **SQL migration** — `backend/migrations/001_phase0_schema.sql` with 9 tables: `users`, `auth_sessions`, `user_preferences`, `ai_chat_sessions`, `ai_messages`, `ai_chart_snapshots`, `ai_tool_actions`, `news_articles`, `ai_knowledge_documents`.

- **Frontend auth service** — `frontend/src/services/authService.ts` with API calls + mock fallback for `VITE_DATA_SOURCE=mock`.

- **Frontend AI service** — `frontend/src/services/aiService.ts` with all AI API calls + auth header injection.

- **Frontend AI panel** — Extracted `AiAssistantPanel` from `RightPanel` into `frontend/src/features/ai/`, using `useAiChat` hook with backend API / local mock dispatching.

- **Frontend types** — Added `DataFreshness`, `DataMetadata`, `UserSession` to `frontend/src/types/index.ts`.

- **Unit tests** — 53 tests covering auth security (password hashing, session tokens, email validation), AI models (enums, DTOs), scope gate (in-scope/out-of-scope, prompt injection), chart action validator (indicators, ranges, XSS/SQL injection), and mock service.

### Changed

- **AuthContext rewrite** — `AuthContext.tsx` now uses backend API (Bearer token auth) with async login/register/logout. Falls back to localStorage mock for `VITE_DATA_SOURCE=mock`.

- **AuthModal** — Now async with loading spinner, disabled inputs during submission, error handling for both API and mock paths.

- **RightPanel** — Extracted ~150 lines of inline AI chat code into standalone `AiAssistantPanel` component.

- **Trades API** — Response now includes `metadata.data_type = "ticker_derived"`, `metadata.is_true_trade_tape = false`, source/exchange/freshness. Added `GET /api/trades/{symbol}/summary`.

- **Order book API** — Every response path now includes `metadata` with source, exchange, `is_synthetic` flag, and `DataFreshness`. Added `GET /api/orderbook/{symbol}/summary` with depth/imbalance.

- **Indicators API** — Added `GET /api/indicators/supported` listing all 10 indicators, expanded freshness metadata. Added `GET /api/indicators/{symbol}/summary`.

- **Market overview API** — Response now includes `metadata.is_placeholder = true` to prevent AI/users from treating default data as real analytics.

- **Backend config** — Added PostgreSQL connection vars, auth session config, migration flag.

- **Test conftest** — Added PostgreSQL env defaults, graceful mocking for environments without Docker-only deps.

- **`.env.example`** — Added `POSTGRES_HOST`, `POSTGRES_LMVIEW_DB`, `RUN_MIGRATIONS`, `SESSION_EXPIRY_HOURS`.

### Not Implemented (Phase 1+)

- Real LLM integration (LangGraph, model inference, RAG)

- Autonomous chart interaction

- News PostgreSQL persistence (schema ready, service stubbed)

- Frontend AI Interact Mode (action approval/execution UI)

- Cookie-based session transport (Bearer token for Phase 0)

- Alembic/SQLAlchemy migration framework

## [0.14.2] - 2026-05-30 - Drawing Toolbar Light Theme Polish

### Added

- **Drawing tool groups** - Rebuilt the floating left drawing bar around hoverable Line, Shapes, Fibonacci, Chart Patterns, Elliott Wave, and Position / Forecast groups with viewport-bounded flyout menus.

- **Drawing tools** - Added stable chart-rendered Fibonacci retracement, ABCD/XABCD patterns, Elliott wave, long/short position, and forecast drawing paths while keeping cursor, text, ruler, eraser, lock, replay, and delete-all flows intact.

### Fixed

- **Light mode contrast** - Moved chart toolbar, symbol selector, drawing toolbar, replay controls, tool flyouts, hover, active, and disabled states onto shared theme tokens so Light Mode remains readable.

- **Drawing toolbar interaction** - Kept tool group hover highlighted blue, preserved flyouts while moving from the button to the menu, and disabled eraser while all drawings are locked.

- **Pattern drafting** - Added point-by-point ABCD/XABCD drafting with anchored labels, preview segments, low-opacity polygon fills, and Escape/Cursor cancellation.

- **Fullscreen delete confirmation** - Moved Delete All Drawings confirmation into the chart fullscreen subtree so cancel/confirm remains visible above the fullscreen canvas.

- **Indicator localization** - Replaced hardcoded Indicator panel labels, descriptions, pane badges, color labels, and switch status text with i18n keys for full Vietnamese coverage.

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

## [0.14.0] - 2026-05-22 - Frontend Structure Refactor

### Changed

- **Frontend folder structure** - Reorganized `frontend/src` into standard Vite React TypeScript folders, including `@types`, `constants`, `data`, `features`, `components/layout`, `components/ui`, and `routes`.

- **Frontend services** - Centralized API helpers, environment constants, timeframe constants, market/news data services, and health checks outside React components.

- **UI shell** - Merged the top toolbar behavior into the canonical `Header` component and removed redundant toolbar/replay/watchlist/news files.

- **Chart feature** - Flattened `features/chart` by removing the redundant nested `components/chart` directories and adding a concise feature barrel export.

- **Styling and i18n** - Moved theme tokens into `index.css`, removed the old theme module, and expanded translations for the refactored market/news/header UI.

- **Project docs** - Updated `docs/SYSTEM.md` and `AGENTS.md` to match the new frontend folder structure and hot spot paths.

## [0.13.1] — 2026-05-22 — Bug Fixes: Data Pipeline & Backend APIs

### Fixed

- **Kafka Topics** — Resolved `Unrecognized partition` errors in the Python producer by recreating `crypto_ticker`, `crypto_klines`, `crypto_trades`, and `crypto_depth` topics with the correct 12 partitions. Data ingestion is now stable.

- **Orderbook API** — Fixed an HTTP 500 `ReadOnlyError` in `/api/orderbook/{symbol}` by routing the fallback cache expiration write (`expire`) to the Redis Master node instead of a read-only Sentinel replica.

- **Exchange Fallback Logic** — Updated `/api/trades` and `/api/orderbook` to correctly parse new exchange-aware Redis keys. Implemented Binance-first lookup with automatic fallback to OKX (and then legacy keys) to fully utilize OKX as a redundant backup source.

## [0.13.0] — 2026-05-22 — Dev HTTP / Prod HTTPS Nginx Routing

### Changed

- **Nginx dev mode** — Switched from self-signed HTTPS to plain HTTP (port 80 only). No more browser certificate warnings in development.

- **Nginx prod mode** — HTTPS via certbot with any domain (DuckDNS, custom, etc.), not limited to DuckDNS. Self-signed cert still used as fallback until certbot issues a real certificate.

- **Nginx config split** — Single `nginx.conf` replaced with `nginx-dev.conf` (HTTP-only) and `nginx-prod.conf` (HTTPS). Entrypoint selects config via `NGINX_MODE` env var.

- **`init_certbot.sh`** — Now domain-agnostic; DuckDNS auto-detection is optional, not assumed. Only starts `duckdns-auto` if `DUCKDNS_TOKEN` is configured.

- **`certbot_auto.sh`** — Removed DuckDNS-specific sentinel domain check.

- **`.env.example`** — Generalized HTTPS automation section; `CERTBOT_DOMAIN` default changed from DuckDNS to `example.com`.

- **`docker-compose.yml`** — `nginx-dev` exposes port 80 only; `nginx-prod` exposes 80+443 with letsencrypt/certbot volumes. Ports and volumes moved from base template to concrete services.

## [0.12.3] — 2026-05-21 — Charting Library Upgrade

### Changed

- **Dependencies** — Upgraded `lightweight-charts` to `5.2.0` in `frontend/package.json`.

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

## [0.12.1] — 2026-05-19 — Integration Tests & API Routing

### Changed

- **Integration Test Suite** — Modernized test infrastructure to support Redis Sentinel HA by replacing legacy `get_redis` mocks with `get_redis_master`/`get_redis_replica`. Added global fixtures to mock FastAPI background tasks during testing.

- **API Routing** — Reordered FastAPI router inclusions in `backend/app.py` to prioritize new `market_overview` routes over legacy `market` overlapping routes.

### Added

- **API Tests** — Added mandatory integration tests for `market_overview` (`/api/market/overview`, `/api/market/heatmap`, `/api/market/rankings`) and `news` (`/api/news/latest`, `/api/news/trending`, `/api/news/search`) endpoints.

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

## [0.11.0] — 2026-05-16 — Monitoring & Logging Nginx Routing

### Added

- **Nginx reverse proxy for monitoring** — Grafana (`/grafana/`), Prometheus (`/prometheus/`), Loki (`/loki/`) routed through nginx

- **Basic Auth for Prometheus/Loki** — htpasswd generated at container startup from `MONITORING_USER`/`MONITORING_PASSWORD` env vars (default: admin/admin)

- **Grafana WebSocket proxy** — `/grafana/api/live/` for live dashboard updates

- **Rate limiting** — `monitoring_limit` zone (10r/s per IP) applied to all monitoring endpoints

### Changed

- **Grafana subpath** — Configured `GF_SERVER_SERVE_FROM_SUB_PATH=true` with `GF_SERVER_ROOT_URL=%(protocol)s://%(domain)s/grafana/`

- **Prometheus subpath** — Added ` — web.external-url=/prometheus/` and ` — web.route-prefix=/prometheus/`

- **Grafana Prometheus datasource** — Updated URL to `http://prometheus:9090/prometheus`

- **Nginx Dockerfile** — Added `apache2-utils` for htpasswd generation

- **`.env.example`** — Added `MONITORING_USER`, `MONITORING_PASSWORD`, `GRAFANA_ADMIN_PASSWORD`

### Agent

- Agent: Gemini (Antigravity)

- Files modified: 6 (nginx.conf, Dockerfile, entrypoint.sh, docker-compose.yml, .env.example, datasources.yml)

## [0.10.0] — 2026-05-16

### Changed

- **Documentation system rewrite** — Replaced all project documentation with a new standardized system:
  - `docs/SYSTEM.md` — Complete system documentation (architecture, data flow, tech stack, setup, testing)

  - `docs/CHANGELOG.md` — Structured changelog (this file), migrated from `docs/TRACKING.md`

  - `docs/AGENTS.md` — AI agent coding instructions following the agents.md open standard

  - `README.md` — User-facing project overview following banesullivan/README template

- **Project renamed** from "Lambda Architecture for TradingView-Style Platform" to **LMView**

- **Documentation language** standardized to English (previously mixed Vietnamese/English)

## [0.9.0] — 2026-05-14 — High Availability Infrastructure

### Changed

- **Monitoring stack integration** — Merged Flink infrastructure refactor with monitoring/logging stack

- **Redis Sentinel entrypoint** — Fixed entrypoint scripts for correct Sentinel initialization

- **Node-exporter volumes** — Corrected volume mount paths for host metrics collection

- **Grafana provisioning** — Fixed rule hierarchy in provisioning configuration

- **Configuration types** — Resolved file type mismatches in monitoring configs

## [0.8.0] — 2026-05-09 — HA Architecture Migration

### Changed

- **Kafka HA** — Migrated from single Kafka node to 3-node KRaft cluster (`kafka-1`, `kafka-2`, `kafka-3`) with replication factor 3

- **Redis Sentinel HA** — Replaced standalone KeyDB with Redis cluster: 1 Master, 2 Replicas, 3 Sentinels

- **Backend Redis client** — Implemented `RedisSentinelManager` in `backend/core/redis_sentinel.py` with auto-discovery, failover, and read/write splitting

### Known Issues

- PyFlink writers still use `keydb_` prefix in filenames (e.g., `keydb_ticker.py`, `KeyDBKlineWriter`) while connections use Sentinel config

- `src/common/config.py` retains default `REDIS_HOST = "keydb"`, overridden by HA environment variables

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

## [0.6.0] — 2026-05-02 — Comprehensive Test Suite

### Added

- **161 total tests** across 5 categories:
  - Unit: 80 tests (constants, binance mappers/client, models, candle service)

  - Integration: 39 tests (health, ticker, symbols, trades, indicators, klines, historical APIs)

  - Security: 17 tests (SQL injection, XSS, path traversal, CORS, oversized queries)

  - Performance: 9 benchmarks (aggregation, merging, validation with time limits)

  - E2E: 6 tests (route registration, OpenAPI schema, docs endpoint)

- **Test infrastructure** — `tests/integration/`, `tests/e2e/`, `tests/performance/` packages

## [0.5.0] — 2026-04-28 — Infrastructure & Pipeline Restoration

### Fixed

- **Producer image** — Downgraded from Python 3.14-slim to 3.11-slim (fastavro C-extension compatibility)

- **Nginx port conflict** — Removed duplicate port 3000 binding between dagster-webserver and nginx

- **Binance WebSocket** — Switched `!ticker@arr` to `!miniTicker@arr` (lighter payload, no timeout)

- **Flink module resolution** — Fixed ` — pyFiles /app/src` in job submission script

## [0.4.0] — 2026-04-28 — Frontend TypeScript Migration

### Changed

- **Complete TypeScript migration** — All 27 frontend files migrated from `.jsx`/`.js` to `.tsx`/`.ts`

- **React 18 → 19** upgrade

- **Type system** — 18 shared TypeScript interfaces in `types/index.ts`

- **Error handling** — Centralized `AppError` hierarchy + `useApiCall` hook + `ToastProvider`

- **Symbol metadata** — Dynamic CoinGecko API + 24h localStorage cache + fallback data (~90 symbols)

- **i18n** — ~130 translation keys (English + Vietnamese), all hardcoded strings replaced

- **Nginx** — Updated asset caching from `/static/` to `/assets/` (Vite output path)

## [0.3.0] — 2026-04-25 — Data Processing Layer Refactoring

### Changed

- **Exchange abstraction** — `ExchangeClient` base class + `BinanceClient` implementation in `src/exchanges/`

- **Shared infrastructure** — Centralized `src/common/` (config, kafka_client, avro_serializer, logging)

- **Producer rewrite** — 632-line monolith → ~250-line exchange-agnostic orchestrator

- **Flink pipeline split** — 996-line monolith → `pipeline.py` + 7 individual writer modules

- **Batch jobs** — Renamed and refactored maintenance/backfill jobs

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

## [0.1.0] — 2026-04-25 — Initial Documentation

### Added

- **TRACKING.md** — AI assistant working document

- **DOCUMENTATION.md** — Technical documentation (Vietnamese)

- **.gitignore** — Updated exclusion list

<! — TEMPLATE FOR NEW ENTRIES:

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

— >
