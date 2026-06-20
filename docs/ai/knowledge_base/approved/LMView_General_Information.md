# LMView Platform Overview

> **Document Type**: User-Facing Platform Introduction
> **Audience**: End users, AI assistant context, new users
> **Version**: 0.25.42+ | **Review Status**: Ready for Review

---

## What is LMView?

**LMView** is a professional-grade, real-time cryptocurrency technical analysis platform. It delivers live market data, advanced charting, technical indicators, and AI-powered analysis tools for traders who need precision and speed.

Built on a **Lambda Architecture**, LMView processes millions of price updates per second while maintaining sub-second chart responsiveness and years of historical data accessibility.

---

## Core Capabilities

### Real-Time Market Data

LMView connects directly to cryptocurrency exchanges and provides:

| Data Type | Update Frequency | Latency | Sources |
|-----------|------------------|---------|---------|
| **Ticker** | 300ms | <100ms | Binance primary, OKX optional |
| **Candles** | 1s to 1w | <500ms | Multi-timeframe aggregation |
| **Order Book** | 100ms | <200ms | Full depth with live updates |
| **Trades** | Real-time | <100ms | Aggregate trade tape |
| **News** | 5-minute cycles | 5-15min | Multi-source with sentiment |

### Multi-Exchange Support

- **Binance** — Full production support (primary)
- **OKX** — Experimental, opt-in via configuration

### Supported Timeframes

`1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`

All timeframes share synchronized data; switching is instant.

---

## Charting Features

### Chart Types

- **Candlestick** — Standard OHLC with body/wick colors
- **Bars** — OHLC bar chart
- **Line** — Close price line
- **Area** — Filled area under price line
- **Heikin-Ashi** — Smoothed candlestick variant
- **Renko** — Brick-based price action (configurable brick size)
- **Line Break** — Price block chart (configurable lookback)
- **Kagi** — Trend-based line chart (configurable reversal)
- **Point & Figure** — Box reversal chart

### Technical Indicators

LMView provides **16+ built-in indicators**, all available on any timeframe:

#### Trend Indicators
- **SMA** — Simple Moving Average (periods: 20, 50, customizable)
- **EMA** — Exponential Moving Average (periods: 12, 26, customizable)
- **Ichimoku Cloud** — Complete Ichimoku Kinko Hyo system
- **Supertrend** — Trend following with ATR-based bands
- **Parabolic SAR** — Trend direction and reversal points

#### Momentum Indicators
- **RSI** — Relative Strength Index (default 14, overbought/oversold configurable)
- **MACD** — Moving Average Convergence Divergence with signal and histogram
- **Stochastic** — Stochastic Oscillator (K, D lines configurable)
- **MFI** — Money Flow Index (volume-weighted RSI)

#### Volatility Indicators
- **Bollinger Bands** — Standard deviation channels (default 2σ)
- **ATR** — Average True Range (default 14)

#### Volume Indicators
- **Volume** — Raw volume bars with color coding
- **Volume MA** — Volume moving average overlay

#### Specialized
- **VWAP** — Volume-Weighted Average Price (intraday only)

All indicators include:
- Configurable colors and line widths
- Real-time updates synchronized with candle data
- Freshness metadata (source: Flink precomputed or Redis-derived fallback)

---

## Drawing Tools

LMView includes **40+ drawing tools** organized in categories:

### Lines
- Trendline, Ray, Extended Line
- Horizontal Line, Horizontal Ray
- Vertical Line
- Angle Line, Disjoint Angle

### Shapes
- Rectangle, Rotated Rectangle
- Triangle, Ellipse
- Arrow, Polyline
- Price Range

### Fibonacci Tools
- Fibonacci Retracement (standard levels: 0%, 23.6%, 38.2%, 50%, 61.8%, 78.6%, 100%, 127.2%, 161.8%)
- Fibonacci Extension
- Fibonacci Channel
- Fibonacci Arcs
- Fibonacci Spiral
- Fibonacci Time Zones

### Gann Tools
- Gann Box
- Gann Fan (1x1, 1x2, 1x3, 1x4, 1x8, 2x1, 3x1, 4x1, 8x1 angles)
- Gann Square
- Gann Line

### Elliott Wave & Harmonics
- Elliott Wave labeling (impulse/corrective patterns)
- Harmonic ABCD patterns
- XABCD patterns

### Pitchfork Tools
- Standard Pitchfork
- Schiff Pitchfork
- Modified Pitchfork
- Inside Pitchfork

### Text & Annotations
- Text (anchored to data coordinates)
- Callout bubble
- Note
- Balloon
- Anchored Text

### Measurement Tools
- Ruler (price and time distance)
- Crossline
- Date Range
- Price Range Tool
- Risk/Reward visualization

### Position Tools
- Long Position (entry/stop/target)
- Short Position (entry/stop/target)

### Utilities
- Magnet (snap to price/time)
- Lock (prevent edits)
- Hide (temporary visibility toggle)
- Eraser (single drawing)
- Clear All

All drawings:
- Are stored in data-space coordinates (remain anchored during zoom/pan/timeframe changes)
- Persist across sessions (saved to backend storage)
- Support undo/redo history
- Can be locked, hidden, or deleted individually

---

## Order Book & Market Depth

Real-time order book visualization with:

