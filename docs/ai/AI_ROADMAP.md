# AI Roadmap — LMView

## Current State: Phase 3 (Partial)

### Phase 1 — Foundation ✅ (v0.28–v0.29)
- Structured data injection into synthesis prompt (indicator tables, order book, support/resistance, news)
- RAG context formatting rewrite (credibility badges, source types, full chunk text)
- LLM-based intent classifier (async, JSON classification, fallback when rule-based confidence < 0.45)
- Response cache (LRU, SHA-256 key, TTL 30s price / 5min educational, max 100 entries)
- Multi-language support (character-level Vietnamese detection, "think in English → output in target language")
- Cache integrated into `run_chat_langgraph()` batch path; skipped for existing sessions and Interact mode

### Phase 2 — Expert + Pipeline Overhaul ✅ (v0.29)
- **Eliminated redundant tour planner LLM call**: Removed `TOUR_PLANNER_SYSTEM_PROMPT`, `_build_tour_context()`, `_llm_plan_tour()`, `_parse_json_response()`. `plan_tour()` uses `_intent_fallback_tour()` as primary path. File reduced 1000→679 lines. Saves ~5s+ latency per Interact request.
- **Step-by-step reasoning chain** in synthesis Interact mode policy: WHY → WHAT shows → WHAT means → LOOK FOR. Enforces explanation quality over action description.
- **Expert parallelism optimization**: Skip RAG for simple price queries (≤2 meaningful words beyond "price"/"current").

### Phase 3 — Interact Mode Redesign (Current)
- **`highlight_contextual_zone` tool**: 13 zone types (breakout, support_test, divergence, etc.) with direction bias + candle_count. Frontend maps to color-coded chart region. Preserves existing `highlight_section` (UI panel dimming) — this is additional.
- **Structured TA-based tour augmentation**: Tour planner reads structured expert outputs (RSI oversold/overbought → reversal zone, MACD crossovers → trend push, volume spikes → volume_spike zone, candlestick patterns → reversal zone) instead of keyword matching on synthesis text.
- **Remaining**: Better action proposal flow with user approval chaining, improved tour step navigation, multi-action sequences in single response.

### Phase 4 — RAG / Knowledge Base Overhaul ✅ (Assessed — Minimal Changes Needed)

**Assessment**: System is functional. 18 sources across LMView, crypto education, TA, on-chain, DeFi, risk management. Embedding model `all-MiniLM-L6-v2` (384-dim) works. Hybrid search (60/40 vector/keyword) with BM25 fallback + RRF reranking exists.

**Changes made**:
- Fixed SQL `param_idx` bug in pure vector search path — `score_filter` and `order_expr` now built at USE time (not definition time), so parameter indices stay correct when metadata filters (language, domain, tags) precede them.

**Deferred (good enough)**:
- Embedding model upgrade (bge-m3, e5) — current MiniLM adequate for 18 sources
- Cross-lingual retrieval — `plainto_tsquery` hardcoded to English; would need multilingual tsquery config
- Source credibility decay — no stale-source evidence
- Vietnamese KB sources — system handles VI via separate language path

### Phase 5 — Frontend Rewrite (Planned)
- Chat component extraction (dedicated AiChat component, not inline in panel)
- Tour interaction overhaul (clickable step indicators, skip/replay per step, mini-map overlay)
- Action UX consolidation (unified toolbar, approval/rejection animations)
- AI action debug window production hardening (persist state, filterable log)

### Phase 6 — FinBERT + Observability (Planned)
- Financial sentiment model (FinBERT) for news/headlines
- Vietnamese sentiment expansion with crypto-specific glossary
- Model artifact versioning and observability (freshness, latency, null rate, drift)
- Training data and labels in Iceberg (not just Redis)

## Non-Goals (By Design)
- Auto-trading or direct order execution
- Guaranteed price predictions
- Raw SQL/JS/shell execution
- Browser automation
- API-key rotation to bypass quotas
- Bypassing user approval for chart actions

## Completed Phases Detail

### Phase 1 — Foundation
- **Structured data injection**: Synthesis prompt receives both data tables AND narrative content via `_build_context_sections()` and `_format_indicator_table()`
- **RAG formatting**: Chunks include `credibility_level`, `source_type`, `review_status`. Max 5 chunks. Conflict resolution: "If KB conflicts with your training, PREFER KB."
- **Intent router LLM fallback**: `_llm_classify_intent()` calls actual LLM with JSON prompt when rule-based confidence < 0.45. Routes: technical_analysis, market_data, news_sentiment, knowledge_query, chart_action, general.
- **Response cache**: LRU with SHA-256 key `(message, symbol, timeframe, indicators, language, mode)`. TTL 30s/5min. Cache stats endpoint.
- **Multi-language**: Vietnamese detection via character heuristic (>2% VI chars). "Think in English first, then translate" instruction.
- **Deploy**: `--services` flag for targeted rebuild. `Makefile` swarm-deploy-services target.

### Phase 2 — Expert Pipeline
- **Tour planner**: Deterministic fallback covers 80%+ of cases (orderbook, compare, news, analyze, indicators, trendlines, S/R, tour demo). No LLM call = 0 extra latency.
- **Interact reasoning chain**: Every chart action includes WHY→WHAT shows→WHAT means→LOOK FOR. Example-driven.
- **RAG skip**: Simple price queries skip pgvector. Reduces unnecessary Redis/vector calls.

### Phase 3 — Interact Redesign (Current Sprint)
- **`highlight_contextual_zone` tool parameters**: zone_type (13 enum values) required, label required, message optional, direction optional (bullish/bearish/neutral), candle_count optional (default 5).
- **Zone color mapping**: Bullish→green, bearish→red, neutral→yellow. Zone_type→emoji/label mapping in frontend handler.
- **Region estimation**: Frontend maps candle_count→percentage width relative to ~40 visible candles. Anchors to latest candles (right side).
- **TA augmentation mapping** in tour planner:
  - RSI oversold/overbought → reversal_candles zone
  - MACD bullish/bearish crossover → trend_push zone
  - High volume → volume_spike zone
  - Candlestick patterns → reversal_candles or recent_action zone
