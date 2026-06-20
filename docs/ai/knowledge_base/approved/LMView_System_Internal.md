# LMView System Architecture — Internal Reference

> **Document Type**: Internal System Documentation
> **Audience**: AI Assistant (for understanding system capabilities and limitations)
> **Classification**: Internal Only — Not for end-user consumption
> **Version**: 0.25.42+

---

## Overview

LMView is a Lambda Architecture cryptocurrency market data platform. This document describes the internal components, data flows, APIs, and technical implementation details necessary for the AI assistant to understand system capabilities and limitations.

---

## System Architecture Summary

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         LMView Lambda Architecture                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  Exchanges (Binance, OKX)                                              │
│         ↓ WebSocket                                                    │
│  Producer (Kafka serialization)                                        │
│         ↓ Avro messages                                                │
│  Kafka Topics: ticker, klines, trades, depth                          │
│         ↓                                                              │
│  ├─────────────────┬──────────────────────────────────────┐             │
│  │   SPEED LAYER   │    BATCH/LAKEHOUSE LAYER            │             │
│  │   Flink         │    Spark + Iceberg + MinIO + Trino │             │
│  │   ↓ Redis       │    ↓ MinIO/Iceberg                 │             │
│  │   ↓ InfluxDB    │    ↓ PostgreSQL (catalog)          │             │
│  └─────────────────┴──────────────────────────────────────┘             │
│         ↓                                                              │
│  FastAPI (REST + WebSocket)                                            │
│         ↓                                                              │
│  React Frontend                                                        │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## Core Services & Components

### 1. Producer (`src/producer/main.py`)

**Purpose**: Connects to exchange WebSocket APIs, subscribes to channels, serializes messages to Avro, and produces to Kafka.

**Exchange Connections**:
- **Binance** (always enabled) — `wss://stream.binance.com:9443/stream`
- **OKX** (opt-in via `ENABLE_OKX`) — `wss://ws.okx.com:8443/ws/v5/public`

**Subscribed Channels**:
- `ticker` — 24h rolling ticker, best bid/ask
- `klines` — OHLCV candles (all timeframes: 1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w)
- `trades` — Aggregate trade events
- `depth` — Order book snapshots and updates

**Kafka Topics** (4 topics, Avro serialization):
- `crypto_ticker`
- `crypto_klines`
- `crypto_trades`
- `crypto_depth`

**Message Key Schema**:
```python
key = {
    "exchange": "binance",
    "symbol": "BTCUSDT",
    "interval": "1m"  # for klines only
}
```

**Message Value Schema** (Avro):
- ticker: `price`, `bid`, `ask`, `volume_24h`, `change_24h`, `event_time`
- klines: `openTime`, `open`, `high`, `low`, `close`, `volume`, `closeTime`, `quoteVolume`, `trades`, `ignore`
- trades: `id`, `price`, `qty`, `quoteQty`, `time`, `isBuyerMaker`
- depth: `lastUpdateId`, `bids`, `asks`, `eventTime`

---

### 2. Apache Flink (`src/processing/pipeline.py`)

**Purpose**: Real-time stream processing with low-latency aggregations and state management.

**Job Types**:

#### Kline Aggregator
- Input: 1s kline records from Kafka
- Output: Aggregated candles for all timeframes (1m, 5m, 15m, 1h, 4h, 1d, 1w)
- Writes to:
  - Redis sorted set: `candle:{interval}:{exchange}:{symbol}` (ZSET with score = timestamp)
  - InfluxDB line protocol: `klines` measurement
  - Kafka topic: `aggregated_klines` (for Spark consumption)

**State Management**:
- Partial candles stored in Flink state (checkpointed)
- On interval roll: emit complete candle, clear state
- Deduplication: ZADD `XX` option prevents overwrites

**Important**: Kline aggregator preserves `exchange` field in all outputs.

#### Depth Processor
- Input: Depth updates from Kafka
- Output: Consolidated order book state
- Writes to Redis: `depth:{exchange}:{symbol}` (hash with bids/asks sorted)
- **Known gap**: Depth processing defaults `exchange` to "binance" in some code paths.

