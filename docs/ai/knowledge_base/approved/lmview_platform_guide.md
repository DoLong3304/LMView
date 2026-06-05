---
title: LMView Platform Guide
domain: platform
language: en
source_type: system_doc
---

# LMView Platform Guide

## What is LMView?

LMView is a real-time cryptocurrency technical analysis platform built on Lambda Architecture. It provides live market data, interactive charting, technical indicators, and AI-assisted market analysis.

## Core Features

### Live Chart
- Real-time candlestick charts powered by lightweight-charts.
- Supported timeframes: 1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w.
- Chart types: candlestick, bar, line, area.
- Chart export with OHLCV metadata.
- Fullscreen mode with all controls.

### Technical Indicators
- SMA (Simple Moving Average): 20, 50, 200 periods
- EMA (Exponential Moving Average): 12, 26, 50 periods
- RSI (Relative Strength Index): 14 period
- MACD (Moving Average Convergence Divergence)
- Bollinger Bands
- VWAP (Volume Weighted Average Price)
- ATR (Average True Range)
- Stochastic Oscillator
- Ichimoku Cloud
- Supertrend
- Parabolic SAR
- Volume MA

### Drawing Tools
- Trendlines, rays, and extended lines
- Rectangles, circles, and triangles
- Fibonacci retracement
- ABCD and XABCD harmonic patterns
- Elliott Wave
- Long/short position tools
- Text annotations
- Ruler measurement

### Market Data
- Real-time ticker data from Binance (primary) and OKX (experimental).
- Watchlist with activity-based sorting.
- Order book visualization with depth analysis.
- Recent trades display (note: ticker-derived, not true trade tape).

### AI Assistant (Phase 1)
- Ask Mode: Educational technical analysis support.
- Chart context awareness: The AI sees your current chart state.
- RAG knowledge base: Grounded responses from curated knowledge.
- Bilingual: Supports English and Vietnamese.
- Risk-aware: Always includes educational disclaimers.

## Data Limitations

### Important Caveats
1. **Market overview** may show placeholder data. Check metadata flags.
2. **Trade data** is ticker-derived, not a true exchange trade tape.
3. **Order book** data may be stale, from REST fallback, or synthetic.
4. **News/sentiment** data is in-memory cached and may be unavailable.
5. **OKX data** is experimental — WebSocket handling may have gaps.
6. **Indicators** are computed from available candle data and may lag.

### Data Sources
- Speed layer: Kafka → Flink → Redis Sentinel → InfluxDB
- Batch layer: Kafka → Spark → Iceberg on MinIO → Trino
- Current primary exchange: Binance
- Experimental exchange: OKX

## Authentication
- Session-based authentication with Bearer tokens.
- User registration, login, and profile management.
- Settings for notifications, customization, and AI preferences.
- Admin panel for user management and app settings.
