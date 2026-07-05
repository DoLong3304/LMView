# Speed Layer — Flink + Redis Sentinel + InfluxDB

Real-time data processing with sub-second latency.

## Flink 1.18.1

### Topology
- **JobManager**: 1 replica (worker node, 1GB heap)
- **TaskManager**: 2 replicas (worker node, 1536MB process size)
- **Parallelism**: 12 (matches Kafka partitions)

### Job: src/processing/pipeline.py

Consumes all 4 Kafka topics → processes → writes to Redis + InfluxDB.

| Kafka Topic | Flink Sink | Output |
|---|---|---|
| `crypto_ticker` | keydb_ticker | `ticker:latest:{ex}:{sym}` (String), `ticker:history:{ex}:{sym}` (Sorted Set) |
| `crypto_klines` | keydb_kline | `candle:1s:{sym}` (Sorted Set), `candle:1m:{ex}:{sym}` (Sorted Set) |
| `crypto_trades` | keydb_trades | `trade:latest:{ex}:{sym}` (List, capped 200) |
| `crypto_depth` | keydb_depth | `orderbook:{ex}:{sym}` (Hash) |
| — | indicators | SMA, EMA, RSI, MACD, Bollinger, Stoch, ATR, OBV, VWAP |
| — | influxdb_ticker | `market_ticks` InfluxDB measurement |
| — | influxdb_kline | `candles` InfluxDB measurement |
| — | whale_alert | Large trade detection → Redis + InfluxDB |
| — | liquidity_heatmap | Depth bucket aggregation → InfluxDB |

### 1s→1m Kline Aggregation

- Flink `KeyedProcessFunction` keyed by `(exchange, symbol)`
- Accumulates 1s candles into 1m windows
- On watermark (1m boundary): emits OHLCV candle
- Forward-fills close price when no data (low-volume symbols)

## Redis Sentinel 7.2

### Topology
- **1 master** (redis-master, port 6379)
- **2 replicas** (redis-replica-1/2, read replicas)
- **3 sentinels** (redis-sentinel-1/2/3, ports 26379-26381)
- Monitor name: `lmview_redis`

### Writers

| Writer | Source | Data | Frequency |
|---|---|---|---|
| `binance-kline-ws` | Binance WS (@kline_1s) | `candle:1s:*` | Real-time (~50ms batches) |
| `binance-ticker-ws` | Binance WS (@ticker) | `ticker:latest:*` | Real-time (~50ms batches) |
| `binance-kline-rest` | Binance REST /klines | `candle:1m:*` | Every 30s per symbol |
| `binance-depth-trades-rest` | Binance REST /depth, /trades | `orderbook:*`, `trade:latest:*` | Every 3s per symbol |
| Flink sinks | Kafka streams | All candle/ticker/trade/depth | ~500ms batch flushes |
| Producer DirectRedisWriter | Binance WS (failover) | All types (when Kafka down) | Real-time (bypass) |

### Key Sets

| Key Type | Examples | Purpose |
|---|---|---|
| `ticker:latest:{ex}:{sym}` | `ticker:latest:binance:BTCUSDT` | Latest 24hr ticker |
| `ticker:history:{ex}:{sym}` | Sorted set | Recent ticker samples |
| `candle:1s:{sym}` | Sorted Set per symbol | Recent 1s candles |
| `candle:1m:{ex}:{sym}` | Sorted Set per symbol | Recent 1m candles |
| `trade:latest:{ex}:{sym}` | List | Recent trades (capped 200) |
| `orderbook:{ex}:{sym}` | Hash | Current order book snapshot |
| `indicator:{ex}:{sym}:{interval}` | String | Computed indicator values |

### Access Pattern

- FastAPI reads via `redis_sentinel.py` (Sentinel-aware, auto-discovers master)
- Flink writes via `flink_redis_sentinel.py` (Sentinel-aware, BATCH flush 500ms)
- DirectRedisWriter writes directly to master (bypass path)

## InfluxDB 2.7

- Warm time-series storage (last 90 days)
- Bucket: defined in `INFLUX_BUCKET` env var
- Measurements: `market_ticks`, `candles`, `indicators`, `whale_alerts`, `liquidity_heatmap`
- Tags: `symbol`, `exchange`, `interval`
- Retention: handled by InfluxDB retention policy (default infinite for dev)

## Known Issues

- **Flink memory**: TaskManager reduced to 1536MB (from 2048MB) to prevent OOM on 4vCPU/16GB worker
- **Redis Sentinel + Swarm**: DNS-based service discovery works but sentinel CSV may contain container IPs
- **InfluxDB backfill**: Completed 90 days of 1m candles via `influx-backfill` one-shot service
