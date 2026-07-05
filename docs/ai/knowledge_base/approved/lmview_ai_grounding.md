# LMView AI Grounding — Platform Architecture & Capabilities

> **Metadata**: `review_status: approved` | `allowed_for_rag: true` | `internal_only: false`
> **Version scope**: 0.32.0+ | **Last reviewed**: 2026-07-01

---

## What is LMView?

LMView is a real-time cryptocurrency technical analysis platform. It provides live market data, candlestick charts, technical indicators, order book depth, recent trades, news with sentiment analysis, and an AI assistant for educational market analysis.

## Architecture Overview

LMView follows a Lambda Architecture with three layers:

- **Speed Layer** — Live exchange data flows through Kafka, Apache Flink, Redis Sentinel, and InfluxDB for sub-second updates.
- **Batch/Lakehouse Layer** — Historical and analytical data is processed by Apache Spark, stored in Apache Iceberg tables on AWS S3 (`lmview-iceberg-storage`), and queried through Trino.
- **Serving Layer** — FastAPI provides REST and WebSocket APIs; React 19 frontend renders the trading dashboard.

## Supported Exchanges

- **Binance** — Primary exchange. Full ticker, kline, trade, and depth data.
- **OKX** — Experimental. Code path exists but is disabled by default. Some data processing gaps remain.

## Supported Timeframes

`1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

## Key Features

### Market Data
- Real-time candlestick charts with multiple timeframes and chart types
- Technical indicators: SMA, EMA, RSI, MACD, Bollinger Bands, ATR, VWAP, Stochastic, MFI, Ichimoku, Supertrend, PSAR, Volume
- Order book depth visualization
- Recent trade tape
- Market overview with top movers, heatmap, sector performance

### News & Sentiment
- Multi-source news aggregation with sentiment analysis
- Symbol-specific sentiment tracking
- Trending symbols by mention count
- News sentiment is derived from automated analysis and should be treated as contextual information, not trading signals

### Drawing Tools
- 40+ drawing tools including trend lines, Fibonacci, Gann, pitchfork, Elliott wave
- Data-space coordinates for precision
- Persistence through chart storage service

### AI Assistant (Ask Mode)
- Educational technical analysis support
- Chart context awareness (current symbol, timeframe, indicators, candle data)
- Knowledge base grounding through approved RAG documents
- Financial safety disclaimers and risk warnings always included
- Bilingual support (English/Vietnamese)

### AI Assistant (Interact Mode)
- Same analysis capabilities as Ask Mode
- Can propose safe UI actions (indicator toggles, drawing tools, navigation, walkthroughs)
- Walkthrough mode: multi-step auto-executed analysis plans with step reset and recap
- All actions require user approval before execution
- Never executes trades or modifies positions

## Data Freshness

- **Redis candle data**: Updated in real-time via Flink (sub-second for 1s candles). 1s klines are also written directly to Redis by the producer, bypassing Kafka/Flink for maximum freshness.
- **Indicator data**: Flink precomputed indicators are live; Redis-derived fallback when precomputed is unavailable
- **Order book data**: Streamed through Flink; REST fallback may be 30+ seconds stale
- **Trade tape**: True exchange trades cached in Redis with 1-hour TTL; falls back to ticker-derived data
- **News data**: Fetched every 5 minutes and persisted in PostgreSQL
- **Market overview**: Trino gold tables updated by Dagster schedules; Redis ticker fallback may show placeholder data

## Limitations

- LMView does not execute trades or manage positions
- The AI assistant cannot access external websites or APIs during a conversation
- Indicator values may differ between Flink real-time and Spark batch computations due to different algorithmic approaches
- News sentiment scores are automated estimates and may not capture nuanced sentiment
- Market overview data may be placeholder when Trino gold tables are not yet populated
- Historical data availability depends on backfill status and InfluxDB retention