#### Ticker Writer
- Input: Ticker updates
- Writes to Redis: `ticker:latest:{exchange}:{symbol}` (hash)
- Also aggregates across exchanges: `ticker:aggregated:{symbol}`

#### Indicator Computations
- Pre-computes indicators from live kline stream
- Writes to Redis: `indicator:latest:{exchange}:{symbol}:{interval}` (hash)
- Indicators computed: SMA, EMA, RSI, MACD, Bollinger Bands, VWAP, Volume MA, Stochastic, MFI, ATR, Ichimoku, Supertrend, PSAR
- Freshness: ~100-500ms lag

---

### 3. Apache Spark (`orchestration/` + `src/lakehouse/`)

**Purpose**: Micro-batch processing for gold tables, backfills, and historical aggregations.

**Jobs**:

#### `lakehouse_pipeline.py`
- Reads from Kafka aggregated topics
- Writes to Iceberg tables in MinIO
- Tables: `coin_ticker`, `coin_klines`, `coin_trades`, `coin_depth`
- **Known gap**: Ticker dedup logic omits `exchange` field, merging all exchanges together.

**Iceberg Catalog**:
- Hadoop catalog: `s3://cryptoprice/iceberg` (used by Spark)
- JDBC catalog: `iceberg_catalog.gold` (used by Dagster/Trino)

#### Backfill Jobs
- `backfill_klines.py` — Historical kline backfill from Binance REST API
- `backfill_trades.py` — Historical trade backfill
- `backfill_depth.py` — Order book backfill

**Retention**:
- InfluxDB: 90 days (`INFLUX_1M_RETENTION_DAYS=90`)
- Iceberg: Indefinite (object storage)

---

### 4. Redis Sentinel

**Purpose**: Hot cache for sub-millisecond reads.

**Key Namespaces**:

#### Candles
- `candle:{interval}:{exchange}:{symbol}` — Sorted set (score = timestamp, value = JSON candle)
- Example: `candle:1m:binance:BTCUSDT`

#### Indicators
- `indicator:latest:{exchange}:{symbol}` — Hash (no interval)
- `indicator:latest:{exchange}:{symbol}:{interval}` — Hash with interval-specific values
- Fields: `sma20`, `sma50`, `ema12`, `ema26`, `rsi14`, `macd`, `macd_signal`, `macd_histogram`, `bb_middle`, `bb_upper`, `bb_lower`, `bb_width`, `volume_sma20`, `atr14`, `timestamp`, `interval`

#### Ticker
- `ticker:latest:{exchange}:{symbol}` — Hash with price, bid, ask, change, volume
- `ticker:aggregated:{symbol}` — Aggregated across exchanges (mid-price average)

#### Order Book
- `depth:{exchange}:{symbol}` — Hash with `bids` and `asks` arrays (sorted)
- `depth:s:{exchange}:{symbol}` — String for snapshot ID

#### Trade Cache
- `trade:latest:{exchange}:{symbol}` — Sorted set of recent aggregate trades (score = trade time)

#### Sessions & Auth
- `session:{token}` — User session data (JSON)
- `ai:session:{userId}` — Active AI chat sessions

---

### 5. InfluxDB

**Purpose**: Warm time-series storage for recent history (90 days).

**Measurements**:
- `klines` — OHLCV candles (tags: `exchange`, `symbol`, `interval`)
- `trades` — Individual trades (tags: `exchange`, `symbol`)
- `depth` — Order book snapshots (tags: `exchange`, `symbol`)

**Retention Policies**:
- `autogen` (default): 90 days
- Raw 1m candles: `INFLUX_1M_RETENTION_DAYS=90`

---

### 6. PostgreSQL

**Purpose**: Relational data — authentication, AI chat persistence, settings, catalog, vector store.

**Schemas**:

#### `auth`
- `users` — User accounts (email, hashed_password, role)
- `sessions` — Active sessions (token, user_id, expires_at)

