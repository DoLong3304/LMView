# LMView Data Caveats & Limitations

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.32.0+ | **Last reviewed**: 2026-07-01

---

## Purpose

This document helps the AI assistant provide honest, accurate analysis by documenting known data limitations. When these conditions are detected, the AI should acknowledge them in its response.

---

## Market Data Caveats

### Trade Data

- **True trade tape vs ticker-derived**: The `/api/trades/{symbol}` endpoint first checks for real aggregate trades in Redis (`trade:latest:{exchange}:{symbol}`). If no real trade cache exists, it falls back to ticker-derived price movements.
- **How to detect**: Response metadata includes `data_type` ("exchange_trade" vs "ticker_derived") and `is_true_trade_tape` (true/false).
- **Impact**: Ticker-derived trade data does not represent actual exchange trades. Volume and direction signals from ticker-derived data are approximate.

### Order Book Data

- **Source variety**: Order book data may come from live Flink stream, REST snapshot fallback, or synthetic generation.
- **Freshness matters**: REST fallback data may be 30+ seconds stale. The response includes `source` and `freshness` metadata.
- **Staleness levels**: Fresh (<10s), aging (10-60s), stale (60-300s), very_stale (>300s).

### Market Overview

- **Placeholder data**: When Trino gold tables are not populated, market overview falls back to Redis ticker cache. Placeholder data is flagged with `is_placeholder: true` in response metadata.
- **Gold table dependency**: Market dominance, sector performance, volatility rankings, and movers data require populated Iceberg gold tables via Trino queries.
- **Trino catalog**: Iceberg tables live under `iceberg_catalog.crypto_lakehouse.*` catalog namespace. The catalog name must match Spark's catalog name for cross-engine queries.

### Indicator Values

- **Flink real-time vs Spark batch**: Indicator values computed by Flink use true EMA, Wilder's RSI, and population standard deviation for Bollinger Bands. Spark batch uses SMA approximations and sample standard deviation. Values may differ slightly between sources.
- **Redis-derived fallback**: When Flink precomputed indicators are unavailable or stale (>120s), the backend computes indicators from Redis kline history. Fallback indicators are flagged with `source: "redis_derived"` and `is_fallback: true`.
- **Stale indicators**: Indicator responses include `freshness_seconds` and `is_stale` flags.

---

## News & Sentiment Caveats

### Sentiment Analysis

- **Automated scoring**: News sentiment is computed using automated NLP (VADER heuristic with keyword expansion). Scores are estimates, not human judgments.
- **Confidence levels**: Sentiment confidence depends on article count and sentiment agreement. Low article count or mixed sentiment produces low confidence.
- **Not a trading signal**: News sentiment should be treated as contextual information. Positive or negative sentiment is not proof of future price direction.
- **Score range**: -1.0 (most negative) to +1.0 (most positive). Values near 0 are neutral.

### News Freshness

- **5-minute fetch cycle**: News is fetched and persisted every 5 minutes. There may be a delay between an event and when it appears in LMView.
- **Stale news**: If the newest article is more than 12 hours old, the news context should be considered stale.

### Source Coverage

- **Multi-source**: LMView aggregates from multiple RSS/API news sources. Coverage varies by source availability.
- **Symbol extraction**: Symbols mentioned in articles are extracted algorithmically and may have false positives or missed mentions.

---

## Exchange-Specific Caveats

### Binance
- Primary data path. Most reliable and complete.
- Ticker heartbeat interval is 0.3 seconds for responsive chart updates.

### OKX
- Experimental support. WebSocket subscription handlers exist but are disabled by default.
- Kline interval mapping for Kafka records still needs normalization.
- Depth processing defaults exchange field to "binance" due to a known gap.

---

## AI Capability Caveats

### What the AI Can Do
- Provide educational technical analysis commentary
- Explain indicators, chart patterns, and market concepts
- Reference the current chart context and knowledge base
- Propose safe UI actions in Interact mode (with user approval)
- Provide bilingual responses (English/Vietnamese)
- Retain analytical context across conversation turns (session memory)
- Produce multi-step walkthroughs with auto-executed chart actions

### AI Knowledge Base
- RAG retrieval uses BAAI/bge-small-en-v1.5 embedding model (384-dim, ~33MB)
- Knowledge base: 23+ sources, 28+ documents, 1550+ chunks with embeddings
- Cross-encoder reranker (ms-marco-MiniLM-L-6-v2) re-ranks hybrid search results
- Hybrid search combines vector cosine similarity (60%) + BM25 keyword ranking (40%)
- Documents have credibility levels (verified, high, medium, draft) — AI prefers verified sources
- Embeddings are recomputed when the model is upgraded via the reindex API

### What the AI Cannot Do
- Execute trades or manage positions
- Access external websites or APIs during conversation
- Guarantee price predictions or specific outcomes
- Run code, SQL queries, or shell commands
- Bypass user approval for chart actions
- Access other users' data or sessions

### Financial Safety
- The AI always includes educational disclaimers
- Never claims guaranteed profits or returns
- Provides analysis ranges with confidence levels, not price targets
- Reminds users that cryptocurrency trading carries significant risk
- Past performance does not guarantee future results
