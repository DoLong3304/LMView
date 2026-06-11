# CRYPTO PRICE DATA PIPELINE
## Báo Cáo Kỹ Thuật Toàn Diện — Kiến trúc Lambda cho Cryptocurrency Technical Analysis

**Phiên bản:** 0.23.0  
**Ngày cập nhật:** 2026-06-11  
**Kiến trúc:** Lambda Architecture (Speed Layer + Batch/Lakehouse Layer + Serving Layer)  
**Trạng thái:** Production

---

## MỤC LỤC

1. [Tổng quan luồng thu thập (Ingestion Layer)](#1-tổng-quan-luồng-thu-thập-ingestion-layer)
2. [Tầng Kafka (Broker Layer)](#2-tầng-kafka-broker-layer)
3. [Tầng xử lý real-time (Flink + Redis)](#3-tầng-xử-lý-real-time-flink--redis)
4. [Tầng Bronze (Spark Streaming)](#4-tầng-bronze-spark-streaming)
5. [Tầng Silver (Spark Batch)](#5-tầng-silver-spark-batch)
6. [Tầng Gold (Spark Batch)](#6-tầng-gold-spark-batch)
7. [Tổng kết độ trễ (End-to-End Latency)](#7-tổng-kết-độ-trễ-end-to-end-latency)
8. [Phụ lục](#8-phụ-lục)

---

## 1. Tổng quan luồng thu thập (Ingestion Layer)

### 1.1 Cấu hình nguồn dữ liệu

| Tham số | Binance | OKX |
|---------|---------|-----|
| **Số lượng mã** | Tối đa 200 mã (USDT spot) | 20 mã phổ biến |
| **Quy tắc lọc** | Đuôi USDT, trạng thái `TRADING` | Danh sách whitelist cố định |
| **WebSocket Endpoint** | `wss://stream.binance.com:9443/ws/` | `wss://ws.okx.com:8443/ws/v5/public` |
| **Protocol** | Combined Stream (symbol@stream) | Subscription Frame |

**Danh sách 20 mã OKX (whitelist cố định):**

```
BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT,
ADAUSDT, DOGEUSDT, AVAXUSDT, DOTUSDT, MATICUSDT,
LINKUSDT, SHIBUSDT, LTCUSDT, ATOMUSDT, UNICUSDT,
XLMUSDT, VETUSDT, ICPUSDT, FILUSDT, AAVEUSDT
```

### 1.2 Cơ chế Threading và phân luồng WebSocket

**Tổng số Thread WebSocket tối đa:** ~36 threads

| Stream | Binance Threads | OKX Threads | Symbols/Connection | Mục đích |
|--------|-----------------|-------------|-------------------|----------|
| **Ticker** (`!ticker@arr`) | 1 | 1 | Tất cả (200/20) | Gom toàn bộ mã |
| **Trades** (`@aggTrade`) | `ceil(200/25) = 8` | `ceil(20/25) = 1` | 25 | Chia nhóm |
| **Klines** (`@kline_1s`) | `ceil(200/25) = 8` | `ceil(20/25) = 1` | 25 | Chia nhóm |
| **Depth** (`@depth20@100ms`) | `ceil(200/15) = 14` | `ceil(20/15) = 2` | 15 | Tải nặng hơn |

**Thứ tự kích hoạt thread (staggered để tránh handshake burst):**

```
1. Prometheus Metrics Server (port 9090)
2. Kafka Producer initialization
3. Avro Schema registration → Schema Registry
4. Block chính: Ticker Stream (chờ 0s)
5. Trades threads: bắt đầu cách nhau 1 giây (staggered)
6. Klines threads: bắt đầu cách nhau 1 giây (staggered)
7. Depth threads: bắt đầu cách nhau 1 giây (staggered)
```

**Cơ chế throttle cho Ticker:**
- Chỉ gửi khi `price thay đổi` HOẶC `heartbeat >= 0.3 giây`
- Tránh spam khi giá đứng yên

### 1.3 Tần suất cập nhật từng stream

| Stream | Binance | OKX | Avro Topic |
|--------|---------|-----|------------|
| **Ticker** | Real-time (change/heartbeat 0.3s) | Real-time (change/heartbeat 0.3s) | `crypto_ticker` |
| **Trades** | Real-time (mỗi transaction) | Real-time (mỗi transaction) | `crypto_trades` |
| **Klines** | 1 giây/candle | 1 phút (OKX không hỗ trợ 1s) | `crypto_klines` |
| **Depth** | 100ms (20 bước giá) | Real-time subscription | `crypto_depth` |

### 1.4 Định dạng JSON thô từ Binance

#### 1.4.1 Ticker Stream (`!miniTicker@arr`)

```json
[
  {
    "e": "24hMiniTicker",
    "E": 1672531199000,
    "s": "BTCUSDT",
    "c": "16500.00",
    "o": "16600.00",
    "h": "16700.00",
    "l": "16400.00",
    "v": "1200.50",
    "q": "19800000.00",
    "b": "16499.00",
    "a": "16501.00",
    "p": "-100.00",
    "P": "-0.60",
    "n": 45678
  }
]
```

**Bảng trường dữ liệu Ticker gốc (Binance):**

| Trường gốc | Kiểu | Ý nghĩa |
|------------|------|---------|
| `e` | String | Tên sự kiện |
| `E` | Long | Event timestamp (ms) |
| `s` | String | Symbol (BTCUSDT) |
| `c` | String | Giá đóng cửa hiện tại |
| `o` | String | Giá mở cửa 24h |
| `h` | String | Giá cao nhất 24h |
| `l` | String | Giá thấp nhất 24h |
| `v` | String | Khối lượng base (24h) |
| `q` | String | Khối lượng quote (24h) |
| `b` | String | Best bid price |
| `a` | String | Best ask price |
| `p` | String | Biến động giá tuyệt đối 24h |
| `P` | String | Biến động giá % 24h |
| `n` | Long | Số giao dịch 24h |

#### 1.4.2 Aggregate Trades Stream (`{symbol}@aggTrade`)

```json
{
  "e": "aggTrade",
  "E": 1672531199000,
  "s": "BTCUSDT",
  "a": 123456789,
  "p": "16500.00",
  "q": "0.50000",
  "T": 1672531199000,
  "m": true
}
```

**Bảng trường dữ liệu Trades gốc (Binance):**

| Trường gốc | Kiểu | Ý nghĩa |
|------------|------|---------|
| `e` | String | Tên sự kiện (`aggTrade`) |
| `E` | Long | Event timestamp (ms) |
| `s` | String | Symbol |
| `a` | Long | Aggregate Trade ID |
| `p` | String | Giá khớp |
| `q` | String | Khối lượng khớp |
| `T` | Long | Trade timestamp (ms) |
| `m` | Boolean | Buyer là maker |

#### 1.4.3 Kline Stream (`{symbol}@kline_1s`)

```json
{
  "e": "kline",
  "E": 1672531199000,
  "s": "BTCUSDT",
  "k": {
    "t": 1672531190000,
    "T": 1672531199999,
    "s": "BTCUSDT",
    "i": "1s",
    "o": "16500.00",
    "c": "16501.00",
    "h": "16505.00",
    "l": "16498.00",
    "v": "120.50",
    "n": 456,
    "x": false,
    "q": "1980000.00"
  }
}
```

**Bảng trường dữ liệu Kline gốc (Binance):**

| Trường gốc | Kiểu | Ý nghĩa |
|------------|------|---------|
| `k.t` | Long | Kline start time (ms) |
| `k.T` | Long | Kline close time (ms) |
| `k.i` | String | Interval (1s/1m/1h/1d) |
| `k.o` | String | Open price |
| `k.c` | String | Close price |
| `k.h` | String | High price |
| `k.l` | String | Low price |
| `k.v` | String | Base volume |
| `k.n` | Long | Trade count |
| `k.x` | Boolean | Is closed |
| `k.q` | String | Quote volume |

#### 1.4.4 Depth Stream (`{symbol}@depth20@100ms`)

```json
{
  "lastUpdateId": 160,
  "bids": [["16499.00", "10.50"], ["16498.00", "5.25"]],
  "asks": [["16501.00", "8.00"], ["16502.00", "3.50"]]
}
```

### 1.5 Định dạng JSON thô từ OKX

#### 1.5.1 Ticker Channel (`tickers`)

```json
{
  "arg": {"channel": "tickers", "instId": "BTC-USDT"},
  "data": [{
    "instId": "BTC-USDT",
    "last": "50000.00",
    "lastSz": "0.01000",
    "askPx": "50001.00",
    "askSz": "1.50000",
    "bidPx": "49999.00",
    "bidSz": "2.00000",
    "open24h": "49500.00",
    "high24h": "50500.00",
    "low24h": "49000.00",
    "volCcy24h": "1000000000.00",
    "vol24h": "20000.00",
    "ts": "1609459200000"
  }]
}
```

#### 1.5.2 Trades Channel (`trades`)

```json
{
  "arg": {"channel": "trades", "instId": "BTC-USDT"},
  "data": [{
    "instId": "BTC-USDT",
    "tradeId": "123456789",
    "px": "50000.00",
    "sz": "0.01000",
    "side": "buy",
    "ts": "1609459200000"
  }]
}
```

#### 1.5.3 Kline Channel (`candle{interval}`)

```json
{
  "arg": {"channel": "candle1m", "instId": "BTC-USDT"},
  "data": [["1609459200000", "50000", "50500", "49500", "50200", "100", "5000000", "1"]]
}
```

**Ý nghĩa các phần tử array:**
| Index | Trường | Ý nghĩa |
|-------|--------|---------|
| `[0]` | ts | Start time (ms) |
| `[1]` | o | Open price |
| `[2]` | h | High price |
| `[3]` | l | Low price |
| `[4]` | c | Close price |
| `[5]` | vol | Base volume |
| `[6]` | volCcy | Quote volume |
| `[7]` | confirm | Closed flag (`0`/`1`) |

#### 1.5.4 Depth Channel (`books{level}`)

```json
{
  "arg": {"channel": "books5", "instId": "BTC-USDT"},
  "data": [{
    "asks": [["50001.00", "1.50", "0", "2"]],
    "bids": [["49999.00", "2.00", "0", "3"]],
    "ts": "1609459200000",
    "checksum": 123456
  }]
}
```

### 1.6 Tầng Mapping (Canonical Format)

#### 1.6.1 Binance Mappers

**Ticker Mapper (`map_ticker`):**

```python
{
    "event_time":           int(raw["E"]),              # Long
    "symbol":               str(raw["s"]),              # String
    "exchange":             "binance",                   # String (hardcoded)
    "close":                float(raw.get("c", 0)),     # Double
    "bid":                  float(raw.get("b", 0)),     # Double
    "ask":                  float(raw.get("a", 0)),     # Double
    "h24_open":             float(raw.get("o", 0)),     # Double
    "h24_high":             float(raw.get("h", 0)),     # Double
    "h24_low":              float(raw.get("l", 0)),     # Double
    "h24_volume":           float(raw.get("v", 0)),    # Double
    "h24_quote_volume":     float(raw.get("q", 0)),    # Double
    "h24_price_change":     float(raw.get("p", 0)),    # Double
    "h24_price_change_pct": float(raw.get("P", 0)),    # Double
    "h24_trade_count":      int(raw.get("n", 0)),      # Long
}
```

**Trade Mapper (`map_agg_trade`):**

```python
{
    "event_time":     int(raw["E"]),                # Long
    "symbol":         str(raw["s"]),                # String
    "exchange":       "binance",                     # String
    "agg_trade_id":   int(raw["a"]),                # Long
    "price":          float(raw["p"]),              # Double
    "quantity":       float(raw["q"]),              # Double
    "trade_time":     int(raw["T"]),                # Long
    "is_buyer_maker": bool(raw["m"]),               # Boolean
}
```

**Kline Mapper (`map_kline`):**

```python
{
    "event_time":   int(raw["E"]),                  # Long
    "symbol":       str(raw["s"]),                  # String
    "exchange":     "binance",                       # String
    "kline_start":  int(k["t"]),                    # Long
    "kline_close":  int(k["T"]),                    # Long
    "interval":     str(k["i"]),                    # String
    "open":         float(k["o"]),                  # Double
    "high":         float(k["h"]),                  # Double
    "low":          float(k["l"]),                  # Double
    "close":        float(k["c"]),                  # Double
    "volume":       float(k["v"]),                  # Double
    "quote_volume": float(k["q"]),                  # Double
    "trade_count":  int(k["n"]),                    # Long
    "is_closed":    bool(k["x"]),                   # Boolean
}
```

**Depth Mapper (`map_depth`):**

```python
{
    "event_time":     int(raw.get("E", int(time.time() * 1000))),   # Long
    "symbol":         str(raw.get("s", "")).upper(),               # String
    "exchange":       "binance",                                    # String
    "last_update_id": int(raw.get("lastUpdateId", raw.get("u", 0))), # Long
    "bids":           json.dumps([[float(p), float(q)] for p, q in raw.get("bids")]),  # String (JSON)
    "asks":           json.dumps([[float(p), float(q)] for p, q in raw.get("asks")]),  # String (JSON)
}
```

#### 1.6.2 OKX Mappers

**Symbol Normalization:**

```python
def normalize_symbol(inst_id: str) -> str:
    """Convert OKX instId (BTC-USDT) → canonical symbol (BTCUSDT)"""
    return inst_id.replace("-", "")
```

**Ticker Mapper (`map_ticker`) — có tính toán price_change:**

```python
{
    "event_time":           int(raw.get("ts", int(time.time() * 1000))),        # Long
    "symbol":               normalize_symbol(raw.get("instId", "")),            # String
    "exchange":             "okx",                                              # String
    "close":                float(raw.get("last", 0)),                          # Double
    "bid":                  float(raw.get("bidPx", 0)),                        # Double
    "ask":                  float(raw.get("askPx", 0)),                        # Double
    "h24_open":             float(raw.get("open24h", 0)),                       # Double
    "h24_high":             float(raw.get("high24h", 0)),                       # Double
    "h24_low":              float(raw.get("low24h", 0)),                        # Double
    "h24_volume":           float(raw.get("vol24h", 0)),                        # Double
    "h24_quote_volume":     float(raw.get("volCcy24h", 0)),                     # Double
    "h24_price_change":     last - open_24h,                                    # Double (tính toán)
    "h24_price_change_pct": (price_change / open_24h * 100) if open_24h > 0 else 0,  # Double
    "h24_trade_count":      0,                                                   # Long (OKX không cung cấp)
}
```

**Trade Mapper (`map_agg_trade`) — logic buyer_maker ngược:**

```python
{
    "event_time":     int(raw.get("ts", int(time.time() * 1000))),  # Long
    "symbol":         normalize_symbol(raw.get("instId", "")),      # String
    "exchange":       "okx",                                        # String
    "agg_trade_id":   int(raw.get("tradeId", 0)),                   # Long
    "price":          float(raw.get("px", 0)),                      # Double
    "quantity":       float(raw.get("sz", 0)),                      # Double
    "trade_time":     int(raw.get("ts", int(time.time() * 1000))), # Long
    "is_buyer_maker": raw.get("side", "") == "sell",                 # Boolean (ngược với Binance)
}
```

**Lưu ý quan trọng:** OKX dùng `side=buy` khi buyer là taker (maker = seller), nên logic `is_buyer_maker` ngược với Binance.

---

## 2. Tầng Kafka (Broker Layer)

### 2.1 Cấu hình Topic

| Topic | Partitions | Replication Factor | Retention | Compression |
|-------|-----------|-------------------|-----------|-------------|
| `crypto_ticker` | 12 | 3 | 48 giờ | LZ4 |
| `crypto_trades` | 12 | 3 | 48 giờ | LZ4 |
| `crypto_klines` | 12 | 3 | 48 giờ | LZ4 |
| `crypto_depth` | 12 | 3 | 48 giờ | LZ4 |

### 2.2 Quy tắc phân chia Partition

```python
partition_id = hash(symbol) % 12
```

**Mục tiêu:**
- Đảm bảo tất cả message cùng symbol từ cả hai sàn (Binance + OKX) luôn vào cùng partition
- Tương thích với 12 slots của Flink parallelism
- Tương thích với số cores của Spark executors

### 2.3 Avro Schema Definitions

#### 2.3.1 Ticker Avro Schema (`schemas/ticker.avsc`)

```json
{
  "type": "record",
  "name": "Ticker",
  "namespace": "com.cryptoprice",
  "fields": [
    {"name": "event_time",            "type": "long"},
    {"name": "symbol",                "type": "string"},
    {"name": "exchange",              "type": "string", "default": "binance"},
    {"name": "close",                 "type": "double"},
    {"name": "bid",                   "type": "double"},
    {"name": "ask",                   "type": "double"},
    {"name": "h24_open",             "type": "double"},
    {"name": "h24_high",             "type": "double"},
    {"name": "h24_low",              "type": "double"},
    {"name": "h24_volume",           "type": "double"},
    {"name": "h24_quote_volume",     "type": "double"},
    {"name": "h24_price_change",     "type": "double"},
    {"name": "h24_price_change_pct", "type": "double"},
    {"name": "h24_trade_count",      "type": "long"}
  ]
}
```

#### 2.3.2 Trade Avro Schema (`schemas/trade.avsc`)

```json
{
  "type": "record",
  "name": "AggTrade",
  "namespace": "com.cryptoprice",
  "fields": [
    {"name": "event_time",     "type": "long"},
    {"name": "symbol",         "type": "string"},
    {"name": "exchange",       "type": "string", "default": "binance"},
    {"name": "agg_trade_id",   "type": "long"},
    {"name": "price",          "type": "double"},
    {"name": "quantity",       "type": "double"},
    {"name": "trade_time",     "type": "long"},
    {"name": "is_buyer_maker", "type": "boolean"}
  ]
}
```

#### 2.3.3 Kline Avro Schema (`schemas/kline.avsc`)

```json
{
  "type": "record",
  "name": "Kline",
  "namespace": "com.cryptoprice",
  "fields": [
    {"name": "event_time",   "type": "long"},
    {"name": "symbol",       "type": "string"},
    {"name": "exchange",     "type": "string", "default": "binance"},
    {"name": "kline_start",  "type": "long"},
    {"name": "kline_close",  "type": "long"},
    {"name": "interval",     "type": "string"},
    {"name": "open",         "type": "double"},
    {"name": "high",         "type": "double"},
    {"name": "low",          "type": "double"},
    {"name": "close",        "type": "double"},
    {"name": "volume",       "type": "double"},
    {"name": "quote_volume", "type": "double"},
    {"name": "trade_count",  "type": "long"},
    {"name": "is_closed",    "type": "boolean"}
  ]
}
```

#### 2.3.4 Depth Avro Schema (`schemas/depth.avsc`)

```json
{
  "type": "record",
  "name": "Depth",
  "namespace": "com.cryptoprice",
  "fields": [
    {"name": "event_time",     "type": "long"},
    {"name": "symbol",         "type": "string"},
    {"name": "exchange",       "type": "string", "default": "binance"},
    {"name": "last_update_id", "type": "long"},
    {"name": "bids",           "type": "string"},
    {"name": "asks",           "type": "string"}
  ]
}
```

### 2.4 Confluent Avro Wire Format

```
┌─────────────────────────────────────────────────────────────┐
│  Wire Format: [magic_byte:1][schema_id:4][avro_binary:N]   │
├─────────────────────────────────────────────────────────────┤
│  Byte 0:       Magic byte (0x00)                            │
│  Bytes 1-4:     Schema ID (big-endian int32)                 │
│  Bytes 5-N:     Avro-encoded binary payload                 │
└─────────────────────────────────────────────────────────────┘
```

**Quy trình serialization:**
1. Serialize canonical dict → Avro binary
2. Prepend 5-byte Confluent header (magic + schema_id)
3. Send to Kafka

**Quy trình deserialization (Spark):**
```python
.selectExpr("substring(value, 6, length(value)-5) as avro_value")
.select(from_avro(col("avro_value"), avro_schema).alias("data"))
```

---

## 3. Tầng xử lý real-time (Flink + Redis)

### 3.1 Cấu hình Flink

| Tham số | Giá trị |
|---------|---------|
| Parallelism | 12 slots |
| Checkpoint Interval | 120 giây |
| Checkpoint Mode | EXACTLY_ONCE |
| State Backend | HashMapStateBackend |
| Restart Strategy | 5 failures per 10 minutes |
| Min Pause Between Checkpoints | 30 giây |
| Checkpoint Timeout | 120 giây |

### 3.2 Ticker Stream Processing

**Input:** Kafka topic `crypto_ticker`

**Output 1: KeyDB Hash (`ticker:latest:{exchange}:{symbol}`)**

| Field | Kiểu | Nguồn |
|-------|------|-------|
| `price` | Double | `close` |
| `bid` | Double | `bid` |
| `ask` | Double | `ask` |
| `volume` | Double | `h24_volume` |
| `change24h` | Double | `h24_price_change_pct` |
| `event_time` | Long | `event_time` |
| `exchange` | String | `exchange` |

**Output 2: KeyDB Sorted Set (`ticker:history:{exchange}:{symbol}`)**

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set (ZSET) |
| TTL | 600 giây (10 phút) |
| Score | `event_time` (ms) |
| Member | `"{price}:{volume}"` |

**Output 3: InfluxDB (`market_ticks` measurement)**

| Tag | Field |
|-----|-------|
| `symbol`, `exchange` | `price`, `bid`, `ask`, `volume`, `quote_volume`, `price_change_pct`, `trade_count` |

### 3.3 Kline Stream Processing

#### 3.3.1 Branch 1: Raw 1s Candles

**KeyDB Hash (`candle:1s:{exchange}:{symbol}`)**

| Field | Kiểu | Nguồn |
|-------|------|-------|
| `open` | Double | `open` |
| `high` | Double | `high` |
| `low` | Double | `low` |
| `close` | Double | `close` |
| `volume` | Double | `volume` |
| `quote_volume` | Double | `quote_volume` |
| `trade_count` | Long | `trade_count` |
| `is_closed` | Boolean | `is_closed` |
| `kline_start` | Long | `kline_start` |
| `interval` | String | `interval` |

**KeyDB Sorted Set (`candle:1s:{exchange}:{symbol}`)**

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set |
| TTL | 1 ngày (KEYDB_1S_RETENTION_DAYS) |
| Score | `kline_start` (ms) |
| Member | JSON candle |

**InfluxDB (`candles` measurement)**

| Tag | Field |
|-----|-------|
| `symbol`, `exchange`, `interval` | `open`, `high`, `low`, `close`, `volume`, `quote_volume`, `trade_count`, `is_closed` |

#### 3.3.2 Branch 2: 1s → 1m Aggregation (KlineWindowAggregator)

**Key:** `{exchange}:{symbol}`

**State:** `MapState<kline_start_ms, candle_json>`

**Cơ chế hoạt động:**

```
1. Mỗi candle 1s được lưu vào MapState (dedup theo kline_start)
2. Khi candle từ phút MỚI đến:
   - Aggregate phút cũ và emit
   - Reset window cho phút mới
3. Safety timer fire tại giây thứ 65 để flush window cuối (tránh stuck khi silence)
4. Gap-fill: forward-fill giá từ close trước đó cho các giây thiếu
```

**Công thức Aggregate:**

```
open         = first 1s candle open
close        = last 1s candle close (với real volume)
high         = max(all 1s highs)
low          = min(all 1s lows)
volume       = sum(all 1s volumes)
quote_volume = sum(all 1s quote_volumes)
trade_count  = sum(all 1s trade_counts)
```

**Gap-fill Logic (Forward-fill):**

```python
# Tại giây thiếu, dùng close của giây trước
for sec_offset in range(60):
    ts = window_start + sec_offset * 1000
    if ts in window_candles:
        last_c = window_candles[ts]["c"]
    else:
        window_candles[ts] = {
            "t": ts, "o": last_c, "h": last_c,
            "l": last_c, "c": last_c,
            "v": 0.0, "qv": 0.0, "n": 0,
        }
```

**Output:** `candle:1m:{exchange}:{symbol}` (Hash + Sorted Set)

**InfluxDB:** `candles` measurement (chỉ 1m closed candles)

### 3.4 Indicator Engine (Technical Indicators)

**Input:** Closed 1m candles (từ KlineWindowAggregator)

**Buffer:** `deque(maxlen=60)` — đủ cho SMA50 + buffer

#### 3.4.1 Công thức toán học các chỉ số kỹ thuật

| Chỉ số | Period | Công thức |
|--------|--------|-----------|
| **SMA20** | 20 | `Σ close / 20` |
| **SMA50** | 50 | `Σ close / 50` |
| **EMA12** | 12 | `close × k + prev × (1-k)`, `k = 2/(12+1) = 0.1538` |
| **EMA26** | 26 | `close × k + prev × (1-k)`, `k = 2/(26+1) = 0.0741` |
| **RSI14** | 14 | `100 - (100 / (1 + RS))`, `RS = avg_gain / avg_loss` |
| **BB_MIDDLE** | 20 | `SMA20` |
| **BB_UPPER** | 20 | `SMA20 + 2 × σ` |
| **BB_LOWER** | 20 | `SMA20 - 2 × σ` |
| **BB_WIDTH** | 20 | `BB_UPPER - BB_LOWER` |
| **MACD** | - | `EMA12 - EMA26` |
| **MACD_SIGNAL** | 9 | EMA9 of MACD |
| **MACD_HISTOGRAM** | - | `MACD - MACD_SIGNAL` |
| **ATR14** | 14 | `Σ TR / 14`, `TR = max(high-low, |high-prev_close|, |low-prev_close|)` |
| **VOLUME_SMA20** | 20 | `Σ volume / 20` |

**Chi tiết RSI:**
```python
def _rsi(values, period=14):
    closes = list(values)
    gains = losses = 0.0
    for idx in range(-period, 0):
        diff = closes[idx] - closes[idx - 1]
        if diff > 0: gains += diff
        else: losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0: return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
```

**Chi tiết ATR:**
```python
def _atr(candles, period=14):
    true_ranges = []
    for idx in range(len(rows) - period, len(rows)):
        cur = rows[idx]
        prev = rows[idx - 1]
        tr = max(
            cur["high"] - cur["low"],
            abs(cur["high"] - prev["close"]),
            abs(cur["low"] - prev["close"]),
        )
        true_ranges.append(tr)
    return sum(true_ranges) / len(true_ranges)
```

#### 3.4.2 Output Indicators

**KeyDB Hash (`indicator:latest:{exchange}:{symbol}:{interval}`)**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `timestamp` | Long | kline_start |
| `interval` | String | candle interval |
| `close` | Double | close price |
| `high` | Double | high price |
| `low` | Double | low price |
| `volume` | Double | volume |
| `sma20` | Double | SMA 20 |
| `sma50` | Double | SMA 50 |
| `ema12` | Double | EMA 12 |
| `ema26` | Double | EMA 26 |
| `rsi14` | Double | RSI 14 |
| `bb_middle` | Double | Bollinger Middle |
| `bb_upper` | Double | Bollinger Upper |
| `bb_lower` | Double | Bollinger Lower |
| `bb_width` | Double | Bollinger Width |
| `macd` | Double | MACD line |
| `macd_signal` | Double | MACD signal |
| `macd_histogram` | Double | MACD histogram |
| `atr14` | Double | ATR 14 |
| `volume_sma20` | Double | Volume SMA 20 |

**KeyDB Sorted Set (`indicator:history:{exchange}:{symbol}:{interval}`)**

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set |
| TTL | 604800 giây (7 ngày) |
| Score | `kline_start` (ms) |
| Member | JSON snapshot indicators |

**InfluxDB (`indicators` measurement)**

| Tag | Field |
|-----|-------|
| `symbol`, `exchange` | `sma20`, `sma50`, `ema12`, `ema26`, `rsi14`, `bb_middle`, `bb_upper`, `bb_lower`, `macd`, `macd_signal`, `atr14`, `volume_sma20`, `close` |

### 3.5 Depth Stream Processing

**Input:** Kafka topic `crypto_depth`

**KeyDB Hash (`orderbook:{exchange}:{symbol}`)**

| Field | Kiểu | Mô tả |
|-------|------|-------|
| `bids` | String (JSON) | Array of [price, qty] |
| `asks` | String (JSON) | Array of [price, qty] |
| `last_update_id` | Long | lastUpdateId |
| `event_time` | Long | event_time |
| `exchange` | String | exchange |
| `bid_depth` | Integer | Số lượng bid levels |
| `ask_depth` | Integer | Số lượng ask levels |
| `best_bid` | Double | Giá bid cao nhất |
| `best_ask` | Double | Giá ask thấp nhất |
| `spread` | Double | best_ask - best_bid |

**TTL:** 300 giây (5 phút)

### 3.6 Trade Stream Processing

**Input:** Kafka topic `crypto_trades`

**KeyDB Sorted Set (`trade:latest:{exchange}:{symbol}`)**

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set (ZSET) |
| TTL | 600 giây (10 phút) |
| Score | `trade_time` (ms) |
| Member | `{"p": price, "q": quantity, "t": trade_time, "m": is_buyer_maker, "T": event_time}` |
| Max Entries | 200 trades/symbol |

---

## 4. Tầng Bronze (Spark Streaming)

### 4.1 Cấu hình Spark

| Tham số | Giá trị |
|---------|---------|
| App Name | BinanceDualStreamToIceberg |
| Master | spark://spark-master:7077 |
| Executor Cores | 2 |
| Extensions | IcebergSparkSessionExtensions |
| Catalog | JDBC (PostgreSQL) |
| Warehouse | s3a://cryptoprice/iceberg |
| Format | Apache Iceberg (Parquet + Avro metadata) |

### 4.2 Luật xử lý Bronze

1. **Deserialize Avro:** Strip 5-byte Confluent header, decode Avro binary
2. **Cast timestamp:** `event_time` (Long ms) → `TIMESTAMP`
3. **Add ingested_at:** `current_timestamp()`
4. **Deduplicate:** `dropDuplicates(["symbol", "event_timestamp"])` với watermark
5. **Trigger:** 1 minute micro-batch
6. **Output Mode:** Append
7. **Filter (Klines):** Chỉ `is_closed = true`

### 4.3 Bảng Bronze: `bronze.coin_ticker`

**Path:** `s3a://cryptoprice/iceberg/bronze/coin_ticker`

**Partitioning:** `days(event_timestamp)`

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `event_time` | BIGINT | Event timestamp (ms) |
| `symbol` | STRING | Trading pair (BTCUSDT) |
| `exchange` | STRING | Exchange source (binance/okx) |
| `close` | DOUBLE | Closing price |
| `bid` | DOUBLE | Best bid |
| `ask` | DOUBLE | Best ask |
| `h24_open` | DOUBLE | 24h open price |
| `h24_high` | DOUBLE | 24h high price |
| `h24_low` | DOUBLE | 24h low price |
| `h24_volume` | DOUBLE | 24h base volume |
| `h24_quote_volume` | DOUBLE | 24h quote volume |
| `h24_price_change` | DOUBLE | 24h absolute change |
| `h24_price_change_pct` | DOUBLE | 24h change % |
| `h24_trade_count` | BIGINT | Trade count |
| `event_timestamp` | TIMESTAMP | Event time (cast from event_time) |
| `ingested_at` | TIMESTAMP | Ingestion time |

### 4.4 Bảng Bronze: `bronze.coin_trades`

**Path:** `s3a://cryptoprice/iceberg/bronze/coin_trades`

**Partitioning:** `days(trade_timestamp)`

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `event_time` | BIGINT | Event timestamp (ms) |
| `symbol` | STRING | Trading pair |
| `exchange` | STRING | Exchange source |
| `agg_trade_id` | BIGINT | Aggregate trade ID |
| `price` | DOUBLE | Trade price |
| `quantity` | DOUBLE | Trade quantity |
| `trade_time` | BIGINT | Trade timestamp (ms) |
| `is_buyer_maker` | BOOLEAN | Buyer is maker |
| `event_timestamp` | TIMESTAMP | Event time |
| `trade_timestamp` | TIMESTAMP | Trade time (cast from trade_time) |
| `ingested_at` | TIMESTAMP | Ingestion time |

### 4.5 Bảng Bronze: `bronze.coin_klines`

**Path:** `s3a://cryptoprice/iceberg/bronze/coin_klines`

**Partitioning:** `days(kline_timestamp)`

**Filter:** Chỉ `is_closed = true`

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `event_time` | BIGINT | Event timestamp (ms) |
| `symbol` | STRING | Trading pair |
| `exchange` | STRING | Exchange source |
| `kline_start` | BIGINT | Candle start (ms) |
| `kline_close` | BIGINT | Candle close (ms) |
| `interval` | STRING | Candle interval |
| `open` | DOUBLE | Open price |
| `high` | DOUBLE | High price |
| `low` | DOUBLE | Low price |
| `close` | DOUBLE | Close price |
| `volume` | DOUBLE | Base volume |
| `quote_volume` | DOUBLE | Quote volume |
| `trade_count` | BIGINT | Trade count |
| `is_closed` | BOOLEAN | Closed flag |
| `kline_timestamp` | TIMESTAMP | Candle time (cast from kline_start) |
| `ingested_at` | TIMESTAMP | Ingestion time |

---

## 5. Tầng Silver (Spark Batch)

### 5.1 SilverTickerTransformation

**Schedule:** Hourly

**Lookback:** 2 ngày (cho late arrivals)

**Transformations:**

1. **Deduplication:** `row_number() OVER (PARTITION BY symbol, event_time, exchange ORDER BY ingested_at DESC)`
2. **Validation:** `price > 0 AND price < 1,000,000 AND volume >= 0`
3. **Pivot by exchange:** Join Binance + OKX on same row
4. **Calculate metrics:**

```
price_mid     = (price_binance + price_okx) / 2
volume_total  = volume_binance + volume_okx
spread_pct    = |price_binance - price_okx| / price_mid × 100
quality_score = 100 (dual source) OR 50 (single source)
```

### 5.2 Bảng Silver: `silver.ticker_unified`

**Path:** `s3a://cryptoprice/iceberg/silver/ticker_unified`

**Partitioning:** `_partition_date`

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `event_time` | BIGINT | Event timestamp (ms) |
| `symbol` | STRING | Trading pair |
| `price_binance` | DOUBLE | Binance price |
| `price_okx` | DOUBLE | OKX price |
| `price_mid` | DOUBLE | Mid price = (binance + okx) / 2 |
| `volume_binance` | DOUBLE | Binance 24h volume |
| `volume_okx` | DOUBLE | OKX 24h volume |
| `volume_total` | DOUBLE | Total volume |
| `spread_pct` | DOUBLE | Price spread % |
| `quality_score` | INT | Data quality (50/100) |
| `last_updated` | TIMESTAMP | Last update time |
| `_partition_date` | DATE | Partition date |

### 5.3 SilverKlineAggregation

**Aggregations:**

| Source Interval | Target Interval | Multiplier |
|-----------------|-----------------|------------|
| 1m | 5m | 5 |
| 1m | 15m | 15 |
| 1m | 1h | 60 |
| 1h | 4h | 4 |
| 1h | 1d | 24 |

**Công thức Aggregate:**

```
open         = first candle open
high         = max(all highs)
low          = min(all lows)
close        = last candle close
volume       = sum(all volumes)
trade_count = sum(all trade_counts)
```

### 5.4 Bảng Silver: `silver.kline_multi_timeframe`

**Path:** `s3a://cryptoprice/iceberg/silver/kline_multi_timeframe`

**Partitioning:** `_partition_date`, `interval`

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `event_time` | BIGINT | Event timestamp (ms) |
| `symbol` | STRING | Trading pair |
| `interval` | STRING | Candle interval (5m/15m/1h/4h/1d) |
| `open_price` | DOUBLE | Open price |
| `high_price` | DOUBLE | High price |
| `low_price` | DOUBLE | Low price |
| `close_price` | DOUBLE | Close price |
| `volume` | DOUBLE | Total volume |
| `trade_count` | BIGINT | Trade count |
| `is_closed` | BOOLEAN | Closed flag |
| `quality_score` | INT | Data quality |
| `last_updated` | TIMESTAMP | Last update time |
| `_partition_date` | DATE | Partition date |

---

## 6. Tầng Gold (Spark Batch)

### 6.1 GoldMarketOverview

**Schedule:** Mỗi 5 phút

**Transformations:**

1. **Latest price:** `row_number() OVER (PARTITION BY symbol ORDER BY event_time DESC)`
2. **24h price change:** Compare with price 24h ago
3. **24h volume:** Sum of volumes in last 24h
4. **Market cap:** `h24_quote_volume × 10` (rough estimate)
5. **Ranking:** `row_number() OVER (ORDER BY h24_quote_volume DESC)`

### 6.2 Bảng Gold: `gold.market_overview`

**Path:** `s3a://cryptoprice/iceberg/gold/market_overview`

**Partitioning:** None (flat table cho fast full scan)

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `symbol` | STRING | Trading pair (logical primary key) |
| `close` | DOUBLE | Latest close price |
| `h24_price_change_pct` | DOUBLE | 24h change % |
| `h24_volume` | DOUBLE | 24h base volume |
| `h24_quote_volume` | DOUBLE | 24h quote volume |
| `market_cap` | DOUBLE | Market cap estimate |
| `rank` | INT | Rank by quote volume |
| `last_updated` | TIMESTAMP | Last update time |

### 6.3 Bảng Gold: `gold.coin_ticker`

**Path:** `s3a://cryptoprice/iceberg/gold/coin_ticker`

**Purpose:** Fast API queries cho market overview

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `symbol` | STRING | Trading pair |
| `close` | DOUBLE | Current price |
| `h24_price_change_pct` | DOUBLE | 24h change % |
| `h24_volume` | DOUBLE | 24h volume |
| `h24_quote_volume` | DOUBLE | 24h quote volume |
| `market_cap` | DOUBLE | Market cap estimate |
| `rank` | INT | Rank by volume |
| `last_updated` | TIMESTAMP | Last update |

---

## 7. Tổng kết độ trễ (End-to-End Latency)

### 7.1 Nhánh Real-time

```
Exchange → WebSocket → Producer → Kafka → Flink → Redis/InfluxDB
    │          │          │          │        │         │
   ~0ms    ~100ms      ~10ms     ~50ms   ~100ms    ~0ms
    └─────────────────────────────────────────────────────────┘
                        Total: ~260ms
```

**Data Freshness:** < 1 giây

### 7.2 Nhánh Batch/Lakehouse

```
Kafka → Spark Streaming → Bronze → Silver ETL → Gold ETL
   │          │              │         │          │
  ~0ms      ~1min          ~0      ~1hour      ~5min
  └─────────────────────────────────────────────────┘
              Total: 1-2 hours
```

**Data Freshness:**

| Layer | Freshness |
|-------|-----------|
| Bronze | ~1 phút |
| Silver | ~1 giờ |
| Gold | ~5 phút |

### 7.3 Tổng hợp Data Freshness

| Storage | Data Type | Freshness |
|---------|-----------|-----------|
| Redis Sentinel | Ticker, Trades, Klines, Indicators, Depth | Real-time (< 1s) |
| InfluxDB | Ticker, Klines, Indicators | Real-time (< 1s) |
| Bronze (Iceberg) | Raw data | ~1 phút |
| Silver (Iceberg) | Cleaned, unified | ~1 giờ |
| Gold (Iceberg) | Aggregated, business metrics | ~5 phút |

---

## 8. Phụ lục

### 8.1 Biến môi trường

| Variable | Default | Description |
|----------|---------|-------------|
| `KAFKA_BOOTSTRAP` | kafka-1:9092,kafka-2:9092,kafka-3:9092 | Kafka brokers |
| `SCHEMA_REGISTRY_URL` | http://schema-registry:8080/apis/ccompat/v7 | Schema Registry |
| `KLINE_INTERVAL` | 1m | Kline interval |
| `DEPTH_LEVEL` | 20 | Order book depth level |
| `DEPTH_UPDATE_MS` | 100 | Depth update frequency |
| `SYMBOLS_PER_CONNECTION` | 25 | Symbols per WS connection |
| `SYMBOLS_PER_DEPTH_CONN` | 15 | Symbols per depth connection |
| `MAX_SYMBOLS` | 200 | Max symbols to fetch |
| `ENABLE_OKX` | false | Enable OKX exchange |
| `MINIO_ENDPOINT` | http://minio:9000 | MinIO endpoint |
| `INFLUX_URL` | http://influxdb:8086 | InfluxDB URL |
| `FLINK_PARALLELISM` | 12 | Flink parallelism |
| `KEYDB_1S_RETENTION_DAYS` | 1 | 1s candle retention |
| `KEYDB_1M_RETENTION_DAYS` | 7 | 1m candle retention |
| `INDICATOR_HISTORY_TTL_SEC` | 604800 | Indicator history TTL (7 days) |

### 8.2 Redis Key Patterns

| Key Pattern | Type | TTL | Content |
|-------------|------|-----|---------|
| `ticker:latest:{ex}:{sym}` | Hash | - | Latest ticker |
| `ticker:history:{ex}:{sym}` | Sorted Set | 600s | Price history |
| `candle:1s:{ex}:{sym}` | Sorted Set | 1 ngày | 1s candle history |
| `candle:1m:{ex}:{sym}` | Sorted Set | 7 ngày | 1m candle history |
| `candle:latest:{ex}:{sym}` | Hash | - | Latest candle info |
| `indicator:latest:{ex}:{sym}:{int}` | Hash | 7 ngày | Indicators |
| `indicator:history:{ex}:{sym}:{int}` | Sorted Set | 7 ngày | Indicator history |
| `orderbook:{ex}:{sym}` | Hash | 300s | Order book |
| `trade:latest:{ex}:{sym}` | Sorted Set | 600s | Trade history |

### 8.3 InfluxDB Measurements

| Measurement | Tags | Fields |
|-------------|------|--------|
| `market_ticks` | symbol, exchange | price, bid, ask, volume, quote_volume, price_change_pct, trade_count |
| `candles` | symbol, exchange, interval | open, high, low, close, volume, quote_volume, trade_count, is_closed |
| `indicators` | symbol, exchange | sma20, sma50, ema12, ema26, rsi14, bb_middle, bb_upper, bb_lower, macd, macd_signal, atr14, volume_sma20, close |

### 8.4 Lakehouse Path Structure

```
s3a://cryptoprice/iceberg/
├── bronze/
│   ├── coin_ticker/
│   ├── coin_trades/
│   └── coin_klines/
├── silver/
│   ├── ticker_unified/
│   └── kline_multi_timeframe/
└── gold/
    ├── market_overview/
    └── coin_ticker/
```

**Catalog:** PostgreSQL (`iceberg_catalog`)

**Format:** Apache Iceberg (Parquet + Avro metadata)

### 8.5 Checkpoint Locations

| Topic | Checkpoint Path |
|-------|-----------------|
| `crypto_ticker` | `s3://cryptoprice/checkpoints/crypto_ticker_v1` |
| `crypto_trades` | `s3://cryptoprice/checkpoints/crypto_trades_v1` |
| `crypto_klines` | `s3://cryptoprice/checkpoints/crypto_klines_v1` |

### 8.6 Data Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         INGESTION LAYER                                    │
│  ┌──────────────┐     ┌──────────────┐                                   │
│  │   Binance    │     │     OKX      │                                   │
│  │  WebSocket   │     │  WebSocket   │                                   │
│  │  (Combined)  │     │ (Subscribe)  │                                   │
│  └──────┬───────┘     └──────┬───────┘                                   │
│         │                    │                                            │
│         ▼                    ▼                                            │
│  ┌──────────────────────────────────┐                                    │
│  │         Mapper Layer             │                                    │
│  │  binance/mappers.py, okx/mappers │                                    │
│  └──────────────┬───────────────────┘                                    │
└─────────────────┼─────────────────────────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                       KAFKA BROKER LAYER                                     │
│  ┌─────────────────────────────────────────────────────────────┐           │
│  │  4 Topics: crypto_ticker, crypto_trades, crypto_klines,     │           │
│  │            crypto_depth (12 partitions each)               │           │
│  │  Format: Avro + Confluent Schema Registry                   │           │
│  └─────────────────────────────────────────────────────────────┘           │
└─────────────────┬───────────────────────────────────────────────────────────┘
                  │
        ┌────────┴────────┐
        ▼                 ▼
┌───────────────────┐   ┌───────────────────────────────────────────────────┐
│  FLINK (Speed)    │   │           SPARK (Batch/Lakehouse)                   │
│  Real-time        │   │           Append Mode, Trigger 1 min                │
│  processing       │   │                                                     │
│                   │   │  ┌─────────────────────────────────────────────┐   │
│  ┌─────────────┐  │   │  │           BRONZE LAYER                       │   │
│  │ KeyDB       │  │   │  │  coin_ticker, coin_trades, coin_klines        │   │
│  │ Redis       │  │   │  │  Partitioned by day                         │   │
│  │ Sentinel    │  │   │  └─────────────────────────────────────────────┘   │
│  └─────────────┘  │   │                      │                              │
│                   │   │                      ▼                              │
│  ┌─────────────┐  │   │  ┌─────────────────────────────────────────────┐   │
│  │ InfluxDB    │  │   │  │           SILVER LAYER                       │   │
│  │ Time-series │  │   │  │  ticker_unified, kline_multi_timeframe       │   │
│  │ analytics  │  │   │  │  Hourly batch, 2-day lookback                 │   │
│  └─────────────┘  │   │  └─────────────────────────────────────────────┘   │
│                   │   │                      │                              │
│  ┌─────────────┐  │   │                      ▼                              │
│  │ Indicators │  │   │  ┌─────────────────────────────────────────────┐   │
│  │ SMA/EMA/   │  │   │  │           GOLD LAYER                         │   │
│  │ RSI/BB/ATR │  │   │  │  market_overview, coin_ticker                 │   │
│  │ MACD       │  │   │  │  5-min batch, business metrics                │   │
│  └─────────────┘  │   │  └─────────────────────────────────────────────┘   │
└───────────────────┘   └───────────────────────────────────────────────────┘
```

---

**Tài liệu được biên soạn bởi:** Data Architect Agent  
**Nguồn tham khảo:** `src/exchanges/`, `src/producer/`, `src/processing/`, `src/lakehouse/`, `schemas/`