#### `ai`
- `chat_sessions` — AI conversation sessions
- `chat_messages` — Individual messages (role, content, warnings, token counts)
- `chart_snapshots` — Chart context snapshots (symbol, timeframe, indicators, drawings)
- `action_metadata` — Proposed actions from Interact mode
- `knowledge_chunks` — RAG knowledge base documents (chunked text + embeddings)
- `retrieval_logs` — RAG query logs for observability

#### `settings`
- `user_settings` — User preferences (language, theme, notifications)

#### `catalog`
- `symbols` — Cryptocurrency catalog (symbol, name, category, exchange listings)

**pgvector**:
- `knowledge_chunks.embedding` — `vector(1536)` for OpenAI embeddings
- Index: `ivfflat` for cosine similarity search

---

### 7. FastAPI (`backend/`)

**Purpose**: REST and WebSocket API serving layer.

**REST Endpoints**:

#### Market Data
- `GET /api/ticker` — 24h ticker for all symbols or specific symbol
- `GET /api/klines` — OHLCV candles (supports limit, interval, start/end)
- `GET /api/klines/historical` — Historical candles (InfluxDB-backed)
- `GET /api/orderbook/{symbol}` — Order book snapshot
- `GET /api/trades/{symbol}` — Recent trades
- `GET /api/trades/{symbol}/aggregate` — Aggregate trade tape
- `GET /api/symbols` — Symbol catalog

#### Indicators
- `GET /api/indicators/supported` — List all supported indicators with parameters
- `GET /api/indicators/{symbol}` — Latest indicator snapshot
- `GET /api/indicators/{symbol}/series` — Indicator time series
- `GET /api/indicators/{symbol}/summary` — Compact summary for AI context

#### News
- `GET /api/news` — Latest news with sentiment
- `GET /api/news?symbol=BTCUSDT` — Symbol-specific news
- `GET /api/news/trending` — Trending symbols by mentions

#### Market Overview
- `GET /api/market/overview` — Comprehensive market snapshot (gainers, losers, sectors, heatmap)

#### AI
- `POST /api/ai/chat` — Send message to AI assistant
- `GET /api/ai/chat/{sessionId}` — Get chat history
- `POST /api/ai/action/propose` — Propose UI action (Interact mode)
- `POST /api/ai/action/approve/{actionId}` — Approve proposed action
- `POST /api/ai/action/reject/{actionId}` — Reject proposed action

#### Health
- `GET /api/health` — Service health with latency checks

**WebSocket Endpoints**:

#### `/ws/market/{symbol}`
- Streams real-time: candles, ticker, trades, order book updates
- Message format:
```json
{
  "type": "candle" | "ticker" | "trade" | "depth",
  "data": { ... },
  "freshness": {
    "source": "flink" | "redis" | "synthetic",
    "is_stale": false,
    "freshness_seconds": 0.1
  }
}
```

#### `/ws/ai`
- AI chat streaming responses (Server-Sent Events style)
- Also streams action proposals in Interact mode

---

### 8. React Frontend (`frontend/`)

**Structure**:
- `src/features/chart/` — CandlestickChart component (lightweight-charts)
- `src/features/ai/` — AI Assistant panel (Ask/Interact modes)
- `src/features/settings/` — Settings modal
- `src/services/` — API clients (marketDataService, aiService, authService)
- `src/types/` — TypeScript interfaces
- `src/data/mock/` — Mock data adapters for `VITE_DATA_SOURCE=mock`

**Key Components**:

#### CandlestickChart
- Renders multi-timeframe candles
- Overlays indicators (SMA, EMA, RSI, MACD, etc.)
- Drawing tools layer (data-space anchored)
- Crosshair and tooltip
- Supports all chart types (candles, line, area, Heikin-Ashi, Renko, etc.)

#### AIAssistantPanel
- Ask Mode: Chat interface with context awareness
- Interact Mode: Action proposal cards with approve/reject
- Bilingual (i18n: en/vi)

---

## Data Freshness Model

All critical data responses include a `freshness` object:

```typescript
interface DataFreshness {
  source: string;           // "flink", "redis", "influx", "trino", "synthetic", "placeholder", "unavailable"
  exchange?: string;        // Exchange name if applicable
  event_time?: number;      // Unix timestamp ms of the data event
  last_updated?: string;    // ISO timestamp when this snapshot was generated
  freshness_seconds?: number; // Age of data in seconds
  is_stale: boolean;        // True if exceeds staleness threshold
  is_fallback: boolean;     // True if using fallback source
  warnings: string[];       // Human-readable warnings
}
```

**Staleness Thresholds** (by data type):
- Candles: 120 seconds
- Indicators: 120 seconds
- Order Book: 30 seconds
- Trades: 3600 seconds (1 hour)
- News: 43200 seconds (12 hours)
- Market Overview: N/A (placeholders flagged differently)

---

## API Error Handling

**Standard error response**:
```json
{
  "detail": "Error message",
  "code": "ERROR_CODE"  // optional
}
```

**Common HTTP Codes**:
- `200` — Success
- `400` — Invalid parameters (symbol format, interval, limit)
- `404` — Symbol not found or no data available
- `429` — Rate limit exceeded
- `500` — Internal server error
- `503` — Service unavailable (downstream dependency down)

---

## WebSocket Connection

**Connection URL**: `ws://localhost:8000/ws/market/{symbol}`

**Authentication**: Query parameter `?token={session_token}`

**Message Flow**:
1. Client connects with symbol and auth token
2. Server validates session
3. Server subscribes to Redis pub/sub channels for that symbol
4. Real-time messages pushed as they arrive
5. Client can send `{"type": "ping"}` for heartbeat (optional)

**Reconnection**: Client should implement exponential backoff reconnection.

---

## Indicator Computation Details

### Available Indicators

| Indicator | Category | Default Params | Series Support | Freshness Source |
|-----------|----------|----------------|----------------|------------------|
| SMA 20 | trend | period=20 | yes | Flink / Redis-derived |
| SMA 50 | trend | period=50 | yes | Flink / Redis-derived |
| EMA 12 | trend | period=12 | yes | Flink / Redis-derived |
| EMA 26 | trend | period=26 | yes | Flink / Redis-derived |
| RSI | momentum | period=14 | yes | Flink (computed) / Redis-derived |
| MACD | momentum | fast=12, slow=26, signal=9 | yes | Flink (computed) / Redis-derived |
| Bollinger Bands | volatility | period=20, std=2 | yes | Flink (computed) / Redis-derived |
| VWAP | volume | — | no | Flink (computed) |
| Volume MA | volume | period=20 | yes | Flink / Redis-derived |
| Stochastic | momentum | k=14, d=3 | no | Future |
| MFI | momentum | period=14 | no | Future |
| ATR | volatility | period=14 | yes | Flink / Redis-derived |
| Ichimoku | trend | conv=9, base=26, span=52, disp=26 | no | Flink (computed) |
| Supertrend | trend | period=10, multiplier=3 | no | Flink (computed) |
| Parabolic SAR | trend | step=0.02, max=0.2 | no | Flink (computed) |

**Notes**:
- "Series support" means the indicator can return time series data via `/series` endpoint.
- Indicators marked "computed" are calculated by Flink, not available from simple Redis lookups.
- Redis-derived fallback computes indicators on-demand from kline history.

---

## Configuration Environment Variables

### Backend (`backend/.env`)
```
RUN_MIGRATIONS=true
DATABASE_URL=postgresql://...
REDIS_URL=redis://redis:6379
INFLUX_URL=http://influxdb:8086
KAFKA_BOOTSTRAP_SERVERS=kafka:9092
AI_MODE=mock | real
AI_ENABLE_REAL_LLM=false
VECTOR_DB=pgvector
```

### Frontend (`.env`)
```
VITE_API_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
VITE_DATA_SOURCE=api | mock
VITE_DEFAULT_SYMBOL=BTCUSDT
```

---

## Service Dependencies Startup Order