- **Live updates** — 100ms refresh from exchange
- **Full depth** — Up to 1000 levels on each side
- **Cumulative depth** — Optional aggregated view
- **Spread indicator** — Real bid-ask spread
- **Depth heatmap** — Visual concentration of orders

Order book data sources:
- **Primary**: Flink live stream (sub-second)
- **Fallback**: REST snapshot (may be 30+ seconds stale)

---

## Trade Tape

Recent trades display with:

- **Real-time feed** — Every trade as it happens
- **Color coding** — Green for buys, red for sells
- **Size indicator** — Larger trades visually emphasized
- **Time stamps** — Exact execution time

Data sources:
- **Primary**: Redis trade cache (true exchange trades)
- **Fallback**: Ticker-derived synthetic trades (when real trades unavailable)

---

## News & Sentiment

Aggregated cryptocurrency news with:

- **Multi-source aggregation** — RSS feeds, API sources
- **Sentiment scoring** — Automated NLP analysis (-1 to +1)
- **Symbol extraction** — Auto-detection of mentioned cryptocurrencies
- **Trending topics** — Most mentioned symbols
- **Bilingual support** — English and Vietnamese content

**Important**: News sentiment is contextual, not a trading signal. Automated analysis may miss nuance.

---

## AI Assistant

LMView includes an AI assistant operating in two distinct modes:

### Ask Mode (Educational Analysis)

The AI acts as a technical analysis tutor:

- Explains indicators, chart patterns, and concepts
- Analyzes current chart context (symbol, timeframe, active indicators)
- References approved knowledge base documents
- Provides bilingual responses (English/Vietnamese)
- Always includes educational disclaimers

**Limitations**:
- No financial advice or price predictions
- No external API access during conversation
- Cannot execute trades
- No code execution

### Interact Mode (UI Orchestration)

The AI can propose safe UI actions:

- Add/remove indicators
- Change timeframes
- Navigate to other panels (order book, screener, watchlist)
- Highlight specific chart areas
- Start guided tours

**Safety**: All actions require explicit user approval. The AI never modifies settings without permission.

---

## Data Freshness & Quality

LMView provides transparency into data provenance:

| Data Type | Primary Source | Freshness | Fallback | Stale Threshold |
|-----------|----------------|-----------|----------|-----------------|
| Candles | Flink stream | <500ms | Redis/Influx | 2 minutes |
| Indicators | Flink precomputed | <500ms | Redis-derived | 2 minutes |
| Order Book | Flink stream | <200ms | REST snapshot | 30 seconds |
| Trades | Redis cache | <100ms | Ticker-derived | 1 hour |
| News | PostgreSQL | 5-15min | None | 12 hours |
| Market Overview | Trino gold tables | Scheduled | Redis ticker | None (placeholder) |

All API responses include `freshness` metadata indicating source, age, and fallback status.

---

## Technology Stack

### Backend
- **FastAPI** — REST and WebSocket API
- **PostgreSQL** — Auth, AI sessions, settings, catalog, pgvector for RAG
- **Redis Sentinel** — Hot cache (candles, indicators, order book)
- **InfluxDB** — Warm time-series storage (90-day retention)
- **Apache Kafka** — Message bus (4 topics, high-throughput)
- **Apache Flink** — Stream processing (real-time aggregations)
- **Apache Spark** — Batch processing (historical backfills, gold tables)
- **Apache Iceberg** — Table format for historical data
- **MinIO** — S3-compatible object storage
- **Trino** — SQL query engine for lakehouse

### Frontend
- **React 19** — Modern UI framework
- **TypeScript** — Type-safe development
- **lightweight-charts** — TradingView charting library
- **Tailwind CSS** — Utility-first styling
- **Vite** — Build tool and dev server

### Infrastructure
- **Docker & Docker Swarm** — Container orchestration
- **Nginx** — Reverse proxy and TLS termination
- **AWS EC2** — Cloud hosting (2-node cluster)
- **EFS** — Shared file storage

---

## Security & Privacy

- **Authentication** — Email/password with session tokens
- **No external data leakage** — AI assistant cannot access external websites during chats
- **Session isolation** — User data is strictly partitioned
- **No trade execution** — LMView is read-only; no API keys or exchange connections

---

## Getting Started

1. **Sign up** at the LMView web interface
2. **Select a symbol** — BTC/USDT is default
3. **Choose timeframe** — Click timeframe buttons (1m, 5m, 1h, etc.)
4. **Add indicators** — Use the indicator panel or ask AI to add them
5. **Draw on chart** — Select drawing tools from the toolbar
6. **Ask AI** — Open the AI assistant panel for analysis

---

## AI Assistant Quick Examples

**Ask Mode:**
- "What does RSI at 72 mean?"
- "Explain Bollinger Band squeeze"
- "Analyze the current BTC chart"
- "What's the market sentiment today?"

**Interact Mode:**
- "Add a 50-period SMA"
- "Switch to 4-hour timeframe"
- "Draw a trendline from this swing high to this swing low"
- "Show me the order book"

---

## Glossary Reference

For definitions of technical analysis terms, cryptocurrency terminology, and bilingual glossary, see the separate **Bilingual Glossary** document.

---

## Feedback & Support

LMView is actively developed. For issues, feature requests, or questions:

- Check the documentation at `docs/`
- Review known caveats in `docs/system/13-caveats.md`
- Report bugs with specific reproduction steps