1. PostgreSQL (wait for ready)
2. Redis Sentinel (wait for master elected)
3. Kafka + Zookeeper
4. InfluxDB
5. MinIO
6. Trino
7. Producer (needs Kafka)
8. Flink JobManager (needs Kafka)
9. Flink TaskManager (needs JobManager)
10. Spark (optional)
11. FastAPI backend (needs PostgreSQL, Redis, InfluxDB)
12. Nginx (needs FastAPI)
13. Frontend (served by Nginx)

---

## Known Caveats (AI-Actionable)

### 1. Exchange Field Loss in Depth
- The depth processing pipeline sometimes drops the `exchange` field, defaulting to "binance".
- AI should not assume depth data always reflects the requested exchange.
- Check `data.source` and `data.exchange` in responses.

### 2. Ticker-Derived Trade Fallback
- When `trade:latest:{exchange}:{symbol}` cache is empty, trades endpoint returns synthetic data derived from ticker price movements.
- Response includes `is_true_trade_tape: false`.
- AI must treat volume and direction from synthetic trades as approximate only.

### 3. Placeholder Market Overview
- When Trino gold tables are not populated, `/api/market/overview` returns placeholder data with `is_placeholder: true`.
- AI should note data incompleteness when this flag is set.

### 4. Indicator Value Discrepancies
- Flink uses Wilder's RSI and population std dev for Bollinger Bands.
- Spark batch uses SMA-based RSI and sample std dev.
- Values may differ slightly between real-time and historical views.

### 5. OKX Disabled by Default
- `ENABLE_OKX=false` in producer config.
- OKX kline interval mapping still needs normalization before production use.

### 6. No Heartbeat on WebSocket
- WebSocket connections have no ping/pong; idle connections may be dropped by proxies/browsers.
- Client should implement reconnection logic.

---

## Database Schemas (Relevant Tables)

### `ai.chat_sessions`
```sql
CREATE TABLE ai.chat_sessions (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL,
    title VARCHAR(255),
    mode VARCHAR(10) CHECK (mode IN ('ask', 'interact')),
    symbol VARCHAR(20),
    timeframe VARCHAR(10),
    exchange VARCHAR(20),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

### `ai.chat_messages`
```sql
CREATE TABLE ai.chat_messages (
    id UUID PRIMARY KEY,
    session_id UUID REFERENCES ai.chat_sessions(id),
    role VARCHAR(10) CHECK (role IN ('user', 'assistant', 'system')),
    content TEXT NOT NULL,
    warnings JSONB,
    token_input INT,
    token_output INT,
    estimated_cost_usd DECIMAL(10,6),
    created_at TIMESTAMP DEFAULT NOW()
);
```

### `ai.knowledge_chunks`
```sql
CREATE TABLE ai.knowledge_chunks (
    id SERIAL PRIMARY KEY,
    source_id VARCHAR(100) NOT NULL,
    chunk_index INT NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1536),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW()
);
-- Index: ivfflat (cosine similarity)
```

---

## Redis Key TTLs

| Key Pattern | TTL | Purpose |
|-------------|-----|---------|
| `session:*` | 24 hours | User sessions |
| `trade:latest:*` | 1 hour | Trade cache |
| `depth:*` | No TTL (always fresh) | Order book |
| `candle:*` | No TTL (cumulative) | Candle history |
| `indicator:latest:*` | No TTL | Indicator cache |

---

## API Rate Limits

Currently no hard rate limits, but:
- `/api/klines/historical` may be throttled if query range > 1 year
- `/api/market/overview` limited to 1 request per 10 seconds per IP (soft limit)
- WebSocket connections: max 5 per user session

---

## Testing & Validation

### Backend Tests
```bash
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. python -m pytest tests/ -m "unit or integration" -v
```

### Frontend Tests
```bash
cd frontend
npm run typecheck
npm run build
```

---

## Conclusion

This internal reference provides the AI assistant with sufficient technical context to understand LMView's capabilities, data provenance, and limitations. For user-facing explanations, refer to `LMView_Platform_Overview.md`.
