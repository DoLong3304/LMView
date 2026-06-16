# DATA FLOW — LMView Cryptocurrency Platform
## Tài liệu đầy đủ hợp nhất (7 phần)

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# MỤC LỤC TOÀN BỘ

```
PHẦN 1: TỔNG QUAN KIẾN TRÚC & THU THẬP DỮ LIỆU TỪ SÀN
  1.1  Lambda Architecture (3 tầng)
  1.2  Cấu hình nguồn (Binance + OKX)
  1.3  Threading model cho WebSocket
  1.4  JSON thô Binance (4 streams)
  1.5  JSON thô OKX (4 streams)
  1.6  Tầng Mapping (Canonical Format)
  1.7  Producer + Kafka integration

PHẦN 2: KAFKA BROKER
  2.1   Tổng quan Kafka
  2.2   4 Topics (12 partitions × RF=3)
  2.3   Partitioning strategy
  2.4   Avro schemas (4)
  2.5   Confluent wire format
  2.6   Schema Registry
  2.7   Schema evolution
  2.8   Performance tuning
  2.9   Failure handling
  2.10  Checkpoint locations

PHẦN 3: FLINK SPEED LAYER
  3.1   Tổng quan Flink
  3.2   Cấu hình Flink job
  3.3   Ticker stream (3 writers)
  3.4   Klines stream (KlineWindowAggregator gap-fill)
  3.5   Indicator Engine (true EMA/RSI/BB/MACD/ATR)
  3.6   Depth stream
  3.7   Trade stream
  3.8   Tổng hợp 8 writers
  3.9   Pipeline orchestration
  3.10  Performance & throughput
  3.11  Failure handling
  3.12  Flink KeyDB connection
  3.13  Redis key patterns + InfluxDB measurements

PHẦN 4: SPARK LAKEHOUSE
  4.1   Tổng quan Spark Lakehouse
  4.2   Bronze layer (3 tables)
  4.3   Silver layer (2 tables + quality scoring)
  4.4   Gold layer (9 tables)
  4.5   Pipeline orchestration

PHẦN 5: SERVING LAYER (FASTAPI + WEBSOCKET)
  5.1   Tổng quan Serving
  5.2   Configuration & constants
  5.3   WebSocket streaming (3 routes + Redis pipeline)
  5.4   REST API endpoints (20+)
  5.5   Service layer
  5.6   Pydantic models
  5.7   Database clients
  5.8   Auth & JWT
  5.9   Performance optimizations
  5.10  Error handling
  5.11  Health checks
  5.12  CORS, rate limiting
  5.13  Logging & observability

PHẦN 6: TECHNICAL INDICATORS (FLINK vs SPARK)
  6.1   Tổng quan hệ thống indicators
  6.2   Flink real-time indicators (true EMA)
  6.3   Spark batch indicators (SMA approx)
  6.4   So sánh side-by-side
  6.5   Pipeline sequence diagram
  6.6   Query patterns
  6.7   Warmup & bootstrap
  6.8   Monitoring & alerting
  6.9   Indicator coverage matrix

PHẦN 7: DATA FLOW DIAGRAMS & LATENCY
  7.1   System overview (Lambda)
  7.2   Sequence diagrams
  7.3   Cold path (Bronze→Silver→Gold)
  7.4   Latency budget
  7.5   Throughput analysis
  7.6   Failure modes & RPO/RTO
  7.7   Scaling patterns
  7.8   Cost optimization
  7.9   Monitoring stack
  7.10  Capacity planning
  7.11  Production topology
  7.12  Glossary
  7.13  Kết luận toàn bộ series
```

---

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Kiến trúc:** Lambda Architecture (Speed Layer + Batch/Lakehouse Layer + Serving Layer)  
**Trạng thái:** Production

---

## MỤC LỤC TOÀN BỘ TÀI LIỆU

```
Part 1: Architecture Overview & Exchange Ingestion
Part 2: Kafka Broker Layer
Part 3: Flink Speed Layer (KeyDB + InfluxDB Writers)
Part 4: Spark Lakehouse (Bronze / Silver / Gold Tables)
Part 5: Serving Layer (FastAPI + WebSocket)
Part 6: Technical Indicators (Flink Real-time vs Spark Batch)
Part 7: Data Flow Diagrams & End-to-End Latency
```

---

# PHẦN 1: TỔNG QUAN KIẾN TRÚC & THU THẬP DỮ LIỆU TỪ SÀN

---

## 1.1 Tổng quan Lambda Architecture

LMView là nền tảng phân tích kỹ thuật cryptocurrency real-time, xây trên **Lambda Architecture** với 3 tầng xử lý chính:

### 1.1.1 Ba tầng của Lambda Architecture

| Tầng | Công nghệ | Độ trễ | Mục đích |
|------|-----------|--------|----------|
| **Speed Layer** | Flink + Redis Sentinel + InfluxDB | < 1 giây | Xử lý real-time, ghi vào hot cache |
| **Batch/Lakehouse Layer** | Spark + Iceberg + MinIO | 1-2 giờ | Xử lý batch, clean data, compute business metrics |
| **Serving Layer** | FastAPI + WebSocket + Trino | < 50ms | Phục vụ API + streaming cho frontend |

### 1.1.2 Luồng dữ liệu tổng quan

```
Exchange WebSocket
       │
       ▼
┌──────────────────┐
│  Kafka Broker    │  (4 topics: ticker, trades, klines, depth)
│  Avro + Schema   │
│  Registry        │
└────────┬─────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌────────┐ ┌────────┐
│ Flink  │ │ Spark  │
│(Speed) │ │(Batch) │
└───┬────┘ └───┬────┘
    │         │
    ▼         ▼
┌────────┐ ┌────────┐
│ Redis  │ │Iceberg │
│InfluxDB│ │(MinIO) │
└───┬────┘ └───┬────┘
    │         │
    ▼         ▼
┌──────────────────┐
│  FastAPI + WS    │
│  (Serving Layer) │
└──────────────────┘
```

### 1.1.3 So sánh Speed Layer vs Batch Layer

| Aspect | Speed Layer (Flink) | Batch Layer (Spark) |
|--------|---------------------|---------------------|
| **Trigger** | Event-driven (mỗi message đến) | Time-driven (1 phút micro-batch) |
| **Độ trễ** | < 1 giây | 1-2 giờ |
| **State** | In-memory với checkpoint | Stateless batch jobs |
| **Output** | Redis Sentinel + InfluxDB | Iceberg (Bronze/Silver/Gold) |
| **Use case** | Real-time chart, trading | Historical analysis, AI training |
| **Indicators** | SMA/EMA/RSI/BB/MACD/ATR (1m) | RSI/MACD/BB (1h) |
| **History** | 7 ngày (Redis) | Full history (Iceberg) |

---

## 1.2 Cấu hình nguồn dữ liệu (Exchange Ingestion)

### 1.2.1 Hai sàn giao dịch được hỗ trợ

| Tham số | Binance | OKX |
|---------|---------|-----|
| **Số lượng mã** | Tối đa 200 mã (USDT spot) | 20 mã phổ biến (opt-in) |
| **Quy tắc lọc** | Đuôi USDT, trạng thái `TRADING` | Danh sách whitelist cố định |
| **WebSocket Endpoint** | `wss://stream.binance.com:9443/ws/` | `wss://ws.okx.com:8443/ws/v5/public` |
| **Protocol** | Combined Stream (symbol@stream) | Subscription Frame |
| **Default** | Enabled (`ENABLE_BINANCE=true`) | Disabled (`ENABLE_OKX=false`) |

### 1.2.2 Danh sách 20 mã OKX (whitelist cố định)

```
BTCUSDT, ETHUSDT, BNBUSDT, SOLUSDT, XRPUSDT,
ADAUSDT, DOGEUSDT, AVAXUSDT, DOTUSDT, MATICUSDT,
LINKUSDT, SHIBUSDT, LTCUSDT, ATOMUSDT, UNICUSDT,
XLMUSDT, VETUSDT, ICPUSDT, FILUSDT, AAVEUSDT
```

### 1.2.3 Bốn luồng dữ liệu thu thập đồng thời

| Stream | Binance Channel | OKX Channel | Tần suất | Mục đích |
|--------|-----------------|-------------|----------|----------|
| **Ticker** | `!miniTicker@arr` | `tickers` | Real-time (change/heartbeat 0.3s) | Giá + khối lượng 24h |
| **Trades** | `{symbol}@aggTrade` | `trades` | Mỗi transaction | Trade thực tế |
| **Klines** | `{symbol}@kline_1s` | `candle1m` | 1 giây (Binance) / 1 phút (OKX) | Candle OHLCV |
| **Depth** | `{symbol}@depth20@100ms` | `books5` | 100ms (Binance) / Real-time (OKX) | Order book |

---

## 1.3 Cơ chế Threading và phân luồng WebSocket

### 1.3.1 Tổng số Thread WebSocket tối đa

**Tổng số Thread WebSocket tối đa:** ~36 threads

| Stream | Binance Threads | OKX Threads | Symbols/Connection | Mục đích |
|--------|----------------|-------------|-------------------|----------|
| **Ticker** (`!ticker@arr`) | 1 | 1 | Tất cả (200/20) | Gom toàn bộ mã |
| **Trades** (`@aggTrade`) | `ceil(200/25) = 8` | `ceil(20/25) = 1` | 25 | Chia nhóm |
| **Klines** (`@kline_1s`) | `ceil(200/25) = 8` | `ceil(20/25) = 1` | 25 | Chia nhóm |
| **Depth** (`@depth20@100ms`) | `ceil(200/15) = 14` | `ceil(20/15) = 2` | 15 | Tải nặng hơn |

### 1.3.2 Thứ tự kích hoạt thread (staggered để tránh handshake burst)

```
1. Prometheus Metrics Server (port 9090)
2. Kafka Producer initialization
3. Avro Schema registration → Schema Registry
4. Block chính: Ticker Stream (chờ 0s)
5. Trades threads: bắt đầu cách nhau 1 giây (staggered)
6. Klines threads: bắt đầu cách nhau 1 giây (staggered)
7. Depth threads: bắt đầu cách nhau 1 giây (staggered)
```

### 1.3.3 Cơ chế throttle cho Ticker

- Chỉ gửi khi `price thay đổi` HOẶC `heartbeat >= 0.3 giây`
- Tránh spam khi giá đứng yên

---

## 1.4 Định dạng JSON thô từ Binance

### 1.4.1 Ticker Stream (`!miniTicker@arr`)

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

### 1.4.2 Aggregate Trades Stream (`{symbol}@aggTrade`)

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

### 1.4.3 Kline Stream (`{symbol}@kline_1s`)

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

### 1.4.4 Depth Stream (`{symbol}@depth20@100ms`)

```json
{
  "lastUpdateId": 160,
  "bids": [["16499.00", "10.50"], ["16498.00", "5.25"]],
  "asks": [["16501.00", "8.00"], ["16502.00", "3.50"]]
}
```

---

## 1.5 Định dạng JSON thô từ OKX

### 1.5.1 Ticker Channel (`tickers`)

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

### 1.5.2 Trades Channel (`trades`)

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

### 1.5.3 Kline Channel (`candle{interval}`)

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

### 1.5.4 Depth Channel (`books{level}`)

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

---

## 1.6 Tầng Mapping (Canonical Format)

### 1.6.1 Tại sao cần Canonical Format

```
Exchange JSON → Canonical Format → Kafka → Flink/Spark
                      │
                      ▼
           Unified schema cho tất cả exchanges
           (Binance + OKX cùng format)
```

**Lợi ích:**
- Flink/Spark không cần biết exchange nào gửi data
- Schema consistency giữa Binance và OKX
- Dễ dàng thêm exchange mới

### 1.6.2 Binance Mappers

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

### 1.6.3 OKX Mappers

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

### 1.6.4 Lưu ý quan trọng về OKX

**OKX dùng `side=buy` khi buyer là taker (maker = seller), nên logic `is_buyer_maker` ngược với Binance.**

```
Binance:  m = true  → Buyer là Maker (buyer đặt giá thấp hơn, seller fill)
OKX:      side = "buy" → Buyer là Taker (buyer fill maker)

Do đó:
  Binance: is_buyer_maker = raw["m"]
  OKX:     is_buyer_maker = (raw["side"] == "sell")
```

---

## 1.7 Producer và Kafka Integration

### 1.7.1 Producer Flow

```
WebSocket JSON → Mapper (canonical) → Avro serialize → Kafka Broker
                                            │
                                            ▼
                              Confluent Wire Format:
                              [magic:1][schema_id:4][avro_binary:N]
```

### 1.7.2 Key Producer Settings

| Setting | Value | Description |
|---------|-------|-------------|
| `bootstrap.servers` | `kafka-1:9092,kafka-2:9092,kafka-3:9092` | Kafka cluster |
| `compression.type` | `lz4` | LZ4 compression |
| `batch.size` | 16384 | Batch size 16KB |
| `linger.ms` | 5 | Linger 5ms for batching |
| `acks` | `all` | Wait for all replicas |
| `retries` | 3 | Retry 3 times |

---

**Tiếp theo: Part 2 — Kafka Broker Layer**

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# PHẦN 2: TẦNG KAFKA BROKER

---

## 2.1 Tổng quan Kafka trong hệ thống

**Mô tả:** Kafka đóng vai trò **message broker** trung gian, nhận dữ liệu thô từ producer và phân phối cho các consumer (Flink, Spark) theo mô hình pub/sub. Đây là điểm giao giữa Exchange Ingestion (phần 1) và hai tầng xử lý Speed (Flink) + Batch (Spark).

### 2.1.1 Tại sao dùng Kafka

| Lý do | Giải thích |
|-------|-----------|
| **Decoupling** | Producer không cần biết ai consume data |
| **Durability** | Message lưu 48 giờ, cho phép replay nếu consumer fail |
| **Scalability** | 12 partitions cho phép parallel processing |
| **Schema enforcement** | Confluent Avro Schema Registry đảm bảo tất cả consumer dùng cùng schema |
| **Fault tolerance** | Replication factor 3, tự động failover |
| **Ordered delivery** | Mỗi partition đảm bảo thứ tự message |

### 2.1.2 Vị trí trong data flow

```
Producer (Binance/OKX)
       │
       │ 1. Serialize dict → Avro
       │ 2. Prepend 5-byte Confluent header
       │ 3. Send to Kafka
       ▼
┌─────────────────────────────────────┐
│           KAFKA BROKER              │
│  4 topics × 12 partitions × RF=3    │
│  Retention: 48h, Compression: LZ4   │
└──────┬──────────────────────┬───────┘
       │                      │
       │ 2. Subscribe         │ 2. Subscribe
       ▼                      ▼
┌──────────────┐      ┌──────────────┐
│   FLINK      │      │   SPARK      │
│  (Speed)     │      │ (Streaming)  │
└──────────────┘      └──────────────┘
```

### 2.1.3 Kafka Cluster Topology

| Component | Configuration | Purpose |
|-----------|---------------|---------|
| **Brokers** | 3 brokers (kafka-1, kafka-2, kafka-3) | Cluster cho HA |
| **ZooKeeper** | KRaft mode (no ZK) | Cluster coordination |
| **Schema Registry** | http://schema-registry:8080 | Avro schema storage |
| **Replication Factor** | 3 | Mỗi message replicate 3 lần |
| **Min In-Sync Replicas** | 2 | Tối thiểu 2 replicas đồng bộ |
| **Compression** | LZ4 | Giảm ~70% storage |

---

## 2.2 Cấu hình 4 Topics

### 2.2.1 Topic Configuration

| Topic | Partitions | Replication Factor | Retention | Compression |
|-------|-----------|-------------------|-----------|-------------|
| `crypto_ticker` | 12 | 3 | 48 giờ | LZ4 |
| `crypto_trades` | 12 | 3 | 48 giờ | LZ4 |
| `crypto_klines` | 12 | 3 | 48 giờ | LZ4 |
| `crypto_depth` | 12 | 3 | 48 giờ | LZ4 |

### 2.2.2 Lý do chọn 12 partitions

12 partitions được chọn dựa trên:

| Tiêu chí | Giải thích |
|----------|-----------|
| **Flink parallelism** | `FLINK_PARALLELISM=12` — tương thích 1-1 với slots |
| **Spark executors** | Mỗi executor 2 cores, cần 6 executors × 2 cores = 12 parallelism |
| **CPU cores** | Tối ưu cho 12 vCPU trên production cluster |
| **Throughput** | Đủ xử lý ~1M messages/giây (mỗi partition ~85K msg/s) |

### 2.2.3 Lý do chọn Retention 48h

- **Đủ replay window**: Consumer có thể replay nếu restart
- **Storage optimization**: Không giữ quá nhiều data
- **Spark batch start**: Mỗi batch job có thể đọc lại 48h data

### 2.2.4 Lý do chọn LZ4 Compression

- **Tốc độ**: LZ4 nén/giải nén nhanh hơn GZIP ~5 lần
- **Ratio**: Vẫn đạt ~70% compression
- **CPU efficient**: Phù hợp với real-time pipeline

---

## 2.3 Quy tắc phân chia Partition

### 2.3.1 Partitioning Strategy

```python
partition_id = hash(symbol) % 12
```

### 2.3.2 Mục tiêu của partitioning strategy

| Mục tiêu | Giải thích |
|----------|-----------|
| **Symbol locality** | Tất cả message cùng symbol vào cùng partition |
| **Multi-exchange** | Binance + OKX cùng symbol → cùng partition |
| **Order preservation** | Mỗi symbol có thứ tự message nhất quán |
| **Hot partition mitigation** | Hash distribution cân bằng load |

### 2.3.3 Ví dụ phân chia

| Symbol | hash(symbol) | Partition ID |
|--------|--------------|--------------|
| BTCUSDT | 1284912345 | 5 |
| ETHUSDT | 9876543210 | 6 |
| SOLUSDT | 5432167890 | 2 |
| ADAUSDT | 123456789 | 9 |

**Lưu ý:** Tất cả message của BTCUSDT (cả Binance lẫn OKX) đều vào partition 5 → giữ thứ tự cross-exchange.

### 2.3.4 Tương thích với Flink + Spark

```
12 partitions Kafka
        │
        ├── Flink 12 slots ──→ Mỗi slot đọc 1 partition
        │   (FLINK_PARALLELISM=12)
        │
        └── Spark 12 cores ──→ Mỗi core đọc 1 partition
            (spark.cores.max=2, executors=6)
```

---

## 2.4 Avro Schema Definitions

### 2.4.1 Tại sao dùng Avro + Schema Registry

| Lợi ích | Giải thích |
|---------|-----------|
| **Compact binary** | Nhỏ hơn JSON ~40% |
| **Schema evolution** | Thêm field không break consumers |
| **Type safety** | Type checking tại deserialize time |
| **Code generation** | Có thể generate code từ schema |
| **Language-agnostic** | Python, Java, Scala, Go đều support |

### 2.4.2 Ticker Avro Schema (`schemas/ticker.avsc`)

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

### 2.4.3 Trade Avro Schema (`schemas/trade.avsc`)

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

### 2.4.4 Kline Avro Schema (`schemas/kline.avsc`)

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

### 2.4.5 Depth Avro Schema (`schemas/depth.avsc`)

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

---

## 2.5 Confluent Avro Wire Format

### 2.5.1 Wire Format Structure

```
┌─────────────────────────────────────────────────────────────┐
│  Wire Format: [magic_byte:1][schema_id:4][avro_binary:N]   │
├─────────────────────────────────────────────────────────────┤
│  Byte 0:       Magic byte (0x00)                            │
│  Bytes 1-4:     Schema ID (big-endian int32)                 │
│  Bytes 5-N:     Avro-encoded binary payload                 │
└─────────────────────────────────────────────────────────────┘
```

### 2.5.2 Quy trình Serialization (Producer)

```python
# 1. Canonical dict
data = {
    "event_time": 1672531199000,
    "symbol": "BTCUSDT",
    "exchange": "binance",
    "close": 16500.00,
    # ... more fields
}

# 2. Serialize dict → Avro binary
avro_binary = avro.serializer.serialize(data)

# 3. Prepend 5-byte Confluent header
schema_id = 42  # from Schema Registry
wire_format = b'\x00' + schema_id.to_bytes(4, 'big') + avro_binary

# 4. Send to Kafka
producer.send(topic='crypto_ticker', value=wire_format)
```

### 2.5.3 Quy trình Deserialization (Spark)

```python
# 1. Read raw bytes from Kafka
raw_value = spark.read.format("kafka")...

# 2. Strip 5-byte Confluent header
avro_binary = raw_value[5:]  # skip magic(1) + schema_id(4)

# 3. Decode Avro
.selectExpr("substring(value, 6, length(value)-5) as avro_value")
.select(from_avro(col("avro_value"), avro_schema).alias("data"))
.select("data.*")
```

### 2.5.4 Tại sao cần Magic Byte

- **Identification**: Consumer biết đây là Confluent format
- **Future-proof**: Có thể thêm version mới (0x00 → 0x01)

### 2.5.5 Tại sao cần Schema ID

- **Schema versioning**: Mỗi schema version có ID riêng
- **No embedded schema**: Không cần embed schema trong mỗi message
- **Cache efficiency**: Consumer cache schema 1 lần, dùng cho nhiều messages

---

## 2.6 Schema Registry

### 2.6.1 Schema Registry Architecture

```
┌────────────────────────────────────┐
│       Schema Registry              │
│  (http://schema-registry:8080)     │
│                                    │
│  Subject: crypto_ticker-value      │
│    Version 1: {14 fields}          │
│    Version 2: {15 fields}          │  ← Schema evolution
│                                    │
│  Subject: crypto_trades-value      │
│    Version 1: {8 fields}           │
│                                    │
│  Subject: crypto_klines-value      │
│    Version 1: {14 fields}          │
│                                    │
│  Subject: crypto_depth-value       │
│    Version 1: {6 fields}           │
└────────────────────────────────────┘
```

### 2.6.2 Schema Registration Flow

```
1. Producer startup → POST /subjects/{topic}-value/versions
2. Schema Registry → Store schema → Return schema_id
3. Producer → Cache schema_id
4. Producer → Use schema_id trong wire format
5. Consumer → Strip header → Extract schema_id
6. Consumer → GET /schemas/ids/{schema_id} → Cache schema
7. Consumer → Deserialize using cached schema
```

### 2.6.3 Schema Compatibility

LMView sử dụng **BACKWARD compatibility**:
- Thêm field mới với default value → OK
- Xóa field → KHÔNG OK
- Đổi tên field → KHÔNG OK

**Ví dụ evolution:**
```json
// v1: 14 fields
{"event_time": 123, "symbol": "BTC", ...}

// v2: 15 fields (thêm "exchange")
{"event_time": 123, "symbol": "BTC", "exchange": "binance", ...}
```

Consumer đọc v2 schema, có thể đọc cả v1 messages (dùng default "binance").

---

## 2.7 Schema Evolution Best Practices

### 2.7.1 Cho phép

- ✅ Thêm field mới với default value
- ✅ Xóa field chỉ dùng locally (không commit)
- ✅ Rename field bằng cách thêm field mới + deprecate field cũ

### 2.7.2 Không cho phép

- ❌ Đổi kiểu dữ liệu (Long → String)
- ❌ Xóa field đã commit
- ❌ Rename field đã commit

---

## 2.8 Kafka Performance Tuning

### 2.8.1 Producer Settings (từ code)

| Setting | Value | Reason |
|---------|-------|--------|
| `bootstrap.servers` | `kafka-1:9092,kafka-2:9092,kafka-3:9092` | 3 brokers |
| `compression.type` | `lz4` | 70% size reduction, fast |
| `acks` | `all` | Wait all replicas |
| `retries` | 3 | Transient failures |
| `max.in.flight.requests.per.connection` | 5 | Throughput |
| `linger.ms` | 5 | Small batching |
| `batch.size` | 16384 | 16KB batch |

### 2.8.2 Flink Kafka Consumer Settings

| Setting | Value |
|---------|-------|
| `group.id` | `flink_crypto_ticker_v1` |
| `scan.startup.mode` | `latest-offset` |
| `format` | `avro-confluent` |
| `avro-confluent.url` | `http://schema-registry:8080/apis/ccompat/v7` |

### 2.8.3 Spark Kafka Consumer Settings

| Setting | Value |
|---------|-------|
| `kafka.bootstrap.servers` | (same as producer) |
| `subscribe` | (topic name) |
| `startingOffsets` | `latest` |
| `failOnDataLoss` | `false` |
| `maxOffsetsPerTrigger` | `500_000` |

---

## 2.9 Failure Handling

### 2.9.1 Producer Failures

| Failure | Handling |
|---------|----------|
| Broker unavailable | Retry 3 times, log error |
| Serialization fail | Log + skip message |
| Network timeout | Exponential backoff |
| Schema not found | Re-register schema |

### 2.9.2 Consumer Failures (Flink)

| Failure | Handling |
|---------|----------|
| Kafka offset commit fail | Restart from checkpoint |
| Deserialization fail | Skip message + log |
| Downstream writer fail | Retry in pipeline |
| Checkpoint fail | Restart from previous checkpoint |

### 2.9.3 Consumer Failures (Spark)

| Failure | Handling |
|---------|----------|
| Kafka offset commit fail | Restart from checkpoint |
| Avro parse fail | Skip batch + log |
| Iceberg write fail | Retry with backoff (5 attempts) |

### 2.9.4 Spark Retry Logic (từ code)

```python
def _start_query_with_retry(start_query_fn, query_name, max_retries=5, backoff_sec=15):
    attempt = 0
    while True:
        try:
            query = start_query_fn()
            return query
        except Exception as exc:
            attempt += 1
            if attempt >= max_retries:
                raise
            time.sleep(backoff_sec * attempt)
```

**5 retries × exponential backoff (15s, 30s, 45s, 60s, 75s) = ~225s max wait**

---

## 2.10 Checkpoint Locations

| Topic | Checkpoint Path |
|-------|-----------------|
| `crypto_ticker` | `s3://cryptoprice/checkpoints/crypto_ticker_v1` |
| `crypto_trades` | `s3://cryptoprice/checkpoints/crypto_trades_v1` |
| `crypto_klines` | `s3://cryptoprice/checkpoints/crypto_klines_v1` |

**Lưu trữ:** MinIO (S3-compatible) — đảm bảo durability khi pod restart.

**Checkpoint nội dung:**
- Kafka offsets
- Flink keyed state
- Spark batch watermarks
- Deduplication state

---

**Tiếp theo: Part 3 — Flink Speed Layer (KeyDB + InfluxDB Writers)**

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# PHẦN 3: TẦNG XỬ LÝ REAL-TIME (FLINK SPEED LAYER)

---

## 3.1 Tổng quan Flink trong hệ thống

**Mô tả:** Apache Flink là **stream processing engine** xử lý dữ liệu real-time ngay khi nó đến Kafka. Flink duy trì state trong memory, checkpoint định kỳ xuống S3 (MinIO), và có restart strategy để đảm bảo exactly-once semantics. Đây là core của Speed Layer trong Lambda Architecture.

### 3.1.1 Vai trò của Flink

| Trách nhiệm | Mô tả |
|--------------|-------|
| **Real-time processing** | Xử lý từng message khi đến từ Kafka |
| **Stateful aggregation** | 1s→1m candle aggregation với dedup + gap-fill |
| **Multi-write fanout** | 1 input → 3+ outputs (KeyDB hash, KeyDB sorted set, InfluxDB) |
| **Indicator computation** | Tính SMA/EMA/RSI/BB/MACD ngay khi candle close |
| **Hot cache population** | Liên tục update Redis để API đọc nhanh |

### 3.1.2 Vị trí trong data flow

```
Kafka (Part 2)
       │
       │  Kafka consumer (latest-offset)
       ▼
┌──────────────────────────────────────────┐
│              FLINK JOB                   │
│  ┌────────────────────────────────────┐  │
│  │  Ticker Stream                     │  │
│  │   ├→ KeyDBWriter (Hash + ZSET)    │  │
│  │   └→ InfluxDBWriter (market_ticks)│  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │  Klines Stream                     │  │
│  │   ├→ KeyDBKlineWriter (1s raw)     │  │
│  │   ├→ KlineWindowAggregator (1m)    │  │
│  │   │   ├→ KeyDBKlineWriter (1m)     │  │
│  │   │   ├→ InfluxDBKlineWriter       │  │
│  │   │   └→ IndicatorWriter           │  │
│  │   └→ InfluxDBKlineWriter (1s)      │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │  Depth Stream                      │  │
│  │   └→ DepthWriter (Hash)            │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │  Trades Stream                     │  │
│  │   └→ KeyDBTradeWriter (ZSET)       │  │
│  └────────────────────────────────────┘  │
└────────┬───────────────────┬────────────┘
         │                   │
         ▼                   ▼
    Redis Sentinel      InfluxDB
```

---

## 3.2 Cấu hình Flink

### 3.2.1 Job Configuration

| Tham số | Giá trị | Mô tả |
|---------|---------|-------|
| Parallelism | 12 slots | Tương ứng 12 Kafka partitions |
| Checkpoint Interval | 120 giây | 2 phút checkpoint một lần |
| Checkpoint Mode | EXACTLY_ONCE | Không mất/không trùng message |
| State Backend | HashMapStateBackend | State trong memory + checkpoint xuống S3 |
| Restart Strategy | 5 failures per 10 minutes | Fail 5 lần trong 10 phút mới exit |
| Min Pause Between Checkpoints | 30 giây | Tránh checkpoint quá dồn dập |
| Checkpoint Timeout | 120 giây | Timeout cho 1 checkpoint |
| Unaligned Checkpoints | Enabled | Cho phép xử lý backpressure |

### 3.2.2 Checkpoint Storage

```python
env.get_checkpoint_config().set_checkpoint_storage_dir(
    "s3://flink-checkpoints/flink-checkpoints"
)
```

**Lý do dùng S3 (MinIO):**
- Durability: Không mất state khi pod restart
- Scalability: Không giới hạn storage
- Standard: Tương thích với AWS S3 API

### 3.2.3 S3 Configuration

```python
s3_config = Configuration()
s3_config.set_string("s3.endpoint",          MINIO_ENDPOINT)      # http://minio:9000
s3_config.set_string("s3.access-key",        MINIO_ACCESS_KEY)
s3_config.set_string("s3.secret-key",        MINIO_SECRET_KEY)
s3_config.set_string("s3.path.style.access", "true")
s3_config.set_string("fs.s3a.endpoint",           MINIO_ENDPOINT)
s3_config.set_string("fs.s3a.access.key",         MINIO_ACCESS_KEY)
s3_config.set_string("fs.s3a.secret.key",         MINIO_SECRET_KEY)
s3_config.set_string("fs.s3a.path.style.access",  "true")
s3_config.set_string("fs.s3a.impl",               "org.apache.hadoop.fs.s3a.S3AFileSystem")
env.configure(s3_config)
```

### 3.2.4 Restart Strategy

```python
env.set_restart_strategy(
    RestartStrategies.failure_rate_restart(
        5,        # max failures
        600000,   # 10 minutes interval
        10000,    # 10 seconds delay between restarts
    )
)
```

**Giải thích:**
- Cho phép fail tối đa 5 lần trong 10 phút
- Delay 10 giây giữa các lần restart
- Sau 5 lần fail liên tiếp → job chết

---

## 3.3 Ticker Stream Processing

### 3.3.1 Input

Kafka topic: `crypto_ticker` (12 partitions)

### 3.3.2 Logic tổng quan

```
Ticker message → KeyDBWriter
                  ├─ Hash: ticker:latest:{exchange}:{symbol}
                  └─ Sorted Set: ticker:history:{exchange}:{symbol}
```

### 3.3.3 Writer 1: KeyDBWriter (Hash)

**Mục đích:** Ghi ticker mới nhất vào Redis Hash để API đọc nhanh.

**Output — KeyDB Hash (`ticker:latest:{exchange}:{symbol}`):**

| Field | Kiểu | Nguồn | Mô tả |
|-------|------|-------|-------|
| `price` | Double | `close` | Giá hiện tại |
| `bid` | Double | `bid` | Best bid |
| `ask` | Double | `ask` | Best ask |
| `volume` | Double | `h24_volume` | 24h base volume |
| `change24h` | Double | `h24_price_change_pct` | 24h % change |
| `event_time` | Long | `event_time` | Timestamp |
| `exchange` | String | `exchange` | Exchange name |

**Key format:**
```
ticker:latest:binance:BTCUSDT
ticker:latest:okx:BTCUSDT
```

### 3.3.4 Writer 2: KeyDBWriter (Sorted Set)

**Mục đích:** Lưu history price cho watchlist mini-chart.

**Output — KeyDB Sorted Set (`ticker:history:{exchange}:{symbol}`):**

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set (ZSET) |
| TTL | 600 giây (10 phút) |
| Score | `event_time` (ms) |
| Member | `"{price}:{volume}"` |

**Sử dụng:**
- ZADD `{price}:{volume}` → score = event_time
- ZRANGEBYSCORE → lấy giá trong khoảng thời gian
- ZREMRANGEBYSCORE → cleanup old entries (> 5 phút)

### 3.3.5 Writer 3: InfluxDBWriter

**Mục đích:** Ghi vào InfluxDB cho time-series analytics.

**Output — InfluxDB (`market_ticks` measurement):**

| Tag | Field |
|-----|-------|
| `symbol`, `exchange` | `price`, `bid`, `ask`, `volume`, `quote_volume`, `price_change_pct`, `trade_count` |

### 3.3.6 Batch-buffered Performance

**Key optimization:** Flush nhiều messages cùng lúc qua Redis pipeline.

```python
BATCH_SIZE = 100       # Max records trong buffer
FLUSH_INTERVAL = 0.5   # Flush sau 500ms
CLEANUP_EVERY = 60     # Cleanup mỗi 60 records
```

**Pipeline write:**
```python
pipe = self._r.pipeline()
for value in self._buffer:
    pipe.hset(...)           # HSET latest
    pipe.zadd(...)           # ZADD history
    pipe.expire(...)         # Set TTL
pipe.execute()               # Execute 1 round-trip
```

**Throughput:** ~10,000 messages/giây per writer (batch size 100).

---

## 3.4 Kline Stream Processing

### 3.4.1 Input

Kafka topic: `crypto_klines` (12 partitions)

### 3.4.2 Logic tổng quan (3 branches)

```
Kline message
     │
     ├── Branch 1: Raw 1s candles → KeyDB + InfluxDB
     │
     ├── Branch 2: 1s→1m aggregation (KlineWindowAggregator)
     │              │
     │              ├── KeyDBKlineWriter (1m)
     │              ├── InfluxDBKlineWriter (1m closed)
     │              └── IndicatorWriter (compute indicators)
     │
     └── Branch 3: Same as Branch 1 (same 1s raw)
```

### 3.4.3 Branch 1: Raw 1s Candles

**Mục đích:** Lưu raw 1s candles phục vụ cho chart 1s interval và backfill.

**Output 1 — KeyDB Hash (`candle:1s:{exchange}:{symbol}`):**

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

**Output 2 — KeyDB Sorted Set (`candle:1s:{exchange}:{symbol}`):**

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set |
| TTL | 1 ngày (`KEYDB_1S_RETENTION_DAYS=1`) |
| Score | `kline_start` (ms) |
| Member | JSON candle |

**JSON format:**
```json
{
  "t": 1672531190000,
  "o": 16500.00,
  "h": 16505.00,
  "l": 16498.00,
  "c": 16501.00,
  "v": 120.50,
  "qv": 1980000.00,
  "n": 456,
  "x": false
}
```

**Output 3 — InfluxDB (`candles` measurement, 1s):**

| Tag | Field |
|-----|-------|
| `symbol`, `exchange`, `interval` | `open`, `high`, `low`, `close`, `volume`, `quote_volume`, `trade_count`, `is_closed` |

### 3.4.4 Branch 2: 1s → 1m Aggregation (KlineWindowAggregator)

**Mụ tả:** Aggregate 1s candles thành 1m candles trong Flink keyed state, với deduplication và gap-filling.

**Key:** `{exchange}:{symbol}`

**State:** `MapState<kline_start_ms, candle_json>`

**Cơ chế hoạt động:**

```
1. Mỗi candle 1s được lưu vào MapState (dedup theo kline_start)
   → Nếu trùng kline_start → overwrite (dedup tự động)
2. Khi candle từ phút MỚI đến:
   → Aggregate phút cũ và emit
   → Reset window cho phút mới
3. Safety timer fire tại giây thứ 65 để flush window cuối
   → Tránh stuck khi silence (no trades)
4. Gap-fill: forward-fill giá từ close trước cho các giây thiếu
   → Đảm bảo chart không bị "lỗ hổng"
```

**Công thức Aggregate (1m):**

```
open         = first 1s candle open
close        = last 1s candle close (real volume, không phải forward-filled)
high         = max(all 1s highs)
low          = min(all 1s lows)
volume       = sum(all 1s volumes)
quote_volume = sum(all 1s quote_volumes)
trade_count  = sum(all 1s trade_counts)
is_closed    = true
```

**Code aggregation:**

```python
def _aggregate(self, window_start: int) -> str | None:
    window_candles: dict[int, dict] = {}
    for ts, cjson in self._candles.items():
        minute = (ts // self.WINDOW_MS) * self.WINDOW_MS
        if minute == window_start:
            window_candles[ts] = json.loads(cjson)

    if not window_candles:
        return None

    # Gap-fill missing seconds (forward-fill from previous close)
    last_c = self._last_close.value() or next(iter(window_candles.values()))["c"]
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

    sorted_candles = [window_candles[k] for k in sorted(window_candles)]
    actual_close = sorted_candles[-1]["c"]

    agg = {
        "event_time":   int(time.time() * 1000),
        "symbol":       symbol,
        "exchange":     exchange,
        "kline_start":  window_start,
        "kline_close":  window_start + 59_999,
        "interval":     "1m",
        "open":         sorted_candles[0]["o"],
        "high":         max(c["h"] for c in sorted_candles),
        "low":          min(c["l"] for c in sorted_candles),
        "close":        actual_close,
        "volume":       sum(c["v"] for c in sorted_candles),
        "quote_volume": sum(c["qv"] for c in sorted_candles),
        "trade_count":  sum(c["n"] for c in sorted_candles),
        "is_closed":    True,
    }
    return json.dumps(agg)
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

**Tại sao cần gap-fill:**
- Một số giây có thể không có trade (thị trường quiet)
- Gap-fill đảm bảo chart không bị "lỗ hổng" giữa các candle
- Dùng close price của giây trước để fill (giả định giá không đổi)

**Output — 1m candles:**

| Destination | Key | TTL | Content |
|-------------|-----|-----|---------|
| Redis Hash | `candle:1m:{exchange}:{symbol}` | - | Latest 1m candle (OHLCV fields) |
| Redis Sorted Set | `candle:1m:{exchange}:{symbol}` | 7 ngày | History of 1m candles (score = kline_start) |
| InfluxDB | `candles` measurement (interval=1m, is_closed=true) | 90 ngày | 1m closed candles |

### 3.4.5 Pipeline Flow

```
KeyDBKlineWriter.flat_map(candle)
   │
   ├── interval == "1s"
   │     → key = "candle:1s:{ex}:{sym}", TTL = 1 day
   │
   └── interval == "1m"
         → key = "candle:1m:{ex}:{sym}", TTL = 7 days
         → also write candle:latest:{ex}:{sym} (Hash for quick access)
```

---

## 3.5 Indicator Engine (Technical Indicators)

### 3.5.1 Mục đích

Tính toán **technical indicators** ngay khi có 1m candle closed.

### 3.5.2 Input

Closed 1m candles (từ KlineWindowAggregator).

### 3.5.3 Buffer

| State | Type | Maxlen | Mục đích |
|-------|------|--------|----------|
| `self._closes` | `dict[str, deque]` | 60 | Close prices (đủ cho SMA50 + buffer) |
| `self._volumes` | `dict[str, deque]` | 60 | Volumes |
| `self._candles` | `dict[str, deque]` | 60 | Candles (high/low/close/volume) cho ATR |
| `self._ema_state` | `dict[str, dict[int, float]]` | - | EMA state per symbol × period |
| `self._macd_signal_state` | `dict[str, float]` | - | MACD signal state per symbol |

### 3.5.4 Các Indicators được tính

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

### 3.5.5 Công thức chi tiết

**SMA (Simple Moving Average):**
```python
@staticmethod
def _sma(values, period):
    if len(values) < period:
        return None
    window = list(values)[-period:]
    return sum(window) / period
```

**EMA (Exponential Moving Average) - true exponential smoothing:**
```python
def _ema(self, symbol, close_price, period):
    sym_state = self._ema_state.setdefault(symbol, {})
    if period not in sym_state:
        sym_state[period] = close_price
        return close_price
    k = 2.0 / (period + 1)
    prev = sym_state[period]
    new_ema = close_price * k + prev * (1 - k)
    sym_state[period] = new_ema
    return new_ema
```

**RSI (Relative Strength Index):**
```python
@staticmethod
def _rsi(values, period=14):
    if len(values) < period + 1:
        return None
    closes = list(values)
    gains = 0.0
    losses = 0.0
    for idx in range(-period, 0):
        diff = closes[idx] - closes[idx - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
```

**Bollinger Bands:**
```python
@staticmethod
def _bollinger(values, period=20, multiplier=2.0):
    if len(values) < period:
        return None, None, None, None
    window = list(values)[-period:]
    middle = sum(window) / period
    deviation = pstdev(window) * multiplier if period > 1 else 0.0
    upper = middle + deviation
    lower = middle - deviation
    width = upper - lower
    return middle, upper, lower, width
```

**ATR (Average True Range):**
```python
@staticmethod
def _atr(candles, period=14):
    rows = list(candles)
    if len(rows) < period + 1:
        return None
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
    return sum(true_ranges) / len(true_ranges) if true_ranges else None
```

**MACD:**
```python
def _macd_signal(self, state_key, macd_value, period=9):
    if state_key not in self._macd_signal_state:
        self._macd_signal_state[state_key] = macd_value
        return macd_value
    k = 2.0 / (period + 1)
    prev = self._macd_signal_state[state_key]
    next_signal = macd_value * k + prev * (1 - k)
    self._macd_signal_state[state_key] = next_signal
    return next_signal
```

### 3.5.6 Output 1: KeyDB Hash

**Key:** `indicator:latest:{exchange}:{symbol}:{interval}`

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

**TTL:** `INDICATOR_HISTORY_TTL_SEC` (mặc định 604800s = 7 ngày)

### 3.5.7 Output 2: KeyDB Sorted Set

**Key:** `indicator:history:{exchange}:{symbol}:{interval}`

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set |
| TTL | 604800 giây (7 ngày) |
| Score | `kline_start` (ms) |
| Member | JSON snapshot indicators |
| Max entries | `INDICATOR_HISTORY_MAX_ENTRIES` (10080 = 1 tuần phút) |

**JSON format:**
```json
{
  "exchange": "binance",
  "symbol": "BTCUSDT",
  "interval": "1m",
  "timestamp": 1672531190000,
  "close": 16501.00,
  "sma20": 16480.50,
  "sma50": 16460.25,
  "ema12": 16490.10,
  "ema26": 16475.30,
  "rsi14": 62.5,
  "bb_middle": 16480.50,
  "bb_upper": 16520.30,
  "bb_lower": 16440.70,
  "bb_width": 79.60,
  "macd": 14.80,
  "macd_signal": 10.20,
  "macd_histogram": 4.60,
  "atr14": 35.20,
  "volume_sma20": 120.50
}
```

### 3.5.8 Output 3: InfluxDB

**Measurement:** `indicators`

| Tag | Field |
|-----|-------|
| `symbol`, `exchange` | `sma20`, `sma50`, `ema12`, `ema26`, `rsi14`, `bb_middle`, `bb_upper`, `bb_lower`, `bb_width`, `macd`, `macd_signal`, `macd_histogram`, `atr14`, `volume_sma20`, `close` |

**Retention:** 90 ngày (InfluxDB retention policy)

### 3.5.9 State Management trong Flink

**Code:**
```python
self._closes: dict[str, deque] = {}            # {symbol: deque[close_price]}
self._volumes: dict[str, deque] = {}           # {symbol: deque[volume]}
self._candles: dict[str, deque] = {}           # {symbol: deque[dict]}
self._ema_state: dict[str, dict[int, float]] = {}  # {symbol: {period: ema_value}}
self._macd_signal_state: dict[str, float] = {}  # {symbol: macd_signal}
```

**State key:** `f"{exchange}:{symbol}:{interval}"`

**Lý do dùng state key có interval:**
- Cho phép tính indicators cho nhiều intervals cùng lúc
- Mỗi interval có buffer riêng

### 3.5.10 Trade-off: True EMA vs SMA Approximation

| Approach | Sensitivity | Use case |
|----------|-------------|----------|
| **True EMA** (exponential) | Nhạy với recent prices | Real-time trading |
| **SMA approximation** (window average) | Ít nhạy hơn | Historical analysis |

**Flink dùng True EMA** (exponential smoothing) → nhạy hơn với giá gần nhất.

---

## 3.6 Depth Stream Processing

### 3.6.1 Input

Kafka topic: `crypto_depth` (12 partitions)

### 3.6.2 Logic tổng quan

```
Depth message → DepthWriter → KeyDB Hash
```

### 3.6.3 Output: KeyDB Hash

**Key:** `orderbook:{exchange}:{symbol}`

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

### 3.6.4 Tính toán spread

```python
"best_bid":       float(bids[0][0]) if bids else 0,
"best_ask":       float(asks[0][0]) if asks else 0,
"spread":         round(float(asks[0][0]) - float(bids[0][0]), 8) if bids and asks else 0,
```

### 3.6.5 Batch-buffered Performance

```python
BATCH_SIZE = 50
FLUSH_INTERVAL = 0.3
```

**Throughput:** ~10,000 depth messages/giây per writer.

---

## 3.7 Trade Stream Processing

### 3.7.1 Input

Kafka topic: `crypto_trades` (12 partitions)

### 3.7.2 Logic tổng quan

```
Trade message → KeyDBTradeWriter → KeyDB Sorted Set
```

### 3.7.3 Output: KeyDB Sorted Set

**Key:** `trade:latest:{exchange}:{symbol}`

| Tham số | Giá trị |
|---------|---------|
| Type | Sorted Set (ZSET) |
| TTL | 3600 giây (1 giờ) — đã tăng từ 600s cho historical queries |
| Score | `trade_time` (ms) |
| Member | `{"p": price, "q": quantity, "t": trade_time, "m": is_buyer_maker, "T": event_time}` |
| Max Entries | 200 trades/symbol |

### 3.7.4 Member JSON format

```json
{
  "p": 16500.00,
  "q": 0.50000,
  "t": 1672531199000,
  "m": true,
  "T": 1672531199000
}
```

### 3.7.5 Deduplication

```python
# Dedup: remove existing entry for this trade_time
pipe.zremrangebyscore(key, trade_time, trade_time)
pipe.zadd(key, {trade_json: trade_time})
pipe.expire(key, self.TRADE_TTL_SEC)
```

**Lý do dedup:** Một trade có thể được gửi lại từ Kafka (replay), cần đảm bảo chỉ có 1 entry.

### 3.7.6 Max Entries Enforcement

```python
# Enforce max entries: keep newest MAX_ENTRIES
if count % self.MAX_ENTRIES == 0:
    pipe.zremrangebyrank(key, 0, -self.MAX_ENTRIES - 1)
```

**Logic:** Mỗi 200 writes, remove entries cũ nhất (giữ 200 mới nhất).

---

## 3.8 Tổng hợp Writers trong Flink

### 3.8.1 Bảng tổng hợp

| Writer | Input Topic | Output 1 | Output 2 | Output 3 |
|--------|-------------|----------|----------|----------|
| **KeyDBWriter** | crypto_ticker | Redis Hash `ticker:latest:{ex}:{sym}` | Redis ZSET `ticker:history:{ex}:{sym}` | - |
| **KeyDBKlineWriter** | crypto_klines (1s raw + 1m agg) | Redis ZSET `candle:1s:{ex}:{sym}` / `candle:1m:{ex}:{sym}` | Redis Hash `candle:latest:{ex}:{sym}` | - |
| **KlineWindowAggregator** | crypto_klines (1s) | Emits 1m candles (downstream) | - | - |
| **InfluxDBKlineWriter** | crypto_klines (1s raw + 1m agg) | InfluxDB `candles` measurement (1m closed only) | - | - |
| **InfluxDBWriter** | crypto_ticker | InfluxDB `market_ticks` measurement | - | - |
| **IndicatorWriter** | crypto_klines (1m closed) | Redis Hash `indicator:latest:{ex}:{sym}:{int}` | Redis ZSET `indicator:history:{ex}:{sym}:{int}` | InfluxDB `indicators` measurement |
| **DepthWriter** | crypto_depth | Redis Hash `orderbook:{ex}:{sym}` | - | - |
| **KeyDBTradeWriter** | crypto_trades | Redis ZSET `trade:latest:{ex}:{sym}` | - | - |

### 3.8.2 Số writers tổng cộng

- 8 writer classes
- 12 parallel instances mỗi writer (theo Flink parallelism)
- **Tổng cộng:** 96 writer instances

---

## 3.9 Pipeline Orchestration

### 3.9.1 Flink Job Structure

```python
def run():
    env = StreamExecutionEnvironment.get_execution_environment()
    # ... config ...

    # Ticker pipeline
    ticker_table = t_env.sql_query("SELECT ... FROM kafka_ticker")
    ds_dict = t_env.to_data_stream(ticker_table)
    ds_dict.flat_map(KeyDBWriter(), ...)
    ds_dict.flat_map(InfluxDBWriter(), ...)

    # Kline pipeline
    kline_table = t_env.sql_query("SELECT ... FROM kafka_klines")
    ds_kline_dict = t_env.to_data_stream(kline_table)

    # Branch 1: raw 1s
    ds_kline_dict.flat_map(KeyDBKlineWriter(), ...)
    ds_kline_dict.flat_map(InfluxDBKlineWriter(), ...)

    # Branch 2: 1s→1m aggregation
    ds_1m_candles = (
        ds_kline_dict
        .key_by(lambda v: json.loads(v)["exchange"] + ":" + json.loads(v)["symbol"])
        .process(KlineWindowAggregator(), ...)
    )
    ds_1m_candles.flat_map(KeyDBKlineWriter(), ...)
    ds_1m_candles.flat_map(InfluxDBKlineWriter(), ...)

    # Indicators
    ds_1m_candles.flat_map(IndicatorWriter(), ...)

    # Depth pipeline
    depth_table = t_env.sql_query("SELECT ... FROM kafka_depth")
    ds_depth_dict = t_env.to_data_stream(depth_table)
    ds_depth_dict.flat_map(DepthWriter(), ...)

    # Trade pipeline
    trades_table = t_env.sql_query("SELECT ... FROM kafka_trades")
    ds_trades_dict = t_env.to_data_stream(trades_table)
    ds_trades_dict.flat_map(KeyDBTradeWriter(), ...)

    env.execute("Crypto_MultiStream_Kafka_to_KeyDB_InfluxDB")
```

### 3.9.2 Key-by Strategy

| Stream | Key | Lý do |
|--------|-----|-------|
| **KlineWindowAggregator** | `f"{exchange}:{symbol}"` | Aggregate 1s → 1m per symbol |
| **IndicatorWriter** | `f"{exchange}:{symbol}:{interval}"` | Indicator state per symbol × interval |
| **Các writer khác** | Không key (parallel write) | Mỗi message independent |

### 3.9.3 DataStream Graph

```
kafka_ticker ──┬─→ KeyDBWriter ─────→ Redis
               └─→ InfluxDBWriter ──→ InfluxDB

kafka_klines ──┬─→ KeyDBKlineWriter (1s raw) ──→ Redis
               ├─→ InfluxDBKlineWriter (1s raw) ─→ InfluxDB
               │
               └─→ key_by(exchange:symbol) → KlineWindowAggregator
                                                  │
                              ┌───────────────────┼───────────────────┐
                              ▼                   ▼                   ▼
                       KeyDBKlineWriter    InfluxDBKlineWriter  IndicatorWriter
                        (1m agg)             (1m closed)         (1m closed)
                              │                   │                   │
                              ▼                   ▼                   ▼
                           Redis              InfluxDB         Redis + InfluxDB

kafka_depth ──→ DepthWriter ──→ Redis

kafka_trades ─→ KeyDBTradeWriter ──→ Redis
```

---

## 3.10 Performance & Throughput

### 3.10.1 Throughput per Writer

| Writer | Batch Size | Flush Interval | Throughput (msg/s) |
|--------|------------|---------------|---------------------|
| KeyDBWriter | 100 | 500ms | ~10,000 |
| KeyDBKlineWriter | 50 | 100ms | ~5,000 |
| InfluxDBWriter | 200 | 500ms | ~20,000 |
| InfluxDBKlineWriter | 500 | 3000ms | ~10,000 |
| IndicatorWriter | - | - | ~5,000 |
| DepthWriter | 50 | 300ms | ~10,000 |
| KeyDBTradeWriter | 100 | 500ms | ~10,000 |

### 3.10.2 Total System Throughput

- **Messages/giây:** ~70,000 (all writers combined)
- **Symbols:** 200 (Binance) + 20 (OKX)
- **Per symbol/giây:** ~350 messages

### 3.10.3 Latency Budget

```
Kafka → Flink parsing    : 5ms
Flink state update       : 1ms
Redis pipeline execute   : 2ms
Redis replication        : 1ms
─────────────────────────────────
Total Flink → Redis      : ~10ms

Kafka → InfluxDB write   : 5ms
InfluxDB batch write     : 50ms
─────────────────────────────────
Total Flink → InfluxDB   : ~55ms
```

---

## 3.11 Failure Handling

### 3.11.1 Flink Restart Strategy

```python
env.set_restart_strategy(
    RestartStrategies.failure_rate_restart(
        5,        # max failures
        600000,   # 10 minutes interval
        10000,    # 10 seconds delay
    )
)
```

### 3.11.2 Checkpoint Recovery

```
1. Flink job crash
2. Restart from latest checkpoint
3. Restore keyed state từ S3
4. Re-read Kafka từ committed offset
5. Replay unprocessed messages
6. Resume processing
```

### 3.11.3 Writer-level Error Handling

**Pattern (tất cả writers):**
```python
def flat_map(self, value):
    try:
        # process
        self._buffer.append(record)
        if len(self._buffer) >= BATCH_SIZE:
            self._flush()
    except Exception as e:
        log.error(f"[Writer] flat_map error: {e}")
    return []
```

**Buffer flush error:**
```python
try:
    pipe.execute()
except Exception as e:
    log.error(f"[Writer] flush error (dropped {len(self._buffer)} records): {e}")
finally:
    self._buffer.clear()
    self._last_flush = time.time()
```

**Strategy:**
- Log error
- Drop buffered records (không block pipeline)
- Continue processing new messages
- Không crash job (chỉ 1 worker fail)

### 3.11.4 Redis Sentinel Failover

```
Master down → Sentinel detects (5s)
Sentinel promotes slave → new master
Flink reconnects to new master (10s)
State continues from checkpoint
```

---

## 3.12 Flink KeyDB Connection

### 3.12.1 Sentinel Connection

```python
from common.flink_redis_sentinel import get_flink_redis

def open(self, runtime_context):
    self._r = get_flink_redis()
```

### 3.12.2 Connection Pool

- Mỗi Flink TaskManager có 1 connection pool
- Mỗi writer instance lấy 1 connection từ pool
- Connection reused across batches (không reconnect mỗi batch)

### 3.12.3 Sentinel Configuration

| Setting | Value |
|---------|-------|
| Sentinel hosts | redis-sentinel-1:26379, redis-sentinel-2:26379, redis-sentinel-3:26379 |
| Master name | mymaster |
| Quorum | 2 (cần 2/3 sentinels agree) |
| Failover timeout | 30s |

---

## 3.13 Tổng hợp Redis Key Patterns

### 3.13.1 Bảng tổng hợp

| Key Pattern | Type | TTL | Content |
|-------------|------|-----|---------|
| `ticker:latest:{ex}:{sym}` | Hash | - | Latest ticker (price, bid, ask, volume, change24h, event_time, exchange) |
| `ticker:history:{ex}:{sym}` | Sorted Set | 600s | Price history for watchlist mini-chart (score=event_time, member=price:volume) |
| `candle:1s:{ex}:{sym}` | Sorted Set | 1 ngày | 1s candle history (score=kline_start, member=JSON) |
| `candle:1m:{ex}:{sym}` | Sorted Set | 7 ngày | 1m candle history (score=kline_start, member=JSON) |
| `candle:latest:{ex}:{sym}` | Hash | - | Latest candle info (open, high, low, close, volume, is_closed, interval, exchange) |
| `indicator:latest:{ex}:{sym}:{int}` | Hash | 7 ngày | Latest indicators (sma20, ema12, rsi14, macd, ...) |
| `indicator:history:{ex}:{sym}:{int}` | Sorted Set | 7 ngày | Indicator history (score=kline_start, member=JSON snapshot) |
| `orderbook:{ex}:{sym}` | Hash | 300s | Order book (bids, asks, best_bid, best_ask, spread) |
| `trade:latest:{ex}:{sym}` | Sorted Set | 3600s | Trade tape (score=trade_time, member=JSON, max 200) |

### 3.13.2 Tổng hợp InfluxDB Measurements

| Measurement | Tags | Fields |
|-------------|------|--------|
| `market_ticks` | symbol, exchange | price, bid, ask, volume, quote_volume, price_change_pct, trade_count |
| `candles` | symbol, exchange, interval | open, high, low, close, volume, quote_volume, trade_count, is_closed |
| `indicators` | symbol, exchange | sma20, sma50, ema12, ema26, rsi14, bb_middle, bb_upper, bb_lower, bb_width, macd, macd_signal, macd_histogram, atr14, volume_sma20, close |

---

**Tiếp theo: Part 4 — Spark Lakehouse (Bronze / Silver / Gold Tables)**

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# PHẦN 4: TẦNG LAKEHOUSE (SPARK + ICEBERG)

---

## 4.1 Tổng quan Lakehouse

**Mô tả:** Lakehouse là tầng batch processing trong Lambda Architecture. Dữ liệu từ Kafka được Spark Structured Streaming đọc và ghi vào Iceberg tables theo mô hình **Medallion Architecture** (Bronze → Silver → Gold), cho phép lưu trữ dài hạn, query SQL, và time-travel.

### 4.1.1 Medallion Architecture (3 layers)

| Layer | Mục đích | Latency | Tables |
|-------|----------|---------|--------|
| **Bronze** | Raw data, chưa transform | ~1 phút | coin_ticker, coin_trades, coin_klines |
| **Silver** | Cleaned, deduplicated, unified | ~1 giờ | ticker_unified, kline_multi_timeframe |
| **Gold** | Business metrics, aggregated | ~5 phút | market_overview, coin_ticker, momentum_indicators, indicator_history, market_dominance, volatility_ranking, movers_ranking, sector_performance, news_sentiment |

### 4.1.2 Vị trí trong data flow

```
Kafka (Part 2)
       │
       │  Spark Streaming (1-minute micro-batch)
       ▼
┌──────────────────────────────────────────┐
│           BRONZE LAYER                   │
│  Raw data, append-only, partitioned     │
│  by day                                  │
└────┬─────────────────────────────────┬───┘
     │                                 │
     │ Bronze → Silver ETL (hourly)    │
     ▼                                 ▼
┌──────────────────────────────────────────┐
│           SILVER LAYER                   │
│  Cleaned, deduplicated, unified         │
│  Binance + OKX merged                    │
└────┬─────────────────────────────────┬───┘
     │                                 │
     │ Silver → Gold ETL (5-min batch) │
     ▼                                 ▼
┌──────────────────────────────────────────┐
│           GOLD LAYER                     │
│  Business metrics, ready for API/AI     │
│  Latest snapshot, rankings, indicators  │
└──────────────────────────────────────────┘
       │
       ▼
  Trino (SQL query)
       │
       ▼
  FastAPI + Trino Client
```

### 4.1.3 Tại sao dùng Iceberg

| Lợi ích | Giải thích |
|---------|-----------|
| **ACID transactions** | Đảm bảo data consistency (không partial writes) |
| **Time travel** | Query data tại thời điểm bất kỳ (rollback, audit) |
| **Partition evolution** | Thay đổi partition scheme không cần rewrite data |
| **Hidden partitioning** | Query optimizer tự động filter partitions |
| **Schema evolution** | Add/rename columns without breaking readers |
| **MinIO/S3 support** | Lưu trên object storage, cost-effective |
| **Multi-engine** | Spark, Trino, Flink, Hive cùng đọc |

### 4.1.4 Storage Architecture

```
s3a://cryptoprice/iceberg/
├── bronze/
│   ├── coin_ticker/
│   ├── coin_trades/
│   ├── coin_klines/
│   ├── ticker/         (alternative path)
│   ├── kline/          (alternative path)
│   └── news/
├── silver/
│   ├── ticker_unified/
│   └── kline_multi_timeframe/
└── gold/
    ├── market_overview/
    ├── coin_ticker/
    ├── momentum_indicators/
    ├── indicator_history/
    ├── market_dominance/
    ├── volatility_ranking/
    ├── movers_ranking/
    ├── sector_performance/
    └── news_sentiment/
```

**Catalog:** PostgreSQL (lưu metadata Iceberg)

**Format:** Apache Iceberg (Parquet data + Avro metadata)

---

## 4.2 Cấu hình Spark

### 4.2.1 Spark Session Config (cho cả Bronze/Silver/Gold)

```python
SparkSession.builder \
    .appName("BinanceDualStreamToIceberg")
    .config("spark.sql.session.timeZone", "UTC")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.iceberg_catalog",
            "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.iceberg_catalog.type", "jdbc")
    .config("spark.sql.catalog.iceberg_catalog.uri",
            f"jdbc:postgresql://{POSTGRES_HOST}:5432/iceberg_catalog")
    .config("spark.sql.catalog.iceberg_catalog.jdbc.user", POSTGRES_USER)
    .config("spark.sql.catalog.iceberg_catalog.jdbc.password", POSTGRES_PASSWORD)
    .config("spark.sql.catalog.iceberg_catalog.warehouse", "s3://cryptoprice/iceberg")
    .config("spark.sql.catalog.iceberg_catalog.io-impl",
            "org.apache.iceberg.aws.s3.S3FileIO")
    .config("spark.sql.catalog.iceberg_catalog.s3.endpoint", MINIO_ENDPOINT)
    .config("spark.sql.catalog.iceberg_catalog.s3.access-key-id", MINIO_ACCESS_KEY)
    .config("spark.sql.catalog.iceberg_catalog.s3.secret-access-key", MINIO_SECRET_KEY)
    .config("spark.sql.catalog.iceberg_catalog.s3.path-style-access", "true")
    .config("spark.sql.catalog.iceberg_catalog.client.region", "us-east-1")
    .config("spark.hadoop.fs.s3a.endpoint", MINIO_ENDPOINT)
    .config("spark.hadoop.fs.s3a.access.key", MINIO_ACCESS_KEY)
    .config("spark.hadoop.fs.s3a.secret.key", MINIO_SECRET_KEY)
    .config("spark.hadoop.fs.s3a.path.style.access", "true")
    .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem")
    .config("spark.streaming.stopGracefullyOnShutdown", "true")
    .config("spark.streaming.backpressure.enabled", "true")
    .config("spark.task.maxFailures", "4")
    .config("spark.cores.max", "2")
    .getOrCreate()
```

### 4.2.2 Key Configurations

| Config | Value | Purpose |
|--------|-------|---------|
| `spark.sql.extensions` | `IcebergSparkSessionExtensions` | Enable Iceberg SQL extensions |
| `spark.sql.catalog.iceberg_catalog.type` | `jdbc` (or `hadoop`) | Catalog backend |
| `spark.sql.catalog.iceberg_catalog.warehouse` | `s3://cryptoprice/iceberg` | Iceberg warehouse location |
| `spark.sql.catalog.iceberg_catalog.io-impl` | `org.apache.iceberg.aws.s3.S3FileIO` | S3 file IO |
| `spark.streaming.backpressure.enabled` | `true` | Tự động backpressure |
| `spark.task.maxFailures` | `4` | Retry 4 lần trước khi fail task |
| `spark.cores.max` | `2` | Mỗi executor 2 cores |
| `spark.streaming.stopGracefullyOnShutdown` | `true` | Graceful shutdown |

### 4.2.3 Streaming Source (Kafka)

```python
spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_BOOTSTRAP)
    .option("subscribe", topic)
    .option("startingOffsets", "latest")
    .option("failOnDataLoss", "false")
    .option("maxOffsetsPerTrigger", 500_000)
    .load()
    .selectExpr("substring(value, 6, length(value)-5) as avro_value")
    .select(from_avro(col("avro_value"), avro_schema).alias("data"))
    .select("data.*")
```

**`maxOffsetsPerTrigger: 500_000`** — giới hạn 500K messages/micro-batch để tránh OOM.

---

## 4.3 BRONZE LAYER — Raw Data

### 4.3.1 Tổng quan Bronze

**Mục đích:** Lưu raw data từ Kafka, không transform, không validate. Append-only, partitioned by day.

**Quy tắc xử lý Bronze:**
1. **Deserialize Avro:** Strip 5-byte Confluent header, decode Avro binary
2. **Cast timestamp:** `event_time` (Long ms) → `TIMESTAMP`
3. **Add ingested_at:** `current_timestamp()`
4. **Deduplicate:** `dropDuplicates(["symbol", "event_timestamp"])` với watermark
5. **Trigger:** 1 minute micro-batch
6. **Output Mode:** Append
7. **Filter (Klines):** Chỉ `is_closed = true`

### 4.3.2 Schema Evolution

Best-effort schema evolution: nếu column chưa tồn tại, thêm vào.

```python
def _ensure_column(spark, table_name, column_name, column_type):
    try:
        spark.sql(f"ALTER TABLE {table_name} ADD COLUMNS ({column_name} {column_type})")
    except Exception as exc:
        if "already exists" in str(exc) or "Cannot add duplicate" in str(exc):
            pass  # Column đã tồn tại
        else:
            logger.warning("Could not add column: %s", exc)
```

**Lý do:** Khi schema mới được thêm vào Kafka (ví dụ thêm field `exchange`), Bronze cần tự động thêm column mà không crash.

### 4.3.3 Bảng Bronze: `coin_ticker`

**Path:** `s3a://cryptoprice/iceberg/bronze/coin_ticker` (hoặc `ticker` theo schema cũ)

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

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS iceberg_catalog.crypto_lakehouse.coin_ticker (
    event_time          BIGINT,
    symbol              STRING,
    exchange            STRING,
    close               DOUBLE,
    bid                 DOUBLE,
    ask                 DOUBLE,
    h24_open            DOUBLE,
    h24_high            DOUBLE,
    h24_low             DOUBLE,
    h24_volume          DOUBLE,
    h24_quote_volume    DOUBLE,
    h24_price_change    DOUBLE,
    h24_price_change_pct DOUBLE,
    h24_trade_count     BIGINT,
    event_timestamp     TIMESTAMP,
    ingested_at         TIMESTAMP
) USING iceberg
PARTITIONED BY (days(event_timestamp))
```

**Streaming code:**
```python
ticker_df = (
    read_kafka(spark, "crypto_ticker", TICKER_AVRO_SCHEMA)
    .filter(col("event_time").isNotNull())
    .withColumn("event_timestamp", (col("event_time") / 1000).cast("timestamp"))
    .withColumn("ingested_at", current_timestamp())
    .select("event_time", "symbol", "close", "bid", "ask", ...)
    .withWatermark("event_timestamp", "1 minute")
    .dropDuplicates(["exchange", "symbol", "event_timestamp"])
)

ticker_query = ticker_df.writeStream
    .format("iceberg")
    .outputMode("append")
    .trigger(processingTime="1 minute")
    .option("checkpointLocation", CHECKPOINT_TICKER)
    .toTable(ICEBERG_TABLE_TICKER)
```

### 4.3.4 Bảng Bronze: `coin_trades`

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

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS iceberg_catalog.crypto_lakehouse.coin_trades (
    event_time      BIGINT,
    symbol          STRING,
    exchange        STRING,
    agg_trade_id    BIGINT,
    price           DOUBLE,
    quantity        DOUBLE,
    trade_time      BIGINT,
    is_buyer_maker  BOOLEAN,
    event_timestamp TIMESTAMP,
    trade_timestamp TIMESTAMP,
    ingested_at     TIMESTAMP
) USING iceberg
PARTITIONED BY (days(trade_timestamp))
```

### 4.3.5 Bảng Bronze: `coin_klines`

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
| `interval` | STRING | Candle interval (1s/1m/...) |
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

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS iceberg_catalog.crypto_lakehouse.coin_klines (
    event_time      BIGINT,
    symbol          STRING,
    exchange        STRING,
    kline_start     BIGINT,
    kline_close     BIGINT,
    interval        STRING,
    open            DOUBLE,
    high            DOUBLE,
    low             DOUBLE,
    close           DOUBLE,
    volume          DOUBLE,
    quote_volume    DOUBLE,
    trade_count     BIGINT,
    is_closed       BOOLEAN,
    kline_timestamp TIMESTAMP,
    ingested_at     TIMESTAMP
) USING iceberg
PARTITIONED BY (days(kline_timestamp))
```

### 4.3.6 Checkpoint Locations

| Topic | Checkpoint Path |
|-------|-----------------|
| `crypto_ticker` | `s3://cryptoprice/checkpoints/crypto_ticker_v1` |
| `crypto_trades` | `s3://cryptoprice/checkpoints/crypto_trades_v1` |
| `crypto_klines` | `s3://cryptoprice/checkpoints/crypto_klines_v1` |

### 4.3.7 Bronze Streaming Queries

**Code pattern:**
```python
def _start_query_with_retry(start_query_fn, query_name, max_retries=5, backoff_sec=15):
    attempt = 0
    while True:
        try:
            query = start_query_fn()
            return query
        except Exception as exc:
            attempt += 1
            if attempt >= max_retries:
                raise
            time.sleep(backoff_sec * attempt)
```

**3 streaming queries chạy song song:**
- Ticker query (1-minute trigger)
- Trades query (1-minute trigger)
- Klines query (1-minute trigger)

**Backpressure:** `spark.streaming.backpressure.enabled=true` — Spark tự động giảm rate khi sink chậm.

---

## 4.4 SILVER LAYER — Cleaned & Unified Data

### 4.4.1 Tổng quan Silver

**Mục đích:** Clean, deduplicate, validate, và unify data từ Bronze. Merge Binance + OKX data, tính toán derived metrics.

**Schedule:** Hourly batch jobs

**Lookback:** 2 ngày (cho late arrivals)

### 4.4.2 SilverTickerTransformation

**Transformations (6 steps):**

1. **Deduplication:**
```python
window_spec = Window.partitionBy("symbol", "event_time", "exchange") \
                    .orderBy(col("ingested_at").desc())
deduped = bronze_df.withColumn("row_num", row_number().over(window_spec)) \
                  .filter(col("row_num") == 1) \
                  .drop("row_num")
```

2. **Validation:**
```python
validated = deduped.filter(
    (col("price") > 0) &
    (col("price") < 1_000_000) &  # Loại outliers
    (col("volume") >= 0)
)
```

3. **Pivot by exchange (Binance + OKX):**
```python
unified = validated.groupBy("symbol", "event_time").agg(
    first(when(col("exchange") == "binance", col("price"))).alias("price_binance"),
    first(when(col("exchange") == "okx", col("price"))).alias("price_okx"),
    first(when(col("exchange") == "binance", col("volume"))).alias("volume_binance"),
    first(when(col("exchange") == "okx", col("volume"))).alias("volume_okx")
)
```

4. **Calculate mid-price:**
```python
unified = unified.withColumn(
    "price_mid",
    when(col("price_binance").isNotNull() & col("price_okx").isNotNull(),
         (col("price_binance") + col("price_okx")) / 2)
    .when(col("price_binance").isNotNull(), col("price_binance"))
    .when(col("price_okx").isNotNull(), col("price_okx"))
    .otherwise(None)
)
```

5. **Calculate spread percentage:**
```python
unified = unified.withColumn(
    "spread_pct",
    when(col("price_binance").isNotNull() & col("price_okx").isNotNull() & (col("price_mid") > 0),
         (abs(col("price_binance") - col("price_okx")) / col("price_mid")) * 100)
    .otherwise(0)
)
```

6. **Quality scoring:**
```python
unified = unified.withColumn(
    "quality_score",
    when(col("price_binance").isNotNull() & col("price_okx").isNotNull(), 100)  # Dual source
    .when(col("price_binance").isNotNull() | col("price_okx").isNotNull(), 50)  # Single source
    .otherwise(0)
)
```

### 4.4.3 Bảng Silver: `ticker_unified`

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
| `quality_score` | INT | Data quality (0/50/100) |
| `last_updated` | TIMESTAMP | Last update time |
| `_partition_date` | DATE | Partition date |

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS iceberg_catalog.silver.ticker_unified (
    event_time      BIGINT,
    symbol          STRING,
    price_binance   DOUBLE,
    price_okx       DOUBLE,
    price_mid       DOUBLE,
    volume_binance  DOUBLE,
    volume_okx      DOUBLE,
    volume_total    DOUBLE,
    spread_pct      DOUBLE,
    quality_score   INT,
    last_updated    TIMESTAMP,
    _partition_date DATE
) USING iceberg
PARTITIONED BY (_partition_date)
```

**Tại sao quality_score quan trọng:**
- 100 = Có cả Binance + OKX (đáng tin cậy nhất)
- 50 = Chỉ có 1 exchange (có thể thin liquidity)
- 0 = Không có data (skip)

### 4.4.4 SilverKlineAggregation

**Multi-timeframe aggregation strategy:**

| Source Interval | Target Interval | Multiplier |
|-----------------|-----------------|------------|
| 1m | 5m | 5 |
| 5m | 15m | 3 |
| 15m | 1h | 4 |
| 1h | 4h | 4 |
| 1h | 1d | 24 |

**Unified approach (cache + chain aggregation):**
```
1m → 5m (cache) → 15m (cache) → 1h
```

**Tại sao cache intermediate results:**
- 1m → 5m: 1 lần aggregation
- 5m → 15m: đọc từ cached 5m (không recompute từ 1m)
- 15m → 1h: đọc từ cached 15m
- **Tiết kiệm I/O** so với việc aggregate độc lập từ 1m

**Code:**
```python
def aggregate_klines_unified(spark):
    # Read 1m từ Bronze
    bronze_1m = spark.table("iceberg.crypto_lakehouse.kline") \
                    .filter(col("interval") == "1m")

    # 1m → 5m
    kline_5m = bronze_1m.groupBy(
        "symbol",
        window(from_unixtime(col("event_time") / 1000), "5 minutes").alias("time_window")
    ).agg(
        first("open_price").alias("open_price"),
        _max("high_price").alias("high_price"),
        _min("low_price").alias("low_price"),
        first(col("close_price"), ignorenulls=True).alias("close_price"),
        _sum("volume").alias("volume"),
        _sum("trade_count").alias("trade_count")
    ).select(...).withColumn("interval", lit("5m"))

    kline_5m.cache()  # Cache để dùng cho 5m → 15m

    # 5m → 15m (đọc từ cached 5m)
    kline_15m = kline_5m.groupBy(...).agg(...)
    kline_15m.cache()

    # 15m → 1h
    kline_1h = kline_15m.groupBy(...).agg(...)
```

**Công thức Aggregate:**

```
open         = first candle open
high         = max(all highs)
low          = min(all lows)
close        = last candle close
volume       = sum(all volumes)
trade_count  = sum(all trade_counts)
```

### 4.4.5 Bảng Silver: `kline_multi_timeframe`

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

**DDL:**
```sql
CREATE TABLE IF NOT EXISTS iceberg_catalog.silver.kline_multi_timeframe (
    event_time      BIGINT,
    symbol          STRING,
    `interval`      STRING,
    open_price      DOUBLE,
    high_price      DOUBLE,
    low_price       DOUBLE,
    close_price     DOUBLE,
    volume          DOUBLE,
    trade_count     BIGINT,
    is_closed       BOOLEAN,
    quality_score   INT,
    last_updated    TIMESTAMP,
    _partition_date DATE
) USING iceberg
PARTITIONED BY (_partition_date, `interval`)
```

**Các intervals có sẵn:**

| Interval | Source Aggregation | Use case |
|----------|-------------------|----------|
| 5m | 1m → 5m | Short-term trading |
| 15m | 5m → 15m | Intraday swing |
| 1h | 15m → 1h | Day trading |
| 4h | 1h → 4h | Swing trading |
| 1d | 1h → 1d | Long-term analysis |

---

## 4.5 GOLD LAYER — Business Metrics

### 4.5.1 Tổng quan Gold

**Mục đích:** Pre-aggregated business metrics cho dashboards, API queries, và AI training.

**Schedule:** 5-minute batch jobs

**Tables overview:**

| Table | Source | Use case |
|-------|--------|----------|
| `market_overview` | silver | Fast API queries cho market metrics |
| `coin_ticker` | silver | Fast API queries cho ticker data |
| `momentum_indicators` | silver kline | Latest indicators per symbol |
| `indicator_history` | silver kline | Full indicator history |
| `market_dominance` | silver | BTC/ETH dominance, market cap |
| `volatility_ranking` | silver | Top volatile symbols |
| `movers_ranking` | silver | Top gainers/losers |
| `sector_performance` | silver | Performance by sector |
| `news_sentiment` | bronze.news + silver.news | News sentiment aggregation |

### 4.5.2 Bảng Gold: `market_overview`

**Path:** `s3a://cryptoprice/iceberg/gold/market_overview`

**Partitioning:** `_partition_date`

**Source:** silver.ticker_unified

**Transformations:**

1. **Latest price per symbol:**
```python
latest_window = Window.partitionBy("symbol").orderBy(desc("event_time"))
latest_df = silver_df.withColumn("row_num", row_number().over(latest_window)) \
                     .filter(col("row_num") == 1)
```

2. **24h price change (compare with 24h ago):**
```python
window_24h = Window.partitionBy("symbol").orderBy("event_time").rangeBetween(-86_400_000, 0)
metrics = silver_df.withColumn(
    "price_24h_ago",
    lag("price_mid", 1).over(window_24h)
).withColumn(
    "change_pct_24h",
    when(col("price_24h_ago").isNotNull() & (col("price_24h_ago") > 0),
         ((col("price_mid") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
    .otherwise(0)
)
```

3. **Top 10 gainers/losers (array of structs):**
```python
top_gainers = latest_metrics.orderBy(desc("change_pct_24h")).limit(10) \
                            .select(struct(
                                col("symbol"),
                                col("change_pct_24h").alias("change_pct"),
                                col("price_mid").alias("price")
                            ).alias("gainer")) \
                            .agg(collect_list("gainer").alias("top_10_gainers"))
```

4. **Aggregate metrics:**
```python
overview = latest_metrics.agg(
    count("symbol").alias("total_symbols"),
    _sum("volume_total").alias("total_volume_24h"),
    avg("spread_pct").alias("avg_spread_pct"),
    _sum(col("price_mid") * col("volume_total")).alias("market_cap_total")
)
```

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `snapshot_time` | TIMESTAMP | When this snapshot was taken |
| `total_symbols` | INT | Number of active symbols |
| `total_volume_24h` | DOUBLE | Total 24h volume across all symbols |
| `avg_spread_pct` | DOUBLE | Average spread between Binance + OKX |
| `top_10_gainers` | ARRAY<STRUCT<symbol:STRING, change_pct:DOUBLE, price:DOUBLE>> | Top 10 gainers |
| `top_10_losers` | ARRAY<STRUCT<symbol:STRING, change_pct:DOUBLE, price:DOUBLE>> | Top 10 losers |
| `market_cap_total` | DOUBLE | Total market cap estimate |
| `_partition_date` | DATE | Partition date |

### 4.5.3 Bảng Gold: `coin_ticker`

**Path:** `s3a://cryptoprice/iceberg/gold/coin_ticker`

**Source:** silver.ticker_unified

**Mục đích:** Fast API queries cho market overview (FastAPI `/api/market/overview` endpoint).

**Transformations:**

```python
# Get latest price per symbol
latest_df = silver_df.withColumn("row_num", row_number().over(Window.partitionBy("symbol").orderBy(desc("event_time")))) \
                     .filter(col("row_num") == 1)

# Get price 24h ago
price_24h_df = silver_df.filter(
    (col("event_time") >= time_24h_ago - 300_000) &
    (col("event_time") <= time_24h_ago + 300_000)
).groupBy("symbol").agg(expr("avg(price_mid) as price_24h_ago"))

# Get 24h volume
volume_24h_df = silver_df.filter(col("event_time") >= time_24h_ago) \
                         .groupBy("symbol").agg(expr("sum(volume_total) as h24_volume"))

# Calculate 24h price change
result_df = result_df.withColumn(
    "h24_price_change_pct",
    when((col("price_24h_ago").isNotNull()) & (col("price_24h_ago") > 0),
         ((col("close") - col("price_24h_ago")) / col("price_24h_ago")) * 100)
    .otherwise(0)
)

# Market cap = price * volume * 10 (rough estimate)
result_df = result_df.withColumn("market_cap", col("h24_quote_volume") * 10)

# Rank by quote volume
result_df = result_df.withColumn("rank",
    expr("row_number() OVER (ORDER BY h24_quote_volume DESC)")
)
```

**Schema:**

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

**Note:** Filter `symbol LIKE '%USDT'` để chỉ lấy USDT pairs.

### 4.5.4 Bảng Gold: `momentum_indicators`

**Path:** `s3a://cryptoprice/iceberg/gold/momentum_indicators`

**Source:** silver.kline_multi_timeframe (1h)

**Mục đích:** Latest indicators per symbol, dùng cho `/api/indicators/snapshot`.

**Transformations (chi tiết trong Part 6):**

| Indicator | Period | Use |
|-----------|--------|-----|
| RSI_14 | 14 | Overbought/oversold |
| MACD | 12/26/9 | Trend |
| Bollinger Bands | 20/2σ | Volatility |
| SMA20/50 | 20/50 | Trend |
| EMA12/26 | 12/26 | Trend |
| Volume SMA20 | 20 | Volume trend |

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `symbol` | STRING | Trading pair |
| `snapshot_time` | TIMESTAMP | When calculated |
| `current_price` | DOUBLE | Current price |
| `rsi_14` | DOUBLE | RSI 14 |
| `macd` | DOUBLE | MACD line |
| `macd_signal` | DOUBLE | MACD signal |
| `macd_histogram` | DOUBLE | MACD histogram |
| `bb_upper` | DOUBLE | Bollinger upper |
| `bb_middle` | DOUBLE | Bollinger middle |
| `bb_lower` | DOUBLE | Bollinger lower |
| `bb_width` | DOUBLE | Bollinger width |
| `volume_sma_20` | DOUBLE | Volume SMA 20 |
| `price_sma_20` | DOUBLE | Price SMA 20 |
| `price_sma_50` | DOUBLE | Price SMA 50 |
| `price_ema_12` | DOUBLE | Price EMA 12 |
| `price_ema_26` | DOUBLE | Price EMA 26 |
| `_partition_date` | DATE | Partition date |

### 4.5.5 Bảng Gold: `indicator_history`

**Path:** `s3a://cryptoprice/iceberg/gold/indicator_history`

**Source:** silver.kline_multi_timeframe (1h)

**Mục đích:** Full indicator history cho AI training data.

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `exchange` | STRING | Exchange source |
| `symbol` | STRING | Trading pair |
| `interval` | STRING | 1h (constant) |
| `candle_time` | BIGINT | Candle time (ms) |
| `candle_timestamp` | TIMESTAMP | Candle time |
| `close_price` | DOUBLE | Close price |
| `volume` | DOUBLE | Volume |
| `rsi_14` | DOUBLE | RSI 14 |
| `macd` | DOUBLE | MACD line |
| `macd_signal` | DOUBLE | MACD signal |
| `macd_histogram` | DOUBLE | MACD histogram |
| `bb_upper` | DOUBLE | Bollinger upper |
| `bb_middle` | DOUBLE | Bollinger middle |
| `bb_lower` | DOUBLE | Bollinger lower |
| `bb_width` | DOUBLE | Bollinger width |
| `volume_sma_20` | DOUBLE | Volume SMA 20 |
| `price_sma_20` | DOUBLE | Price SMA 20 |
| `price_sma_50` | DOUBLE | Price SMA 50 |
| `price_ema_12` | DOUBLE | Price EMA 12 |
| `price_ema_26` | DOUBLE | Price EMA 26 |
| `computed_at` | TIMESTAMP | When computed |
| `_partition_date` | DATE | Partition date |

**Partitioning:** `_partition_date, interval, exchange`

**Write mode:** Append (full history)

### 4.5.6 Bảng Gold: `market_dominance`

**Path:** `s3a://cryptoprice/iceberg/gold/market_dominance`

**Source:** silver.ticker_unified

**Mục đích:** BTC/ETH dominance, market cap breakdown.

**Transformations:**
```python
# Total market cap
total_market_cap = market_df.agg(_sum("market_cap")).collect()[0][0] or 1

# BTC dominance
btc_cap = market_df.filter(col("symbol") == "BTCUSDT").agg(_sum("market_cap")).collect()[0][0] or 0
btc_dominance = (btc_cap / total_market_cap) * 100

# ETH dominance
eth_cap = market_df.filter(col("symbol") == "ETHUSDT").agg(_sum("market_cap")).collect()[0][0] or 0
eth_dominance = (eth_cap / total_market_cap) * 100

# Stablecoin volume %
stablecoins = ["USDCUSDT", "BUSDUSDT", "TUSDUSDT", "DAIUSDT"]
stablecoin_vol = market_df.filter(col("symbol").isin(stablecoins)) \
                          .agg(_sum("volume_total")).collect()[0][0] or 0
stablecoin_pct = (stablecoin_vol / total_volume) * 100

# Altcoin volume %
major_coins = ["BTCUSDT", "ETHUSDT"] + stablecoins
altcoin_vol = market_df.filter(~col("symbol").isin(major_coins)) \
                        .agg(_sum("volume_total")).collect()[0][0] or 0
altcoin_pct = (altcoin_vol / total_volume) * 100
```

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `snapshot_time` | TIMESTAMP | When calculated |
| `btc_dominance_pct` | DOUBLE | BTC market cap % |
| `eth_dominance_pct` | DOUBLE | ETH market cap % |
| `stablecoin_volume_pct` | DOUBLE | Stablecoin volume % |
| `altcoin_volume_pct` | DOUBLE | Altcoin volume % |
| `total_market_cap` | DOUBLE | Total market cap |
| `total_volume_24h` | DOUBLE | Total 24h volume |
| `active_symbols` | INT | Number of active symbols |
| `_partition_date` | DATE | Partition date |

### 4.5.7 Bảng Gold: `volatility_ranking`

**Path:** `s3a://cryptoprice/iceberg/gold/volatility_ranking`

**Source:** silver.ticker_unified

**Mục đích:** Rank symbols theo volatility (1h, 24h, 7d).

**Transformations:**
```python
# Calculate volatility (stddev of price) for 1h
vol_1h = ticker_df.filter(col("event_time") >= time_1h_ago) \
                 .groupBy("symbol").agg(stddev("price_mid").alias("volatility_1h"))

# 24h volatility + high/low
vol_24h = ticker_df.filter(col("event_time") >= time_24h_ago) \
                  .groupBy("symbol").agg(
                      stddev("price_mid").alias("volatility_24h"),
                      _max("price_mid").alias("high_24h"),
                      _min("price_mid").alias("low_24h")
                  )

# 7d volatility
vol_7d = ticker_df.filter(col("event_time") >= time_7d_ago) \
                 .groupBy("symbol").agg(stddev("price_mid").alias("volatility_7d"))

# Price range % = (high - low) / low * 100
result = result.withColumn(
    "price_range_pct_24h",
    when(col("low_24h") > 0,
         ((col("high_24h") - col("low_24h")) / col("low_24h")) * 100)
    .otherwise(0)
)

# Rank by 24h volatility
result = result.withColumn("rank_by_volatility",
    row_number().over(Window.orderBy(desc("volatility_24h")))
)
```

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `symbol` | STRING | Trading pair |
| `snapshot_time` | TIMESTAMP | When calculated |
| `volatility_1h` | DOUBLE | 1h volatility (stddev) |
| `volatility_24h` | DOUBLE | 24h volatility |
| `volatility_7d` | DOUBLE | 7d volatility |
| `rank_by_volatility` | INT | Rank by 24h vol |
| `price_range_pct_24h` | DOUBLE | 24h price range % |
| `_partition_date` | DATE | Partition date |

### 4.5.8 Bảng Gold: `movers_ranking`

**Path:** `s3a://cryptoprice/iceberg/gold/movers_ranking`

**Source:** silver.ticker_unified

**Mục đích:** Top gainers/losers cho 1h, 24h, 7d timeframes.

**Transformations:**
```python
timeframes = {
    "1h":  now_ms - (1 * 60 * 60 * 1000),
    "24h": now_ms - (24 * 60 * 60 * 1000),
    "7d":  now_ms - (7 * 24 * 60 * 60 * 1000)
}

for tf_name, tf_start in timeframes.items():
    # First and last price in timeframe
    first_price = df_period.withColumn("rank", row_number().over(Window.partitionBy("symbol").orderBy(asc("event_time")))) \
                          .filter(col("rank") == 1) \
                          .select(col("symbol"), col("price_mid").alias("price_start"))

    last_price = df_period.withColumn("rank", row_number().over(Window.partitionBy("symbol").orderBy(desc("event_time")))) \
                         .filter(col("rank") == 1) \
                         .select(col("symbol"), col("price_mid").alias("price_end"))

    # Calculate change %
    changes = first_price.join(last_price, "symbol") \
                        .withColumn("change_pct",
                            when(col("price_start") > 0,
                                 ((col("price_end") - col("price_start")) / col("price_start")) * 100)
                            .otherwise(0))

    # Top 20 gainers + Top 20 losers
    gainers = changes.filter(col("change_pct") > 0) \
                    .orderBy(desc("change_pct")).limit(20) \
                    .withColumn("category", lit("gainer"))

    losers = changes.filter(col("change_pct") < 0) \
                   .orderBy(asc("change_pct")).limit(20) \
                   .withColumn("category", lit("loser"))

    movers = gainers.union(losers)
```

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `symbol` | STRING | Trading pair |
| `rank` | INT | Rank within category + timeframe |
| `category` | STRING | "gainer" hoặc "loser" |
| `timeframe` | STRING | "1h" / "24h" / "7d" |
| `change_pct` | DOUBLE | Price change % |
| `current_price` | DOUBLE | Current price |
| `volume_24h` | DOUBLE | 24h volume |
| `volume_change_pct` | DOUBLE | Volume change % |
| `snapshot_time` | TIMESTAMP | When calculated |
| `_partition_date` | DATE | Partition date |

**Partitioning:** `_partition_date, timeframe`

### 4.5.9 Bảng Gold: `sector_performance`

**Path:** `s3a://cryptoprice/iceberg/gold/sector_performance`

**Source:** silver.ticker_unified

**Mục đích:** Performance by sector (Large Cap / Mid Cap / Small Cap).

**Sector categorization (theo volume proxy cho market cap):**
- **Large Cap:** volume_total > 1,000,000
- **Mid Cap:** volume_total > 100,000
- **Small Cap:** volume_total ≤ 100,000

**Schema:**

| Column | Spark Type | Mô tả |
|--------|------------|-------|
| `sector` | STRING | Large Cap / Mid Cap / Small Cap |
| `snapshot_time` | TIMESTAMP | When calculated |
| `avg_change_pct` | DOUBLE | Average change % |
| `total_volume` | DOUBLE | Total volume |
| `symbol_count` | INT | Number of symbols |
| `top_symbol` | STRING | Top symbol in sector |
| `top_symbol_change_pct` | DOUBLE | Top symbol's change % |
| `_partition_date` | DATE | Partition date |

### 4.5.10 Bảng Gold: `news_sentiment`

**Path:** `s3a://cryptoprice/iceberg/gold/news_sentiment`

**Source:** bronze.news (Flink) + silver.news (after transform)

**Mục đích:** News sentiment aggregation per symbol.

---

## 4.6 Pipeline Orchestration

### 4.6.1 Bronze Streaming (3 queries song song)

```python
# Ticker query
ticker_query = ticker_df.writeStream
    .format("iceberg")
    .outputMode("append")
    .trigger(processingTime="1 minute")
    .option("checkpointLocation", CHECKPOINT_TICKER)
    .toTable(ICEBERG_TABLE_TICKER)

# Trades query
trades_query = trades_df.writeStream
    .format("iceberg")
    .outputMode("append")
    .trigger(processingTime="1 minute")
    .option("checkpointLocation", CHECKPOINT_TRADES)
    .toTable(ICEBERG_TABLE_TRADES)

# Klines query
klines_query = klines_df.writeStream
    .format("iceberg")
    .outputMode("append")
    .trigger(processingTime="1 minute")
    .option("checkpointLocation", CHECKPOINT_KLINES)
    .toTable(ICEBERG_TABLE_KLINES)

spark.streams.awaitAnyTermination()
```

### 4.6.2 Silver ETL (Hourly)

```python
# Main orchestration
def main():
    spark = create_spark_session()
    create_silver_tables(spark)
    transform_ticker(spark)              # Ticker: bronze → silver
    aggregate_timeframe("1m", "5m", 5)   # 1m → 5m
    aggregate_timeframe("1m", "15m", 15) # 1m → 15m
    aggregate_timeframe("1m", "1h", 60)  # 1m → 1h
    aggregate_timeframe("1h", "4h", 4)   # 1h → 4h
    aggregate_timeframe("1h", "1d", 24)  # 1h → 1d
```

**Unified approach (1m → 5m → 15m → 1h in ONE pass):**
- Cache 5m in-memory
- Aggregate 5m → 15m from cached 5m
- Cache 15m in-memory
- Aggregate 15m → 1h from cached 15m

### 4.6.3 Gold ETL (5-min batch)

```python
# Main orchestration
def main():
    spark = create_spark_session()
    create_gold_tables(spark)
    populate_coin_ticker(spark)            # silver → coin_ticker
    market_overview.calculate()            # silver → market_overview
    market_dominance.calculate()            # silver → market_dominance
    volatility_ranking.calculate()          # silver → volatility_ranking
    movers_ranking.calculate()              # silver → movers_ranking
```

### 4.6.4 Calculate All Gold Metrics (master orchestrator)

```python
# Pipeline steps
# [1/7] Create Gold tables
# [2/7] Calculate market dominance
# [3/7] Calculate volatility rankings
# [4/7] Calculate movers rankings (gainers/losers)
# [5/7] Transform News (Bronze → Silver)
# [6/7] Calculate news sentiment
# [7/7] Summary
```

---

## 4.7 Retry & Error Handling

### 4.7.1 Streaming Query Retry

```python
def _start_query_with_retry(start_query_fn, query_name, max_retries=5, backoff_sec=15):
    attempt = 0
    while True:
        try:
            query = start_query_fn()
            return query
        except Exception as exc:
            attempt += 1
            if attempt >= max_retries:
                raise
            time.sleep(backoff_sec * attempt)
```

**5 retries × exponential backoff (15s, 30s, 45s, 60s, 75s) = ~225s max wait**

### 4.7.2 Batch Job Error Handling

```python
try:
    # ... main logic ...
    logger.info("Pipeline completed successfully")
except Exception as e:
    logger.error(f"Pipeline failed: {e}", exc_info=True)
    raise
finally:
    spark.stop()
```

---

## 4.8 Schema Evolution

### 4.8.1 Cho phép (BACKWARD compatibility)

- ✅ Thêm column mới
- ✅ Đổi tên column (thêm cột mới + deprecate cũ)
- ✅ Thêm partition field

### 4.8.2 Không cho phép

- ❌ Đổi kiểu dữ liệu
- ❌ Xóa column đã commit
- ❌ Đổi partition scheme (cần rewrite)

### 4.8.3 Best-effort Column Addition

```python
def _ensure_column(spark, table_name, column_name, column_type):
    try:
        spark.sql(f"ALTER TABLE {table_name} ADD COLUMNS ({column_name} {column_type})")
    except Exception as exc:
        if "already exists" in str(exc) or "Cannot add duplicate" in str(exc):
            pass
```

---

## 4.9 Lakehouse Performance

### 4.9.1 Storage Format

| Format | Where | Why |
|--------|-------|-----|
| **Parquet** | Data files | Columnar, compressed, fast column reads |
| **Avro** | Iceberg metadata | Schema evolution, compact |
| **LZ4/Snappy** | Compression | Fast decompression, ~70% size reduction |

### 4.9.2 Partition Pruning

| Table | Partition Column | Effect |
|-------|------------------|--------|
| Bronze ticker | `days(event_timestamp)` | Skip non-relevant days |
| Bronze klines | `days(kline_timestamp)` | Skip non-relevant days |
| Silver ticker_unified | `_partition_date` | Skip non-relevant dates |
| Silver kline_multi_timeframe | `_partition_date, interval` | Skip non-relevant dates+intervals |
| Gold momentum_indicators | `_partition_date` | Skip old data |
| Gold indicator_history | `_partition_date, interval, exchange` | Fine-grained filtering |

### 4.9.3 Storage Estimates

| Layer | Records/day | Size/day | Retention | Total |
|-------|-------------|----------|-----------|-------|
| Bronze ticker | 200 symbols × 86400s = ~17M | ~500MB | 90 days | ~45GB |
| Bronze klines | 200 symbols × 1440 candles = ~288K | ~50MB | 90 days | ~4.5GB |
| Bronze trades | ~50M trades | ~5GB | 90 days | ~450GB |
| Silver kline_multi_timeframe | ~30K rows (1h × 200 symbols) | ~3MB | 365 days | ~1.1GB |
| Gold momentum_indicators | 200 symbols × 1 snapshot | ~10KB | 30 days | ~300KB |
| Gold indicator_history | 200 × 1h × 365d = 1.7M | ~100MB | 365 days | ~36GB |

---

## 4.10 Lakehouse Path Structure

```
s3a://cryptoprice/iceberg/
├── bronze/
│   ├── coin_ticker/          # Stream write từ Kafka
│   ├── coin_trades/          # Stream write từ Kafka
│   ├── coin_klines/          # Stream write từ Kafka
│   ├── ticker/                # Alternative path
│   ├── kline/                 # Alternative path
│   └── news/                  # Dagster batch
├── silver/
│   ├── ticker_unified/        # Hourly ETL
│   └── kline_multi_timeframe/ # Hourly ETL
└── gold/
    ├── market_overview/        # 5-min ETL
    ├── coin_ticker/            # 5-min ETL
    ├── momentum_indicators/    # 5-min ETL
    ├── indicator_history/      # 5-min ETL
    ├── market_dominance/       # 5-min ETL
    ├── volatility_ranking/     # 5-min ETL
    ├── movers_ranking/         # 5-min ETL
    ├── sector_performance/     # 5-min ETL
    └── news_sentiment/         # 5-min ETL
```

---

**Tiếp theo: Part 5 — Serving Layer (FastAPI + WebSocket)**

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# PHẦN 5: TẦNG SERVING (FASTAPI + WEBSOCKET)

---

## 5.1 Tổng quan Serving Layer

**Mô tả:** FastAPI là **web framework** phục vụ REST API endpoints và WebSocket streaming cho frontend. Đây là điểm cuối cùng trong data flow — nhận data từ Redis Sentinel (real-time), InfluxDB (analytics), Trino (historical), và serve cho React frontend.

### 5.1.1 Vai trò của Serving Layer

| Trách nhiệm | Mô tả |
|--------------|-------|
| **REST API** | Endpoints cho historical data, klines, ticker, trades, orderbook |
| **WebSocket streaming** | Real-time candle updates mỗi 50ms |
| **Data aggregation** | Tính toán từ Redis + InfluxDB + Trino |
| **Multi-source fallback** | Redis → InfluxDB → Trino → REST API fallback chain |
| **AI integration** | Phục vụ chart snapshots, sessions, knowledge cho AI features |
| **Auth & settings** | PostgreSQL-backed cho user management |

### 5.1.2 Vị trí trong data flow

```
Redis Sentinel (Speed)     InfluxDB (Analytics)     Trino (Lakehouse)
       │                            │                        │
       │  latest ticker             │  90 days candles       │  365 days history
       │  7 days candles            │  indicators            │  gold tables
       │  7 days indicators         │                        │
       └────────────┬───────────────┴────────────┬───────────┘
                    │                            │
                    ▼                            ▼
┌──────────────────────────────────────────────────────────────┐
│                  FASTAPI (Python)                              │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  REST API routes                                       │  │
│  │  /api/klines, /api/ticker, /api/trades, /api/orderbook│  │
│  │  /api/indicators, /api/market, /api/historical, ...   │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  WebSocket routes                                      │  │
│  │  /api/stream/all, /api/stream/{interval},              │  │
│  │  /api/stream/indicators/{interval}                     │  │
│  └────────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Service layer                                         │  │
│  │  candle_service, indicator_service, ticker_service, ... │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ▼
                 ┌───────────────────┐
                 │   React Frontend  │
                 │  (CandlestickChart,│
                 │  Watchlist, AI Helper)
                 └───────────────────┘
```

### 5.1.3 Cấu trúc thư mục backend

```
backend/
├── app.py                          # FastAPI app entry
├── api/                            # Thin route handlers
│   ├── klines.py                   # /api/klines
│   ├── ticker.py                   # /api/ticker
│   ├── orderbook.py                # /api/orderbook
│   ├── trades.py                   # /api/trades
│   ├── websocket.py                # /api/stream/*
│   ├── indicators.py               # /api/indicators
│   ├── market.py                   # /api/market/*
│   ├── market_overview.py          # /api/market/overview
│   ├── historical.py               # /api/klines/historical
│   ├── screener.py                 # /api/screener
│   ├── news.py                     # /api/news
│   ├── auth.py                     # /api/auth
│   ├── settings.py                 # /api/settings
│   ├── admin.py                    # /api/admin
│   ├── health.py                   # /api/health
│   └── ai/                         # AI Ask Mode
│       ├── chat.py
│       ├── sessions.py
│       ├── knowledge.py
│       ├── chart_context.py
│       ├── chart_actions.py
│       └── health.py
├── services/                       # Business logic
│   ├── candle_service.py
│   ├── indicator_service.py
│   ├── market_data_service.py
│   ├── orderbook_service.py
│   └── ai/                         # AI services
├── core/                           # Config, constants, DB clients
│   ├── constants.py                # INTERVAL_SECONDS, MAX_* constants
│   ├── database.py                 # Redis, Trino, InfluxDB clients
│   ├── redis_sentinel.py           # Sentinel client
│   ├── postgres.py                 # PostgreSQL
│   ├── security.py                 # Auth
│   └── config.py
├── models/                         # Pydantic schemas
│   └── common.py                   # DataFreshness, error models
└── migrations/                     # SQL migrations
```

### 5.1.4 Nguyên tắc thiết kế

| Nguyên tắc | Giải thích |
|------------|-----------|
| **Thin route handlers** | API files chỉ làm routing + validation |
| **Business logic in services** | Logic nặng đặt trong `services/` |
| **Pydantic models** | Type-safe request/response |
| **Async/await** | Toàn bộ FastAPI handlers là async |
| **Multi-source fallback** | Mỗi endpoint có fallback chain rõ ràng |
| **Freshness metadata** | Mỗi response có metadata về data source + freshness |

---

## 5.2 Configuration & Constants

### 5.2.1 INTERVAL_SECONDS (constants.py)

```python
INTERVAL_SECONDS = {
    "1s":  1,        # 1 second
    "1m":  60,       # 1 minute
    "5m":  300,      # 5 minutes
    "15m": 900,      # 15 minutes
    "1h":  3600,     # 1 hour
    "4h":  14400,    # 4 hours
    "1d":  86400,    # 1 day
    "1w":  604800,   # 1 week
}
```

### 5.2.2 Retention & Cache Constants

| Constant | Value | Purpose |
|----------|-------|---------|
| `INFLUX_1M_RETENTION_DAYS` | 90 | InfluxDB 1m retention |
| `MAX_RAW_CANDLES` | 1500 | Max candles per query |
| `LIVE_MAX_BASE_ROWS` | 5000 | Max live rows |
| `MAX_BACKFILL_PAGES` | 20 | Max backfill pages |
| `GOLD_FRESHNESS_MINUTES` | 30 | Gold table max age |

### 5.2.3 ALL_INTERVALS (websocket.py)

```python
ALL_INTERVALS = ["1s", "1m", "5m", "15m", "1h", "4h", "1d", "1w"]
```

### 5.2.4 Database Connections (database.py)

| Database | Client | Purpose |
|----------|--------|---------|
| Redis Sentinel | `redis.asyncio` | Hot cache, real-time |
| InfluxDB | `influxdb_client` | Time-series analytics |
| Trino | `trino-python-client` | Iceberg SQL queries |
| PostgreSQL | `asyncpg` | Auth, settings, AI persistence |

---

## 5.3 WebSocket Streaming Layer ⭐

### 5.3.1 Tổng quan WebSocket Routes

| Route | Path | Mục đích | Update Interval |
|-------|------|----------|-----------------|
| `/api/stream/all` | WS | ALL 8 timeframes cùng lúc | 50ms |
| `/api/stream/{interval}` | WS | Single timeframe | 50ms |
| `/api/stream/indicators/{interval}` | WS | Real-time indicator snapshot | 50ms |

**Critical optimization (v0.23.1):** Loop interval giảm từ 0.3s → 0.05s (6× faster updates).

### 5.3.2 Route Registration Order (QUAN TRỌNG!)

```python
# MUST register /stream/all BEFORE /stream/{interval}
# FastAPI matches WebSocket routes in declaration order

@router.websocket("/stream/all")
async def stream_all_first(websocket: WebSocket, symbol: str = "", exchange: str = "binance"):
    """Real-time candle streaming for all timeframes."""
    await _stream_all_impl(websocket, symbol, exchange)

@router.websocket("/stream/{interval}")
async def stream_interval(websocket: WebSocket, interval: str):
    """Single timeframe streaming."""
    # ...
```

**Lý do:** Nếu `/stream/{interval}` đăng ký trước, nó sẽ match `all` thành `interval="all"` → invalid interval.

### 5.3.3 WebSocket `/stream/all` — Implementation Chi Tiết

**Mục đích:** Stream candles cho 8 timeframes đồng thời qua 1 connection.

**Request format:**
```
ws://host/api/stream/all?symbol=BTCUSDT&exchange=binance
```

**Response format:**
```json
{
  "1s":  {"openTime": 1672531190000, "open": 16500, "high": 16505, "low": 16498, "close": 16501, "volume": 120.5},
  "1m":  {"openTime": 1672531140000, "open": 16480, "high": 16520, "low": 16470, "close": 16500, "volume": 1200.0},
  "5m":  {"openTime": 1672530900000, "open": 16450, "high": 16530, "low": 16430, "close": 16500, "volume": 6000.0},
  "15m": {"openTime": 1672530000000, "open": 16400, "high": 16550, "low": 16380, "close": 16500, "volume": 18000.0},
  "1h":  {"openTime": 1672527600000, "open": 16350, "high": 16580, "low": 16320, "close": 16500, "volume": 72000.0},
  "4h":  {"openTime": 1672513200000, "open": 16200, "high": 16600, "low": 16150, "close": 16500, "volume": 288000.0},
  "1d":  {"openTime": 1672444800000, "open": 16000, "high": 16650, "low": 15950, "close": 16500, "volume": 1728000.0},
  "1w":  {"openTime": 1672012800000, "open": 15500, "high": 16700, "low": 15450, "close": 16500, "volume": 12096000.0}
}
```

### 5.3.4 Redis Pipeline Optimization (v0.23.1) ⭐

**Trước v0.23.1:**
- 6 sequential Redis calls per loop × 10 intervals = 60+ calls
- Latency: ~300ms per update

**Sau v0.23.1:**
- 1 Redis pipeline với 6 commands → parse → build candles
- Latency: ~50ms per update

**Code:**
```python
pipe = r.pipeline()
pipe.hgetall(f"ticker:latest:{exchange}:{symbol}")               # 1
pipe.zrevrange(candle_1s_key, 0, 0)                                # 2
pipe.zrevrange(candle_1m_key, 0, 0)                                # 3
pipe.zrevrange(candle_1m_key, 0, 0, withscores=True)                # 4
pipe.zrevrange(trade_key, 0, 0)                                    # 5
pipe.hgetall(candle_latest_key)                                    # 6
pipeline_results = await pipe.execute()
```

**6 Redis commands trong 1 round-trip = 1 network latency thay vì 6.**

### 5.3.5 Real-time Candle Building Logic

**Hàm `_build_candle_from_data`:**

Cho mỗi interval, build candle từ data đã prefetch:

```python
def _build_candle_from_data(interval, candle_1s, candle_1m_window, candle_1m_data,
                              live_price, live_ts, target_ms, candle_latest):
    # 1. Nếu interval = "1s": dùng raw 1s candle
    if interval == "1s" and candle_1s:
        return {
            "openTime": candle_1s["openTime"],
            "open": candle_1s["open"],
            "high": candle_1s["high"],
            "low": candle_1s["low"],
            "close": candle_1s["close"],
            "volume": candle_1s["volume"],
        }

    # 2. Nếu interval = "1m": aggregate từ 1s candles
    if interval == "1m" and candle_1m_data:
        return {
            "openTime": candle_1m_window,
            "open": candle_1m_data[0]["o"],
            "high": max(c["h"] for c in candle_1m_data),
            "low": min(c["l"] for c in candle_1m_data),
            "close": candle_1m_data[-1]["c"],
            "volume": round(sum(c["v"] for c in candle_1m_data), 8),
        }

    # 3. Nếu interval = 5m/15m/1h/4h/1d/1w: aggregate từ 1m candles
    if candle_1m_data:
        flink_window = (candle_1m_window // target_ms) * target_ms
        return {
            "openTime": flink_window,
            "open": candle_1m_data[0]["o"],
            "high": max(c["h"] for c in candle_1m_data),
            "low": min(c["l"] for c in candle_1m_data),
            "close": candle_1m_data[-1]["c"],
            "volume": round(sum(c["v"] for c in candle_1m_data), 8),
        }

    # 4. Fold in live ticker price (cho responsiveness khi 1m/5m stream lag)
    if live_price and live_ts:
        live_window = (live_ts // target_ms) * target_ms
        if flink_candle and live_window == flink_window:
            # Cùng window → update close/high/low với live price
            flink_candle["close"] = live_price
            flink_candle["high"] = max(flink_candle["high"], live_price)
            flink_candle["low"] = min(flink_candle["low"], live_price)
            return flink_candle
        if live_window > flink_window:
            # New window → tạo candle mới
            return {
                "openTime": live_window,
                "open": live_price, "high": live_price,
                "low": live_price, "close": live_price,
                "volume": 0,
            }

    return flink_candle
```

**Tại sao fold in live ticker:**
- 1m/5m/15m candles được aggregate từ 1s data
- Nhưng 1s data có thể lag (Flink processing delay)
- Live ticker price LUÔN fresh → fold in để candle update ngay khi có trade

### 5.3.6 Trade Qty Accumulation

**Mục đích:** Real-time volume update cho current candle.

```python
# Parse trade qty
trade_qty: float = 0.0
if raw_trade:
    t = json.loads(raw_trade[0])
    trade_qty = float(t.get("q", 0))

# Accumulate vào tất cả intervals
for iv in ALL_INTERVALS:
    candle = ...
    if trade_qty > 0 and candle:
        candle["volume"] = round(candle.get("volume", 0) + trade_qty, 8)
```

**Logic:** Mỗi trade mới cộng qty vào volume của candle hiện tại (cho cả 1s, 1m, 5m, ...). Trade qty được cộng vào mọi interval vì mỗi interval đang accumulate trade vào in-progress candle.

### 5.3.7 Change Detection

**Chỉ gửi khi có thay đổi:**
```python
last_sent: dict[str, dict | None] = {iv: None for iv in ALL_INTERVALS}
any_changed = False

for iv in ALL_INTERVALS:
    candle = _build_candle_from_data(...)
    if candle and candle != last_sent[iv]:
        result[iv] = candle
        last_sent[iv] = candle
        any_changed = True
    else:
        result[iv] = last_sent[iv]

if any_changed:
    await websocket.send_json(result)
```

**Lợi ích:**
- Giảm bandwidth: chỉ gửi khi candle thực sự thay đổi
- Frontend chỉ re-render khi cần
- Tần suất update tự nhiên theo trade flow

### 5.3.8 Loop Interval (v0.23.1 critical fix)

```python
while True:
    # ... fetch & build candles ...
    if any_changed:
        await websocket.send_json(result)
    
    # CRITICAL: Reduced from 0.3s to 0.05s for real-time responsiveness
    # This is the primary latency source — tighter loop = faster updates
    await asyncio.sleep(0.05)
```

**Trade-off:**
- 0.05s loop = 20Hz polling = 20 Redis pipelines/giây
- Trade-off giữa latency vs Redis load
- 50ms là sweet spot: đủ nhanh cho real-time, không quá tải Redis

### 5.3.9 Single Interval WebSocket (`/stream/{interval}`)

**Use case:** Component chỉ cần 1 interval (e.g., 1m chart).

**Implementation:**
```python
@router.websocket("/stream/{interval}")
async def stream_interval(websocket: WebSocket, interval: str):
    interval = interval.strip().lower()
    if interval not in ALL_INTERVALS:
        await websocket.accept()
        await websocket.send_json({"error": f"Unsupported interval: {interval}"})
        await websocket.close()
        return

    await websocket.accept()
    r = await get_redis()
    symbol = websocket.query_params.get("symbol", "BTCUSDT").upper()
    exchange = websocket.query_params.get("exchange", "binance").strip().lower() or "binance"
    target_ms = INTERVAL_SECONDS[interval] * 1000
    last_sent = None

    try:
        while True:
            ticker = await r.hgetall(f"ticker:latest:{exchange}:{symbol}")
            live_price = float(ticker["price"]) if ticker.get("price") else None
            live_ts = int(ticker["event_time"]) if ticker.get("event_time") else None

            candle = await _build_candle(
                r, symbol, interval, target_ms, exchange, live_price, live_ts,
            )
            if candle and candle != last_sent:
                await websocket.send_json(candle)
                last_sent = candle

            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
```

**Optimizations:**
- Validate interval early
- Track `last_sent` để chỉ gửi khi thay đổi
- Sleep 50ms giữa các loop

### 5.3.10 Indicator Stream WebSocket (`/stream/indicators/{interval}`)

**Use case:** Real-time indicator updates cho chart.

**Implementation:**
```python
@router.websocket("/stream/indicators/{interval}")
async def stream_indicators(websocket: WebSocket, interval: str):
    interval = interval.strip().lower()
    if interval not in ALL_INTERVALS:
        await websocket.accept()
        await websocket.send_json({"error": f"Unsupported interval: {interval}"})
        await websocket.close()
        return

    await websocket.accept()
    r = await get_redis()
    symbol = websocket.query_params.get("symbol", "BTCUSDT").upper()
    exchange = websocket.query_params.get("exchange", "binance").strip().lower() or "binance"
    last_sent = None

    try:
        while True:
            payload = await _build_indicator_snapshot(r, symbol, exchange, interval)
            if payload and payload != last_sent:
                await websocket.send_json(payload)
                last_sent = payload

            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass
```

**`_build_indicator_snapshot` đọc từ:**
- `indicator:latest:{exchange}:{symbol}:{interval}` (Hash)
- Trả về 20 fields: sma20, ema12, rsi14, macd, bb_middle, atr14, ...

### 5.3.11 WebSocket Error Handling

```python
try:
    while True:
        # ... process ...
except WebSocketDisconnect:
    pass  # Client disconnect là bình thường
except Exception as e:
    log.warning("Stream %s error for %s: %s", interval, symbol, e)
    # KHÔNG re-raise — connection vẫn alive, chỉ log warning
```

**Strategy:**
- WebSocketDisconnect là bình thường (client close tab) → pass
- Generic exceptions → log warning, KHÔNG crash (cho phép tự phục hồi loop tiếp theo)

---

## 5.4 REST API Endpoints

### 5.4.1 Endpoint Tổng hợp

| Endpoint | Method | Source | Mục đích |
|----------|--------|--------|----------|
| `/api/klines` | GET | Redis→InfluxDB→Trino | Candles 1s/1m/5m/15m/1h/4h/1d/1w |
| `/api/klines/historical` | GET | Trino | Long-range historical (months/years) |
| `/api/ticker` | GET | Redis Hash | All tickers hoặc single |
| `/api/ticker/{symbol}` | GET | Redis Hash | Single ticker (single hoặc multi-exchange) |
| `/api/trades/{symbol}` | GET | Redis ZSET | Recent trades (true trade tape hoặc ticker-derived) |
| `/api/trades/{symbol}/summary` | GET | Redis ZSET | Trade summary for AI |
| `/api/orderbook/{symbol}` | GET | Redis Hash→Binance REST | Order book với spread |
| `/api/orderbook/{symbol}/summary` | GET | Redis Hash→Binance REST | Order book summary |
| `/api/indicators/{symbol}` | GET | Redis Hash | Latest indicators |
| `/api/indicators/{symbol}/summary` | GET | Redis Hash | Compact summary for AI |
| `/api/indicators/supported` | GET | Static | List of supported indicators |
| `/api/market/overview` | GET | Trino→Redis | Market metrics (gainers, losers, dominance) |
| `/api/market/heatmap` | GET | Trino | Heatmap data |
| `/api/market/rankings/{category}` | GET | Trino | Rankings by category |
| `/api/screener/*` | GET | Trino | Custom screener queries |
| `/api/news/*` | GET | Trino | News with sentiment |
| `/api/auth/*` | POST/GET | PostgreSQL | Auth (login, register, sessions) |
| `/api/settings/*` | GET/POST | PostgreSQL | User settings |
| `/api/admin/*` | GET/POST | PostgreSQL | Admin operations |
| `/api/ai/*` | POST/GET | PostgreSQL + LLM | AI Ask Mode |

### 5.4.2 `/api/klines` — Candles (chi tiết)

**Query params:**
- `symbol` (required) — Trading pair
- `interval` (default "1m") — 1s/1m/5m/15m/1h/4h/1d/1w
- `limit` (1-1500, default 200) — Number of candles
- `endTime` (optional) — End timestamp in ms (cho scroll loading)
- `exchange` (default "binance") — Exchange name

**Response:**
```json
[
  {
    "openTime": 1672531140000,
    "open": 16480.00,
    "high": 16520.00,
    "low": 16470.00,
    "close": 16500.00,
    "volume": 1200.5
  },
  ...
]
```

**Multi-source fallback chain:**

| Step | Source | Used When |
|------|--------|-----------|
| 1 | Redis cache (`klines_cache:{ex}:{sym}:{interval}:{limit}`) | Cache hit (TTL 200ms-1.5s) |
| 2 | KeyDB 1s/1m sorted set | Last 7 days |
| 3 | InfluxDB `candles` measurement | 1-90 days |
| 4 | Trino `silver.kline_multi_timeframe` | 90+ days |
| 5 | Trino hourly fallback | Very old data for 1h+ intervals |

**Implementation:**
```python
@router.get("/klines")
async def get_klines(symbol, interval="1m", limit=200, endTime=None, exchange="binance"):
    symbol = validate_symbol(symbol)
    interval, target_sec = validate_interval(interval)
    r = await get_redis()

    # Step 1: Check Redis cache
    cache_key = f"klines_cache:{exchange}:{symbol}:{interval}:{limit}"
    if not endTime:
        cached = await r.get(cache_key)
        if cached:
            return json.loads(cached)

    candles = []
    now_ms = int(time.time() * 1000)
    influx_cutoff_ms = now_ms - (INFLUX_1M_RETENTION_DAYS * 24 * 3600 * 1000)

    # Step 2: KeyDB cho 1s, hoặc multi-source cho 1m+
    if interval == "1s":
        candles = await _fetch_1s_candles(r, symbol, limit, endTime, now_ms, exchange)
    else:
        candles = await _fetch_1m_plus_candles(...)

    # Step 3: Aggregate cho intervals > 1m
    if interval not in ("1s", "1m") and candles:
        candles = aggregate(candles, target_sec * 1000)

    # Step 4: Enrich với live ticker
    if not endTime and interval not in ("1s", "1m"):
        candles = await _enrich_with_live_ticker(r, symbol, target_sec, candles, exchange)

    result = candles[-limit:]

    # Step 5: Cache result
    if not endTime:
        ttl_ms = 200 if interval == "1s" else 1500
        r_master = await get_redis_master()
        pipe = r_master.pipeline()
        pipe.set(cache_key, json.dumps(result))
        pipe.pexpire(cache_key, ttl_ms)
        await pipe.execute()

    return result
```

### 5.4.3 `/api/klines/historical` — Long-range Historical

**Use case:** Chart cần load nhiều tháng/năm data (backtest, deep analysis).

**Source:** Trino query Iceberg `silver.kline_multi_timeframe`

**Optimizations:**
- Pagination support
- Aggregate từ 1h/1d (không query 1m)
- Time-based filtering qua `_partition_date`

### 5.4.4 `/api/ticker` — All Tickers (chi tiết)

**Single exchange mode:**
```python
async for key in r.scan_iter(match=f"ticker:latest:{exchange_lower}:*", count=200):
    symbol = key.split(":", 3)[-1]
    data = await r.hgetall(key)
    # ... extract fields ...
```

**Multi-exchange aggregation mode:**
```python
# Collect từ tất cả exchanges
async for key in r.scan_iter(match="ticker:latest:*:*", count=200):
    parts = key.split(":", 3)
    exchange_name = parts[2]
    symbol = parts[3]
    # ...

# Aggregate per symbol
for symbol in symbols_seen:
    prices = [...]  # từ tất cả exchanges
    mid_price = sum(prices) / len(prices)
    total_volume = sum(volumes)
```

**Activity score:**
```python
def _activity_score(volume: float, change_24h: float, event_time: int) -> float:
    """Rank active markets with volume first, then movement and freshness."""
    movement_multiplier = 1.0 + min(abs(change_24h), 100.0) / 100.0
    freshness_bonus = 1.0 if event_time > 0 else 0.0
    return (max(volume, 0.0) * movement_multiplier) + freshness_bonus
```

**Sort by activity_score DESC → top movers trước.**

### 5.4.5 `/api/ticker/{symbol}` — Single Ticker (chi tiết)

**Multi-exchange aggregation:**
- Nếu không có `exchange` param → return mid-price từ Binance + OKX
- Primary data (bid, ask, change24h) từ Binance (fallback OKX)
- `sources` dict chứa giá từ từng exchange

**Response example:**
```json
{
  "symbol": "BTCUSDT",
  "exchange": "aggregated",
  "price": 16500.50,  // mid of Binance + OKX
  "change24h": -0.60,
  "bid": 16500.00,
  "ask": 16501.00,
  "volume": 2400.50,
  "event_time": 1672531199000,
  "activity_score": 39632.5,
  "sources": {
    "binance": 16500.00,
    "okx": 16501.00
  }
}
```

### 5.4.6 `/api/trades/{symbol}` — Recent Trades (chi tiết)

**Multi-source priority:**

| Priority | Source | Format | `is_true_trade_tape` |
|----------|--------|--------|----------------------|
| 1 | `trade:latest:{ex}:{sym}` (Redis ZSET) | `{"p","q","t","m","T"}` | True |
| 2 | `ticker:history:{ex}:{sym}` (Redis ZSET) | `"{price}:{volume}"` | False (ticker-derived) |

**Code:**
```python
# Priority 1: real trade cache
for ex in (exchange, "binance", "okx"):
    raw = await r.zrevrange(f"trade:latest:{ex}:{symbol_u}", 0, limit - 1, withscores=True)
    if raw:
        source = "redis"
        is_true_trade_tape = True
        break

# Priority 2: ticker-derived
if not raw:
    for ex in (exchange, "binance", "okx"):
        raw = await r.zrevrange(f"ticker:history:{ex}:{symbol_u}", 0, limit - 1, withscores=True)
        if raw:
            source = "redis"
            break
```

**Side inference (ticker-derived):**
```python
prev_price = None
for member, score in raw:
    parts = str(member).split(":")
    price = float(parts[0])
    side = "buy" if prev_price is None or price >= prev_price else "sell"
    prev_price = price
```

**Warnings khi ticker-derived:**
```python
warnings = [
    "These are ticker-derived price movements, not true exchange trades.",
    "Side is inferred from price direction and may not reflect actual trade initiator.",
]
```

**Metadata với DataFreshness:**
```json
{
  "metadata": {
    "data_type": "exchange_trade",
    "is_true_trade_tape": true,
    "source": "redis",
    "exchange": "binance",
    "tick_count": 50,
    "freshness": {
      "source": "redis",
      "exchange": "binance",
      "event_time": 1672531199000,
      "freshness_seconds": 0.234,
      "is_stale": false,
      "is_fallback": false,
      "warnings": []
    }
  }
}
```

### 5.4.7 `/api/trades/{symbol}/summary` — Trade Summary

**Compact summary for AI context:**
```json
{
  "symbol": "BTCUSDT",
  "latest_price": 16500.00,
  "tick_count": 50,
  "volume_sum": 120.5,
  "inferred_direction": "up",
  "data_type": "ticker_derived",
  "is_true_trade_tape": false,
  "exchange": "binance",
  "warning": "Direction inferred from ticker price movement, not true trade tape."
}
```

**Direction inference:**
```python
if latest_price > oldest_price: direction = "up"
elif latest_price < oldest_price: direction = "down"
else: direction = "flat"
```

### 5.4.8 `/api/orderbook/{symbol}` — Order Book (chi tiết)

**Multi-source fallback chain:**

| Priority | Source | When Used |
|----------|--------|-----------|
| 1 | `orderbook:{ex}:{sym}` (Redis Hash) | Fresh from Flink |
| 2 | `orderbook:{sym}` (legacy key) | Old format |
| 3 | Ticker-derived synthetic book | No depth, just bid/ask |
| 4 | Binance REST API | Cache miss + no ticker |

**Code:**
```python
# Priority 1: exchange-specific
for ex in (exchange, "binance", "okx"):
    data = await r.hgetall(f"orderbook:{ex}:{symbol_u}")
    if data:
        source = "redis"
        found_exchange = ex
        break

# Priority 2: legacy format
if not data:
    data = await r.hgetall(f"orderbook:{symbol_u}")
    if data:
        source = "redis"
        found_exchange = "unknown"

# Priority 3: ticker-derived synthetic book
if not data:
    ticker = await r.hgetall(f"ticker:latest:{ex}:{symbol_u}")
    if ticker and bid > 0 and ask > 0:
        return synthetic_book(ticker)

# Priority 4: Binance REST API
if not data:
    fallback = await _fetch_binance_orderbook(symbol_u)
    # ... warm cache with TTL 30s
```

**Synthetic orderbook (ticker-derived):**
```json
{
  "bids": [[16500.00, 0.0]],
  "asks": [[16501.00, 0.0]],
  "spread": 1.00,
  "best_bid": 16500.00,
  "best_ask": 16501.00,
  "metadata": {
    "source": "ticker_derived",
    "is_synthetic": true,
    "freshness": {
      "is_fallback": true,
      "warnings": ["Order book derived from ticker bid/ask only — no depth levels available."]
    }
  }
}
```

**Binance REST fallback (`_fetch_binance_orderbook`):**
```python
async def _fetch_binance_orderbook(symbol: str, limit: int = 50) -> dict | None:
    url = "https://api.binance.com/api/v3/depth"
    resp = await _BINANCE_CLIENT.get(url, params={"symbol": symbol, "limit": limit})
    payload = resp.json()
    bids = [[float(p), float(q)] for p, q in payload.get("bids", [])]
    asks = [[float(p), float(q)] for p, q in payload.get("asks", [])]
    # ... warm cache với TTL 30s
```

**Cache warming:**
```python
r_master = await get_redis_master()
await r_master.hset(f"orderbook:binance:{symbol_u}", mapping={...})
await r_master.expire(f"orderbook:binance:{symbol_u}", 30)
```

### 5.4.9 `/api/orderbook/{symbol}/summary` — Order Book Summary

**For AI context:**
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "best_bid": 16500.00,
  "best_ask": 16501.00,
  "spread": 1.00,
  "bid_depth": 1234.56,    // Total bid volume
  "ask_depth": 1198.45,    // Total ask volume
  "imbalance": 0.0295,     // (bid - ask) / total
  "top_bid_levels": [[16500, 10.5], [16499, 5.25], ...],
  "top_ask_levels": [[16501, 8.0], [16502, 3.5], ...],
  "metadata": {...}
}
```

**Imbalance calculation:**
```python
bid_depth = sum(level[1] for level in bids)  # Sum of all bid quantities
ask_depth = sum(level[1] for level in asks)
total_depth = bid_depth + ask_depth
imbalance = (bid_depth - ask_depth) / total_depth if total_depth > 0 else 0.0
```

**Interpretation:**
- imbalance > 0: more bid pressure (bullish)
- imbalance < 0: more ask pressure (bearish)
- |imbalance| > 0.2: significant imbalance

### 5.4.10 `/api/indicators/{symbol}` — Latest Indicators

**Query params:**
- `exchange` (default "binance")
- `interval` (default "1m") — 1m, 5m, 15m, 1h, ...

**Source:** Redis Hash `indicator:latest:{exchange}:{symbol}:{interval}`

**Response example:**
```json
{
  "symbol": "BTCUSDT",
  "exchange": "binance",
  "interval": "1m",
  "timestamp": 1672531190000,
  "close": 16501.00,
  "high": 16505.00,
  "low": 16498.00,
  "volume": 120.50,
  "sma20": 16480.50,
  "sma50": 16460.25,
  "ema12": 16490.10,
  "ema26": 16475.30,
  "rsi14": 62.5,
  "bb_middle": 16480.50,
  "bb_upper": 16520.30,
  "bb_lower": 16440.70,
  "bb_width": 79.60,
  "macd": 14.80,
  "macd_signal": 10.20,
  "macd_histogram": 4.60,
  "atr14": 35.20,
  "volume_sma20": 120.50,
  "metadata": {
    "source": "redis",
    "freshness": {
      "freshness_seconds": 1.5,
      "is_stale": false
    }
  }
}
```

### 5.4.11 `/api/indicators/supported` — List Supported

**Static list:**
```python
INDICATORS = [
    {"name": "sma20", "display_name": "SMA 20", "category": "trend", "params": {"period": 20}},
    {"name": "sma50", "display_name": "SMA 50", "category": "trend", "params": {"period": 50}},
    {"name": "ema12", "display_name": "EMA 12", "category": "trend", "params": {"period": 12}},
    {"name": "ema26", "display_name": "EMA 26", "category": "trend", "params": {"period": 26}},
    {"name": "rsi14", "display_name": "RSI 14", "category": "momentum", "params": {"period": 14}},
    {"name": "macd", "display_name": "MACD", "category": "momentum", "params": {"fast": 12, "slow": 26, "signal": 9}},
    {"name": "bb_upper", "display_name": "Bollinger Upper", "category": "volatility", "params": {"period": 20, "std": 2}},
    {"name": "bb_lower", "display_name": "Bollinger Lower", "category": "volatility", "params": {"period": 20, "std": 2}},
    {"name": "atr14", "display_name": "ATR 14", "category": "volatility", "params": {"period": 14}},
    {"name": "volume_sma20", "display_name": "Volume SMA 20", "category": "volume", "params": {"period": 20}},
]
```

### 5.4.12 `/api/market/overview` — Market Overview (chi tiết)

**Multi-source fallback:**

| Priority | Source | When |
|----------|--------|------|
| 1 | Trino Gold tables | If gold data available + fresh (< 30 min) |
| 2 | Redis ticker scan | Gold unavailable/stale → derive from Redis |

**Trino queries:**

```python
# Market summary
query = f"""
SELECT
    COALESCE(MAX(total_volume_24h), 0) as total_volume_24h,
    COALESCE(MAX(active_symbols), 0) as active_symbols,
    COALESCE(MAX(btc_dominance_pct), 0) as btc_dominance_pct,
    COALESCE(MAX(eth_dominance_pct), 0) as eth_dominance_pct
FROM {DB}.gold_market_dominance
WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
"""

# Top gainers
query = f"""
SELECT symbol, exchange, price, change_24h, volume_24h, rank_gainers
FROM {DB}.gold_movers_ranking
WHERE computed_at >= current_timestamp - INTERVAL '{GOLD_FRESHNESS_MINUTES}' MINUTE
  AND change_24h > 0
ORDER BY rank_gainers ASC
LIMIT {limit}
"""
```

**Redis fallback (`_derive_market_from_redis`):**
- SCAN tất cả `ticker:latest:*:*` keys
- HGETALL mỗi key
- Sort by change_pct → top gainers/losers
- Calculate BTC/ETH dominance

**Trino gold freshness check:**
```python
trino_data_available = ENABLE_GOLD_PATH and (
    market_summary.get("active_symbols", 0) > 0
    or len(top_gainers) > 0
    or len(most_volatile) > 0
    or len(highest_volume) > 0
)
```

**Metadata:**
```json
{
  "metadata": {
    "source": "trino_gold",
    "data_sources": ["trino_gold"],
    "is_placeholder": false,
    "computed_at": "2026-06-11T12:00:00",
    "gold_tables_healthy": true,
    "warning": null
  }
}
```

**Sections returned:**

| Section | Source | Content |
|---------|--------|---------|
| `market_summary` | gold.market_dominance | Total volume, BTC/ETH dominance, active symbols, fear_greed_index |
| `top_gainers` | gold.movers_ranking | Top 10 gainers (24h by default) |
| `top_losers` | gold.movers_ranking | Top 10 losers |
| `most_volatile` | gold.volatility_ranking | Top 10 most volatile |
| `highest_volume` | gold.movers_ranking | Top 10 highest volume |
| `trending_news` | gold.news_sentiment | Top 10 symbols with most news |
| `sector_performance` | gold.sector_performance | Performance by sector |
| `heatmap_data` | JOIN gold.movers_ranking + gold.volatility_ranking | For treemap visualization |
| `indicators_summary` | gold.momentum_indicators | RSI avg, overbought/oversold count, MACD bullish/bearish |

### 5.4.13 `/api/market/heatmap` — Heatmap Data

**Response:**
```json
{
  "timestamp": "2026-06-11T12:00:00",
  "data": [
    {
      "symbol": "BTCUSDT",
      "change_pct": -0.60,
      "price": 16500.00,
      "volume_24h": 1200000.50,
      "market_cap": 19800000000.00,
      "volatility": 0.0234
    },
    ...
  ]
}
```

**Trino query:**
```sql
SELECT
    m.symbol,
    m.change_24h,
    m.price,
    m.volume_24h,
    (m.price * m.volume_24h * 10) as market_cap,
    v.price_range_pct
FROM iceberg.crypto_lakehouse.gold_movers_ranking m
LEFT JOIN iceberg.crypto_lakehouse.gold_volatility_ranking v
    ON m.symbol = v.symbol AND m.exchange = v.exchange
WHERE m.computed_at >= current_timestamp - INTERVAL '30' MINUTE
ORDER BY market_cap DESC
LIMIT 50
```

### 5.4.14 `/api/market/rankings/{category}` — Rankings

**Categories:**
- `gainers` — top gainers
- `losers` — top losers
- `volume` — highest volume
- `volatile` — most volatile

**Query params:**
- `timeframe` (1h/24h/7d)
- `limit` (5-100, default 20)

### 5.4.15 `/api/screener/*` — Custom Screener

Cho phép user query custom conditions trên gold tables.

**Example:**
```
GET /api/screener?condition=rsi_14<30&interval=1h&sort=volume_24h&limit=20
```

**Implementation:** Trino query với dynamic WHERE clause.

### 5.4.16 `/api/news/*` — News với Sentiment

**Source:** bronze.news + silver.news + gold.news_sentiment

**News data flow:**
1. Bronze: Raw news từ RSS feeds, news APIs
2. Silver: Sentiment scored (positive/negative/neutral)
3. Gold: Aggregated sentiment per symbol per day

### 5.4.17 `/api/auth/*` — Authentication

**Source:** PostgreSQL (auth database)

**Endpoints:**
- `POST /api/auth/register` — Create user
- `POST /api/auth/login` — Login → JWT token
- `POST /api/auth/logout` — Invalidate session
- `GET /api/auth/me` — Current user info
- `POST /api/auth/refresh` — Refresh JWT

**Storage:**
- `auth.users` table — user info (email, hashed password)
- `auth.sessions` table — active sessions (token, expires_at)
- `auth.user_settings` table — per-user preferences

### 5.4.18 `/api/settings/*` — User Settings

**Stored in PostgreSQL:**
- Theme (dark/light)
- Default symbol
- Default interval
- Watchlist symbols
- Notification preferences
- AI provider preferences

### 5.4.19 `/api/admin/*` — Admin Operations

**Restricted to admin role:**
- `GET /api/admin/users` — List all users
- `POST /api/admin/users/{id}/disable` — Disable user
- `GET /api/admin/stats` — System statistics
- `GET /api/admin/logs` — Recent logs
- `POST /api/admin/cache/clear` — Clear Redis cache

### 5.4.20 `/api/ai/*` — AI Ask Mode (Phase 1)

**Endpoints:**
- `POST /api/ai/chat` — Send message, get AI response
- `GET /api/ai/sessions` — List chat sessions
- `POST /api/ai/sessions` — Create new session
- `GET /api/ai/sessions/{id}/messages` — Get messages
- `POST /api/ai/knowledge` — Add knowledge chunk
- `GET /api/ai/health` — AI service health

**Storage:** PostgreSQL (chat_sessions, messages, chart_snapshots, knowledge_chunks, embeddings, retrieval_logs)

**Architecture:**
1. User sends question với chart context
2. Backend retrieves chart snapshot + indicators
3. Build prompt với RAG context
4. Call LLM (mock provider hoặc real LiteLLM)
5. Validate output, return to user

---

## 5.5 Service Layer (Business Logic)

### 5.5.1 `candle_service.py` — Candle Business Logic

**Validate:**
```python
def validate_symbol(symbol: str) -> str:
    return symbol.upper().strip()

def validate_interval(interval: str) -> tuple[str, int]:
    if interval not in INTERVAL_SECONDS:
        raise HTTPException(400, f"Unsupported interval: {interval}")
    return interval, INTERVAL_SECONDS[interval]
```

**Aggregate:**
```python
def aggregate(candles: list[dict], target_ms: int) -> list[dict]:
    """Aggregate 1m/1s candles → higher timeframe."""
    # Group by window
    # OHLCV: open=first, high=max, low=min, close=last, volume=sum
```

**Merge unique:**
```python
def merge_unique(existing: list[dict], new: list[dict]) -> list[dict]:
    """Merge and dedupe by openTime."""
    seen = {c["openTime"]: c for c in existing}
    for c in new:
        if c["openTime"] not in seen:
            seen[c["openTime"]] = c
    return sorted(seen.values(), key=lambda x: x["openTime"])
```

**Multi-source collectors:**
- `collect_base_1m_candles` — Collect 1m base candles từ InfluxDB/Trino
- `query_influx_candles` — Query InfluxDB `candles` measurement
- `query_trino_hourly` — Query Trino `silver.kline_multi_timeframe` for 1h

### 5.5.2 `indicator_service.py` — Indicator Business Logic

**Functions:**
- `get_indicator_snapshot(symbol, exchange, interval)` — Get latest indicators
- `get_indicator_summary(symbol, exchange, interval)` — Compact for AI
- `get_supported_indicators()` — Static list

**Snapshot implementation:**
```python
async def get_indicator_snapshot(symbol, exchange, interval):
    r = await get_redis()
    key = f"indicator:latest:{exchange}:{symbol}:{interval}"
    data = await r.hgetall(key)
    if not data:
        return IndicatorSnapshot(source="unavailable", ...)
    return IndicatorSnapshot(source="redis", data=data, freshness=...)
```

### 5.5.3 `market_data_service.py` — Market Data

**Tổng hợp cho frontend service:**
- Combine Redis + InfluxDB + Trino
- Cache layer
- Freshness tracking

---

## 5.6 Pydantic Models

### 5.6.1 `DataFreshness` model (models/common.py)

```python
class DataFreshness(BaseModel):
    source: str                          # redis, influxdb, trino, binance_rest, ticker_derived
    exchange: str | None
    event_time: int | None                # ms timestamp
    freshness_seconds: float | None       # now - event_time
    is_stale: bool                       # True if freshness > threshold
    is_fallback: bool                    # True if using fallback source
    warnings: list[str] = []
```

**Sử dụng:** Mỗi response có `metadata.freshness` để frontend biết data freshness.

### 5.6.2 Error Models

```python
class ErrorResponse(BaseModel):
    error: str
    detail: str | None = None
    request_id: str | None = None
```

### 5.6.3 Indicator Models

```python
class IndicatorValue(BaseModel):
    name: str
    value: float | None
    category: str                        # trend, momentum, volatility, volume
    freshness: DataFreshness | None

class IndicatorSnapshot(BaseModel):
    symbol: str
    exchange: str
    interval: str
    timestamp: int
    close: float
    high: float
    low: float
    volume: float
    sma20: float | None
    sma50: float | None
    ema12: float | None
    ema26: float | None
    rsi14: float | None
    bb_middle: float | None
    bb_upper: float | None
    bb_lower: float | None
    bb_width: float | None
    macd: float | None
    macd_signal: float | None
    macd_histogram: float | None
    atr14: float | None
    volume_sma20: float | None
    metadata: DataFreshness
```

---

## 5.7 Database Clients

### 5.7.1 Redis Sentinel (redis_sentinel.py)

**Master connection (for writes):**
```python
async def get_redis_master():
    return redis.asyncio.sentinel.Sentinel(
        [("redis-sentinel-1", 26379), ("redis-sentinel-2", 26379), ("redis-sentinel-3", 26379)],
        socket_timeout=2
    ).master_for("mymaster")
```

**Read connection (for reads, có thể từ slave):**
```python
async def get_redis():
    return redis.asyncio.Redis(host="redis", port=6379, decode_responses=True)
```

### 5.7.2 InfluxDB Client (database.py)

```python
def get_influx_client():
    return InfluxDBClient(
        url=os.getenv("INFLUX_URL", "http://influxdb:8086"),
        token=os.getenv("INFLUX_TOKEN"),
        org=os.getenv("INFLUX_ORG", "vi"),
    )
```

**Query example:**
```python
def query_influx_candles(symbol, interval, limit, range_h, end_time):
    query = f'''
    from(bucket: "crypto")
      |> range(start: -{range_h}h)
      |> filter(fn: (r) => r._measurement == "candles")
      |> filter(fn: (r) => r.symbol == "{symbol}")
      |> filter(fn: (r) => r.interval == "{interval}")
      |> pivot(rowKey:["_time"], columnKey: ["_field"], valueColumn: "_value")
      |> sort(columns: ["_time"], desc: false)
      |> limit(n: {limit})
    '''
    # ...
```

### 5.7.3 Trino Client (database.py)

```python
def get_trino_connection():
    return trino.dbapi.connect(
        host=os.getenv("TRINO_HOST", "trino"),
        port=int(os.getenv("TRINO_PORT", 8080)),
        user=os.getenv("TRINO_USER", "trino"),
        catalog="iceberg",
        schema="crypto_lakehouse",
    )
```

**Query example:**
```python
def query_trino_hourly(symbol, end_ms, limit):
    conn = get_trino_connection()
    cursor = conn.cursor()
    cursor.execute(f"""
        SELECT event_time, open_price, high_price, low_price, close_price, volume
        FROM silver.kline_multi_timeframe
        WHERE symbol = '{symbol}' AND interval = '1h'
          AND event_time <= {end_ms}
        ORDER BY event_time DESC
        LIMIT {limit}
    """)
    return cursor.fetchall()
```

### 5.7.4 PostgreSQL (postgres.py)

```python
async def get_pg_pool():
    return await asyncpg.create_pool(
        host=os.getenv("POSTGRES_HOST", "postgres"),
        port=5432,
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        database="auth",  # hoặc "ai" cho AI features
        min_size=2,
        max_size=20,
    )
```

**Connection pool:**
- min 2, max 20 connections
- Acquire/release pattern
- Health check on each acquire

---

## 5.8 Auth & Authorization

### 5.8.1 JWT Token

```python
def create_jwt_token(user_id: str, expires_in: int = 86400) -> str:
    payload = {
        "sub": user_id,
        "iat": datetime.utcnow(),
        "exp": datetime.utcnow() + timedelta(seconds=expires_in),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")
```

**Token storage:** Client lưu trong localStorage/cookie. Gửi trong header `Authorization: Bearer <token>`.

### 5.8.2 Protected Routes

```python
async def get_current_user(authorization: str = Header(...)) -> User:
    token = authorization.replace("Bearer ", "")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        raise HTTPException(401, "Token expired")
    user_id = payload["sub"]
    # Query user from PostgreSQL
    return await get_user(user_id)
```

### 5.8.3 Role-based Access Control

```python
async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(403, "Admin access required")
    return user
```

---

## 5.9 Performance Optimizations

### 5.9.1 Redis Caching Strategy

| Cache Key | TTL | Purpose |
|-----------|-----|---------|
| `klines_cache:{ex}:{sym}:{interval}:{limit}` | 200ms-1.5s | Klines response cache |
| `kline:1m:{ex}:{sym}` | 7 ngày | 1m candles |
| `kline:1s:{ex}:{sym}` | 1 ngày | 1s candles |
| `ticker:latest:{ex}:{sym}` | None | Latest ticker |
| `indicator:latest:{ex}:{sym}:{interval}` | 7 ngày | Latest indicators |

### 5.9.2 Multi-source Fallback

Mỗi endpoint có fallback chain rõ ràng:

**Klines:**
```
Redis cache (200ms TTL)
  → KeyDB 1s/1m ZSET
    → InfluxDB (90 days)
      → Trino silver.kline_multi_timeframe
        → Trino hourly fallback
```

**Order book:**
```
Redis orderbook:{ex}:{sym}
  → Redis orderbook:{sym} (legacy)
    → Ticker-derived synthetic
      → Binance REST API
```

**Trades:**
```
Redis trade:latest:{ex}:{sym} (true trades)
  → Redis ticker:history:{ex}:{sym} (ticker-derived)
```

**Market overview:**
```
Trino gold tables (if fresh)
  → Redis ticker scan (fallback)
```

### 5.9.3 Async/Await

Toàn bộ FastAPI handlers là async:
- `async def` cho mọi endpoint
- `await` cho I/O operations (Redis, InfluxDB, Trino, PostgreSQL)
- `asyncio.to_thread` cho blocking operations (Trino sync client)

### 5.9.4 Connection Pooling

| Resource | Pool Size | Notes |
|----------|-----------|-------|
| Redis async | Default | Connection per request |
| InfluxDB client | 1 per process | Reused |
| Trino connection | Per request | Via to_thread |
| PostgreSQL | 2-20 | asyncpg pool |

---

## 5.10 Error Handling

### 5.10.1 Standard Error Response

```python
{
  "error": "symbol_not_found",
  "detail": "No ticker data for BTCUSDT",
  "request_id": "req_abc123"
}
```

### 5.10.2 Error Categories

| HTTP Status | Use Case |
|-------------|----------|
| 400 | Invalid request (bad symbol, interval) |
| 401 | Unauthorized (no token) |
| 403 | Forbidden (insufficient role) |
| 404 | Resource not found (no data) |
| 429 | Rate limited |
| 500 | Internal server error |
| 503 | Service unavailable (DB down) |

### 5.10.3 Graceful Degradation

Khi một source fail → fallback sang source khác:
```python
try:
    trino_data = await query_trino(...)
except Exception as e:
    logger.warning("Trino gold query failed, falling back to Redis")
    redis_data = await query_redis(...)
    return redis_data
```

**Không bao giờ trả về 500** cho user-visible errors — luôn có fallback.

---

## 5.11 Health Checks

### 5.11.1 `/api/health` Endpoint

```python
@router.get("/health")
async def health():
    return {
        "status": "ok",
        "services": {
            "redis": await check_redis(),
            "influxdb": await check_influxdb(),
            "trino": await check_trino(),
            "postgres": await check_postgres(),
        },
        "timestamp": datetime.utcnow().isoformat(),
    }
```

**Service checks:**
- Redis: PING
- InfluxDB: Health endpoint
- Trino: SELECT 1
- PostgreSQL: SELECT 1

### 5.11.2 Kubernetes Liveness/Readiness

```yaml
livenessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /api/health
    port: 8000
  initialDelaySeconds: 5
  periodSeconds: 5
```

---

## 5.12 CORS & Security

### 5.12.1 CORS Configuration

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://lmview.example.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 5.12.2 Rate Limiting

```python
@app.middleware("http")
async def rate_limit(request: Request, call_next):
    client_ip = request.client.host
    # Check rate limit (e.g., 100 req/min)
    if await is_rate_limited(client_ip):
        raise HTTPException(429, "Too many requests")
    return await call_next(request)
```

### 5.12.3 Input Validation

Pydantic models validate tất cả inputs:
- Symbol: `BTCUSDT` (uppercase, alphanumeric)
- Interval: enum check
- Limit: 1-1500
- endTime: positive integer

---

## 5.13 Logging & Observability

### 5.13.1 Structured Logging

```python
logger.info("Stream %s error for %s: %s", interval, symbol, e)
```

**Log format:** `%(asctime)s [%(levelname)s] %(message)s`

### 5.13.2 Request Logging

```python
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration_ms = (time.time() - start_time) * 1000
    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration_ms:.0f}ms")
    return response
```

### 5.13.3 Metrics (Prometheus)

| Metric | Type | Description |
|--------|------|-------------|
| `http_requests_total` | Counter | Total HTTP requests by endpoint |
| `http_request_duration_seconds` | Histogram | Request duration |
| `redis_commands_total` | Counter | Redis commands executed |
| `ws_connections_active` | Gauge | Active WebSocket connections |
| `klines_cache_hits_total` | Counter | Cache hits |

---

**Tiếp theo: Part 6 — Technical Indicators (Flink Real-time vs Spark Batch)**

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# PHẦN 6: TECHNICAL INDICATORS — SO SÁNH CHI TIẾT FLINK vs SPARK

---

## 6.1 Tổng quan hệ thống Indicators

**Mô tả:** LMView tính toán technical indicators ở **HAI TẦNG** khác nhau với công thức và mục đích khác nhau:

| Tầng | Công thức | Timeframe | Output | Latency |
|------|-----------|-----------|--------|---------|
| **Flink (Speed)** | True EMA (exponential smoothing) | 1m candles, on closed candle | Redis `indicator:latest:{ex}:{sym}:{interval}` + InfluxDB `indicators` measurement | < 1s |
| **Spark (Batch/Lakehouse)** | SMA approximation qua `avg().over(window)` | 1h candles, batch run | Iceberg `gold.momentum_indicators` + `gold.indicator_history` | 5-30 min |

### 6.1.1 Tại sao cần 2 tầng?

| Concern | Flink (Speed) | Spark (Batch) |
|---------|---------------|---------------|
| **Latency** | Real-time (<1s) | Batch (5-30 min) |
| **Use case** | Live chart indicators, AI summary, real-time alerts | Historical analysis, screener, multi-timeframe comparison |
| **Data source** | Live 1m candles from Kafka | 1h candles from silver layer |
| **History** | Last 60 closes only (in-memory) | 7+ days (persistent) |
| **Accuracy** | True EMA formula | SMA-based approximation |
| **Storage** | Redis (hot) + InfluxDB (warm) | Iceberg (cold) |

### 6.1.2 Indicators được tính

| Indicator | Flink | Spark | Category |
|-----------|-------|-------|----------|
| **SMA20** | ✅ True SMA | ✅ SMA approx | Trend |
| **SMA50** | ✅ True SMA | ✅ SMA approx | Trend |
| **EMA12** | ✅ True EMA | ⚠️ SMA approx | Trend |
| **EMA26** | ✅ True EMA | ⚠️ SMA approx | Trend |
| **RSI14** | ✅ Wilder's RSI | ✅ Modified RSI | Momentum |
| **BB Upper** | ✅ Population stddev | ✅ Sample stddev | Volatility |
| **BB Middle** | ✅ | ✅ | Volatility |
| **BB Lower** | ✅ | ✅ | Volatility |
| **BB Width** | ✅ | ✅ | Volatility |
| **MACD Line** | ✅ EMA12 - EMA26 | ⚠️ SMA12 - SMA26 | Momentum |
| **MACD Signal** | ✅ True EMA of MACD | ⚠️ SMA approx | Momentum |
| **MACD Histogram** | ✅ MACD - Signal | ✅ | Momentum |
| **ATR14** | ✅ True Range | ❌ Not computed | Volatility |
| **Volume SMA20** | ✅ | ✅ | Volume |

### 6.1.3 Data Flow của Indicators

```
                    Exchange (Binance/OKX)
                              │
                    WebSocket tới Producer
                              │
                    Kafka topic: binance.klines.1m
                              │
                ┌─────────────┴─────────────┐
                │                           │
                ▼                           ▼
        ┌──────────────────┐      ┌──────────────────┐
        │  Flink Speed     │      │  Spark Batch     │
        │  (Real-time)     │      │  (Historical)    │
        │                  │      │                  │
        │  Closed 1m       │      │  1h candles      │
        │  candles         │      │  from silver     │
        │        │         │      │        │         │
        │        ▼         │      │        ▼         │
        │  IndicatorWriter │      │  calculate_      │
        │  (True EMA)      │      │  indicators.py   │
        │        │         │      │  (SMA approx)    │
        │        ▼         │      │        │         │
        │  Redis Hash      │      │        ▼         │
        │  + InfluxDB      │      │  Iceberg Gold    │
        └────────┬─────────┘      └────────┬─────────┘
                 │                          │
                 ▼                          ▼
        ┌──────────────────┐      ┌──────────────────┐
        │  Live chart      │      │  Historical      │
        │  Real-time       │      │  Multi-timeframe │
        │  AI summary      │      │  Screener        │
        └──────────────────┘      └──────────────────┘
```

---

## 6.2 Flink Real-time Indicators

### 6.2.1 IndicatorWriter Class

**File:** `src/processing/writers/indicators.py`  
**Loại:** PyFlink `FlatMapFunction`  
**Input:** Closed 1m kline từ Kafka topic `binance.klines.1m` (chỉ xử lý `is_closed=True`)  
**Output:**
- Redis Hash: `indicator:latest:{exchange}:{symbol}:{interval}` (TTL 7 ngày)
- Redis Hash legacy: `indicator:latest:{exchange}:{symbol}` (cho backward compat)
- Redis ZSET: `indicator:history:{exchange}:{symbol}:{interval}` (capped 10,080 entries)
- InfluxDB `indicators` measurement (buffered, flush 200 pts or 5s)

### 6.2.2 State Management (in-memory)

```python
def open(self, runtime_context):
    self._r = get_flink_redis()
    self._influx_client = InfluxDBClient(...)
    self._write_api = self._influx_client.write_api(...)
    
    # Per-symbol rolling buffers (maxlen=60)
    self._closes: dict[str, deque] = {}           # close prices
    self._volumes: dict[str, deque] = {}           # volumes
    self._candles: dict[str, deque] = {}           # full OHLC for ATR
    
    # EMA state (per symbol, per period)
    self._ema_state: dict[str, dict[int, float]] = {}  # {state_key: {period: ema_value}}
    
    # MACD signal EMA state
    self._macd_signal_state: dict[str, float] = {}  # {state_key: signal_ema}
    
    # InfluxDB buffering
    self._buffer = []
    self._last_flush = time.time()
    
    # History TTL
    self._history_ttl_sec = int(os.environ.get("INDICATOR_HISTORY_TTL_SEC", "604800"))  # 7 days
    self._history_max_entries = int(os.environ.get("INDICATOR_HISTORY_MAX_ENTRIES", "10080"))  # 7 days * 24h * 60min
```

**State key:** `f"{exchange}:{symbol}:{interval}"` — cho phép multi-exchange + multi-interval trong cùng writer.

### 6.2.3 Constants

```python
SMA_PERIODS = (20, 50)              # Two SMA periods
EMA_PERIODS = (12, 26)              # Two EMA periods (for MACD)
MAX_HISTORY = 60                    # Keep last 60 closes (enough for SMA50 + buffer)
```

**Lý do MAX_HISTORY=60:** SMA50 cần 50 closes, thêm 10 buffer = 60. Khi deque đầy, phần tử cũ nhất tự động bị loại bỏ.

### 6.2.4 SMA Formula (True Simple Moving Average)

```python
@staticmethod
def _sma(values, period):
    if len(values) < period:
        return None
    window = list(values)[-period:]   # Last `period` values
    return sum(window) / period        # True arithmetic mean
```

**Đặc điểm:**
- Cần đủ `period` candles mới có giá trị
- Mỗi candle mới → SMA update bằng cách bỏ candle cũ nhất, thêm candle mới nhất
- Không có state riêng (chỉ dựa trên deque)

### 6.2.5 EMA Formula (True Exponential Moving Average) ⭐

```python
def _ema(self, symbol, close_price, period):
    sym_state = self._ema_state.setdefault(symbol, {})
    if period not in sym_state:
        # First time: initialize with close_price
        sym_state[period] = close_price
        return close_price
    
    # EMA = (close - prev_ema) * k + prev_ema
    # where k = 2 / (period + 1)
    k = 2.0 / (period + 1)
    prev = sym_state[period]
    new_ema = close_price * k + prev * (1 - k)
    sym_state[period] = new_ema
    return new_ema
```

**Đặc điểm quan trọng:**
- **True EMA formula** với smoothing constant `k = 2/(period+1)`
- **State persistent** trong `self._ema_state[state_key][period]`
- Sau Flink restart → EMA state MẤT → cần warmup period (50+ candles để ổn định)
- Đây là lý do tại sao Spark dùng SMA approximation (không cần state)

**EMA initialization choice:** Dùng close_price làm seed. Một số implementation dùng SMA của N candles đầu tiên, nhưng LMView chọn close để đơn giản. Hệ quả: 12 candles đầu tiên EMA chưa ổn định.

### 6.2.6 RSI Formula (Wilder's RSI)

```python
@staticmethod
def _rsi(values, period=14):
    if len(values) < period + 1:
        return None
    closes = list(values)
    gains = 0.0
    losses = 0.0
    for idx in range(-period, 0):
        diff = closes[idx] - closes[idx - 1]
        if diff > 0:
            gains += diff
        else:
            losses -= diff
    avg_gain = gains / period
    avg_loss = losses / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))
```

**Công thức:**
1. Tính price change: `diff = close[i] - close[i-1]`
2. Tách thành gains (diff > 0) và losses (-diff > 0)
3. Sum gains/losses trong `period` candles gần nhất
4. `RS = avg_gain / avg_loss`
5. `RSI = 100 - 100/(1+RS)`

**Special case:** Nếu `avg_loss == 0` → RSI = 100 (chỉ có gains, không có losses)

**Lưu ý:** Đây là **simple RSI** (sum gains/period), không phải **Wilder's smoothed RSI** (dùng exponential smoothing cho avg_gain/avg_loss). Tuy nhiên kết quả rất gần với Wilder's RSI cho short period (14).

### 6.2.7 Bollinger Bands Formula (Population StdDev)

```python
@staticmethod
def _bollinger(values, period=20, multiplier=2.0):
    if len(values) < period:
        return None, None, None, None
    window = list(values)[-period:]
    middle = sum(window) / period
    deviation = pstdev(window) * multiplier if period > 1 else 0.0
    upper = middle + deviation
    lower = middle - deviation
    width = upper - lower
    return middle, upper, lower, width
```

**Sử dụng `statistics.pstdev`:** Population standard deviation (chia cho N, không phải N-1).
- Population stddev: `sqrt(sum((x - mean)^2) / N)`
- Sample stddev: `sqrt(sum((x - mean)^2) / (N-1))` ← Spark dùng cái này

**Hệ quả:** Flink BB hơi hẹp hơn Spark BB (do population stddev nhỏ hơn sample stddev). Sai số không đáng kể cho period=20 (chỉ khác ~2.5%).

### 6.2.8 ATR Formula (Average True Range)

```python
@staticmethod
def _atr(candles, period=14):
    rows = list(candles)
    if len(rows) < period + 1:
        return None
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
    return sum(true_ranges) / len(true_ranges) if true_ranges else None
```

**Công thức True Range:**
```
TR = max(
    high - low,                     # Range hiện tại
    |high - prev_close|,            # Gap up
    |low - prev_close|              # Gap down
)
```

**ATR14 = mean(TR[1..14])** — simple mean, không phải Wilder's smoothed ATR.

**Lưu ý:** Cần `len(rows) >= period + 1` vì mỗi TR cần 2 candles (current + prev).

### 6.2.9 MACD Formula (True EMA-based)

```python
ema12 = self._ema(state_key, close_price, 12)
ema26 = self._ema(state_key, close_price, 26)
rsi14 = self._rsi(prices, 14)
bb_middle, bb_upper, bb_lower, bb_width = self._bollinger(prices, 20, 2.0)
volume_sma20 = self._sma(volumes, 20)
macd = ema12 - ema26
macd_signal = self._macd_signal(state_key, macd, 9)
macd_histogram = macd - macd_signal
atr14 = self._atr(candles, 14)
```

**Components:**
1. **MACD Line** = EMA12 - EMA26 (true EMA, exponential smoothing)
2. **Signal Line** = EMA9 of MACD (true EMA, exponential smoothing)
3. **Histogram** = MACD Line - Signal Line

**MACD Signal state:**
```python
def _macd_signal(self, state_key, macd_value, period=9):
    if state_key not in self._macd_signal_state:
        self._macd_signal_state[state_key] = macd_value  # Seed với MACD value
        return macd_value
    
    k = 2.0 / (period + 1)
    prev = self._macd_signal_state[state_key]
    next_signal = macd_value * k + prev * (1 - k)
    self._macd_signal_state[state_key] = next_signal
    return next_signal
```

**Đặc điểm:** Signal line cũng dùng true EMA (không phải SMA). Đây là implementation chuẩn của MACD indicator.

### 6.2.10 Redis Write Pattern

```python
mapping = {
    "timestamp": kline_start,
    "interval": interval,
    "close": round(close_price, 8),
    "high": round(high_price, 8),
    "low": round(low_price, 8),
    "volume": round(volume, 8),
}
# Add các indicators (None values SKIP)
if sma20 is not None:
    mapping["sma20"] = round(sma20, 8)
# ... tương tự cho các indicator khác ...

# Write 3 keys:
self._r.hset(latest_key, mapping=mapping)         # Latest snapshot
self._r.hset(legacy_key, mapping=mapping)         # Backward compat (1m only)
self._r.zadd(history_key, {history_json: kline_start})  # History ZSET
```

**3 Redis keys per update:**
1. `indicator:latest:{exchange}:{symbol}:{interval}` — TTL 7 days
2. `indicator:latest:{exchange}:{symbol}` — TTL 7 days (legacy, chỉ cho 1m)
3. `indicator:history:{exchange}:{symbol}:{interval}` — ZSET, capped at 10,080 entries

**History dedup logic:**
```python
self._r.zremrangebyscore(history_key, kline_start, kline_start)  # Remove existing
self._r.zadd(history_key, {history_json: kline_start})           # Add new
```

**Why dedup:** Nếu cùng timestamp đã tồn tại (Flink replay, restart), ghi đè thay vì duplicate.

**Capping mechanism:**
```python
count = self._history_write_count.get(history_key, 0) + 1
self._history_write_count[history_key] = count
if count % self._history_max_entries == 0:  # Every 10,080 writes
    self._r.zremrangebyrank(history_key, 0, -self._history_max_entries - 1)
```

Giữ lại tối đa 10,080 entries (= 7 days × 24h × 60min) trong ZSET.

### 6.2.11 InfluxDB Write Pattern (Buffered)

```python
point = Point("indicators") \
    .tag("symbol", symbol) \
    .tag("exchange", exchange)

# Add fields (None values SKIP)
if sma20 is not None:
    point = point.field("sma20", round(sma20, 8))
# ...

# Time + close
point = point \
    .field("ema12", ...) \
    .field("ema26", ...) \
    .field("macd", ...) \
    .field("macd_signal", ...) \
    .field("macd_histogram", ...) \
    .field("close", close_price) \
    .time(kline_start, WritePrecision.MS)

self._buffer.append(point)

# Flush condition: buffer >= 200 points OR 5 seconds elapsed
if len(self._buffer) >= 200 or (time.time() - self._last_flush) >= 5.0:
    self._flush_influx()
```

**InfluxDB tags:** `symbol`, `exchange`  
**InfluxDB fields:** `sma20, sma50, rsi14, bb_middle, bb_upper, bb_lower, bb_width, volume_sma20, atr14, ema12, ema26, macd, macd_signal, macd_histogram, close`

**Time precision:** MS (milliseconds) — `kline_start` is in milliseconds.

**Buffer strategy:**
- Buffer 200 points (~200 symbols × 1 candle) hoặc 5 giây
- Synchronous write (SYNCHRONOUS) — đơn giản, đủ nhanh cho 1m batch
- Close() flushes remaining buffer

### 6.2.12 Performance

**Throughput estimate:**
- Input: 1m closed candles for ~150 symbols
- ~2-3 candles/giây peak
- 1 Redis HSET + 1 ZADD + 1 EXPIRE + 1 ZADD history ≈ 5 commands per candle
- ~15 Redis commands/giây
- InfluxDB: 200 points per 5s = 40 points/giây

**State size:**
- Per symbol: 3 deques × 60 entries + 2 EMA state + 1 MACD state = ~600 bytes
- 200 symbols: ~120KB total
- Hoàn toàn fit trong Flink TaskManager heap

### 6.2.13 Limitations & Caveats

| Caveat | Impact | Workaround |
|--------|--------|------------|
| **EMA state lost on restart** | First 50 candles after restart cho RSI/EMA không chính xác | Warmup period; Spark fills in later |
| **History capped at 10,080** | Chỉ giữ 7 days history trong Redis | Spark batch cho longer history |
| **In-memory state per parallel subtask** | Nếu state parallel > 1, EMA không nhất quán | Set `parallelism=1` cho indicator stream |
| **No real Wilder's smoothing for RSI** | RSI khác một chút so với TradingView | Acceptable cho 14-period |

---

## 6.3 Spark Batch Indicators

### 6.3.1 calculate_indicators.py — Batch Pipeline

**File:** `src/batch/unified/indicators.py`  
**Loại:** Spark batch job (standalone hoặc qua Airflow/Dagster)  
**Input:** Iceberg `silver.kline_multi_timeframe` table, filter `interval='1h'`, last 7 days  
**Output:** 
- `gold.momentum_indicators` (latest snapshot per symbol)
- `gold.indicator_history` (history of all indicators)

### 6.3.2 Reading Silver Table

```python
klines_df = spark.table("iceberg.crypto_lakehouse.kline_multi_timeframe") \
                .filter(
                    (col("interval") == "1h") &
                    (col("_partition_date") >= date_7d_ago)
                ) \
                .select("symbol", "event_time", "close_price", "volume")
```

**Input data:**
- `interval = "1h"` (1-hour candles only)
- 7 days lookback = 168 rows per symbol
- Sufficient for: RSI14 (need 15), SMA50 (need 50), BB20 (need 20), EMA26 (need 26)

### 6.3.3 RSI Formula (Window-based Approximation)

```python
def calculate_rsi(df, price_col="close_price", period=14):
    window = Window.partitionBy("symbol").orderBy("event_time")
    
    # 1. Price change
    df = df.withColumn("price_change", col(price_col) - lag(price_col, 1).over(window))
    
    # 2. Separate gains and losses
    df = df.withColumn("gain", when(col("price_change") > 0, col("price_change")).otherwise(0))
    df = df.withColumn("loss", when(col("price_change") < 0, -col("price_change")).otherwise(0))
    
    # 3. Average gain and loss (rolling 14-period)
    window_period = Window.partitionBy("symbol").orderBy("event_time") \
                        .rowsBetween(-period + 1, 0)
    df = df.withColumn("avg_gain", avg("gain").over(window_period))
    df = df.withColumn("avg_loss", avg("loss").over(window_period))
    
    # 4. RS and RSI
    df = df.withColumn(
        "rs",
        when(col("avg_loss") > 0, col("avg_gain") / col("avg_loss")).otherwise(100)
    )
    df = df.withColumn(
        f"rsi_{period}",
        100 - (100 / (1 + col("rs")))
    )
    return df
```

**Đặc điểm:**
- **Window-based** calculation sử dụng `Window.partitionBy("symbol").orderBy("event_time")`
- **Cùng công thức RSI** với Flink (simple RSI, không phải Wilder's smoothed)
- **Lag function** cho price change
- **Row-based window** với `rowsBetween(-period+1, 0)` = last `period` rows

### 6.3.4 MACD Formula (SMA Approximation) ⚠️

```python
def calculate_macd(df, price_col="close_price", fast=12, slow=26, signal=9):
    window = Window.partitionBy("symbol").orderBy("event_time")
    
    # 1. EMA approximation using SMA
    window_fast = Window.partitionBy("symbol").orderBy("event_time") \
                    .rowsBetween(-fast + 1, 0)
    window_slow = Window.partitionBy("symbol").orderBy("event_time") \
                    .rowsBetween(-slow + 1, 0)
    
    df = df.withColumn("ema_12", avg(price_col).over(window_fast))  # ⚠️ Actually SMA
    df = df.withColumn("ema_26", avg(price_col).over(window_slow))  # ⚠️ Actually SMA
    
    # 2. MACD line
    df = df.withColumn("macd", col("ema_12") - col("ema_26"))
    
    # 3. Signal line (SMA of MACD)
    window_signal = Window.partitionBy("symbol").orderBy("event_time") \
                      .rowsBetween(-signal + 1, 0)
    df = df.withColumn("macd_signal", avg("macd").over(window_signal))  # ⚠️ Actually SMA
    
    # 4. Histogram
    df = df.withColumn("macd_histogram", col("macd") - col("macd_signal"))
    return df
```

**⚠️ QUAN TRỌNG:** Tên cột là `ema_12` và `ema_26` nhưng giá trị thực tế là **SMA12 và SMA26**!  

**Tại sao SMA approximation:**
- **Dễ tính** trong Spark window functions
- **Không cần state** giữa các rows
- **Sai số chấp nhận được** cho 1h timeframe (EMA và SMA gần nhau khi period ngắn)

**Hệ quả:** MACD từ Spark sẽ **lag hơn** MACD từ Flink (vì SMA phản ứng chậm hơn EMA với price changes).

### 6.3.5 Bollinger Bands Formula (Sample StdDev)

```python
def calculate_bollinger_bands(df, price_col="close_price", period=20, std_dev=2):
    window = Window.partitionBy("symbol").orderBy("event_time") \
                  .rowsBetween(-period + 1, 0)
    
    # 1. Middle band (SMA)
    df = df.withColumn("bb_middle", avg(price_col).over(window))
    
    # 2. Standard deviation (sample stddev)
    df = df.withColumn("bb_std", stddev(price_col).over(window))  # ⚠️ Sample stddev
    
    # 3. Upper and lower bands
    df = df.withColumn("bb_upper", col("bb_middle") + (col("bb_std") * std_dev))
    df = df.withColumn("bb_lower", col("bb_middle") - (col("bb_std") * std_dev))
    
    # 4. Band width
    df = df.withColumn("bb_width", col("bb_upper") - col("bb_lower"))
    return df
```

**Sử dụng `stddev` (sample):** PySpark `stddev` function mặc định là **sample standard deviation** (chia cho N-1).

**So sánh với Flink:**
- Flink: `pstdev` (population, chia cho N)
- Spark: `stddev` (sample, chia cho N-1)
- Sai số: ~2.5% cho period=20

### 6.3.6 SMA Formula (Window-based)

```python
def calculate_sma(df, price_col="close_price", volume_col="volume", periods=[20, 50]):
    for period in periods:
        window = Window.partitionBy("symbol").orderBy("event_time") \
                      .rowsBetween(-period + 1, 0)
        df = df.withColumn(f"price_sma_{period}", avg(price_col).over(window))
        
        if period == 20:
            df = df.withColumn(f"volume_sma_{period}", avg(volume_col).over(window))
    return df
```

**Tính:**
- `price_sma_20` và `price_sma_50` (price SMA)
- `volume_sma_20` (volume SMA — chỉ period=20)

**Không có SMA từ EMA true** vì đây là Spark batch, không có state.

### 6.3.7 Output Schema (momentum_indicators)

```sql
CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.momentum_indicators (
    symbol STRING NOT NULL,
    snapshot_time TIMESTAMP NOT NULL,
    current_price DOUBLE,
    rsi_14 DOUBLE,
    macd DOUBLE,
    macd_signal DOUBLE,
    macd_histogram DOUBLE,
    bb_upper DOUBLE,
    bb_middle DOUBLE,
    bb_lower DOUBLE,
    bb_width DOUBLE,
    volume_sma_20 DOUBLE,
    price_sma_20 DOUBLE,
    price_sma_50 DOUBLE,
    price_ema_12 DOUBLE,    -- Actually SMA12 (misnomer)
    price_ema_26 DOUBLE,    -- Actually SMA26 (misnomer)
    _partition_date DATE NOT NULL
) USING iceberg
PARTITIONED BY (_partition_date)
```

**⚠️ Lưu ý:** Tên cột `price_ema_12` và `price_ema_26` thực chất chứa **SMA12 và SMA26**. Tên này giữ để consistent với Flink schema.

### 6.3.8 Output Schema (indicator_history)

```sql
CREATE TABLE IF NOT EXISTS iceberg.crypto_lakehouse.indicator_history (
    exchange STRING NOT NULL,        -- Always "aggregated" cho batch
    symbol STRING NOT NULL,
    interval STRING NOT NULL,        -- Always "1h"
    candle_time BIGINT NOT NULL,     -- ms timestamp
    candle_timestamp TIMESTAMP NOT NULL,
    close_price DOUBLE,
    volume DOUBLE,
    rsi_14 DOUBLE,
    macd DOUBLE,
    macd_signal DOUBLE,
    macd_histogram DOUBLE,
    bb_upper DOUBLE,
    bb_middle DOUBLE,
    bb_lower DOUBLE,
    bb_width DOUBLE,
    volume_sma_20 DOUBLE,
    price_sma_20 DOUBLE,
    price_sma_50 DOUBLE,
    price_ema_12 DOUBLE,    -- Actually SMA12
    price_ema_26 DOUBLE,    -- Actually SMA26
    computed_at TIMESTAMP NOT NULL,
    _partition_date DATE NOT NULL
) USING iceberg
PARTITIONED BY (_partition_date, interval, exchange)
```

**Partitioning:** Theo `_partition_date`, `interval`, `exchange` — cho multi-day queries efficient.

**Note:** `exchange` luôn là `"aggregated"` cho batch vì data đã merge multi-exchange ở silver layer.

### 6.3.9 Write Mode

```python
# History table: append
history_df.writeTo("iceberg.crypto_lakehouse.indicator_history").append()

# Latest snapshot: dynamic overwrite
result_df.write \
    .format("iceberg") \
    .mode("overwrite") \
    .option("overwrite-mode", "dynamic") \
    .saveAsTable("iceberg.crypto_lakehouse.momentum_indicators")
```

**`overwrite-mode=dynamic`:** Chỉ overwrite matching partitions (`_partition_date = current_date`), giữ lại lịch sử. Cho phép idempotent re-runs.

### 6.3.10 Performance

**Input data size:**
- 200 symbols × 168 hours (7 days) = 33,600 rows
- Mỗi row ~200 bytes → ~7MB
- Sau calculation: 33,600 rows × 20 columns = ~13MB

**Execution time:**
- Trên cluster 4 cores, 8GB RAM: ~30 giây
- Trên single machine: ~2-3 phút

**Cost:** Job chạy mỗi 5-30 phút (qua Airflow/Dagster) → 48-288 runs/ngày. Chấp nhận được.

---

## 6.4 So sánh Side-by-Side: Flink vs Spark

### 6.4.1 Công thức Side-by-Side

| Indicator | Flink Real-time | Spark Batch | Difference |
|-----------|-----------------|-------------|------------|
| **SMA20** | `sum(last_20_closes) / 20` | `avg(close).over(window 20 rows)` | Identical |
| **SMA50** | `sum(last_50_closes) / 50` | `avg(close).over(window 50 rows)` | Identical |
| **EMA12** | `close * k + prev_ema * (1-k)`, k=2/13 | `avg(close).over(window 12 rows)` ⚠️ | **Fl: true EMA, Sp: SMA** |
| **EMA26** | `close * k + prev_ema * (1-k)`, k=2/27 | `avg(close).over(window 26 rows)` ⚠️ | **Fl: true EMA, Sp: SMA** |
| **RSI14** | `(100 - 100/(1+RS))`, simple gain/loss sum | `100 - 100/(1+RS)`, avg gain/loss | Very similar (within 0.5) |
| **BB Middle** | `sum(last_20)/20` | `avg(close).over(20)` | Identical |
| **BB Upper** | `middle + 2*pstdev` | `middle + 2*stddev` | **Fl: pop, Sp: sample** |
| **BB Lower** | `middle - 2*pstdev` | `middle - 2*stddev` | **Fl: pop, Sp: sample** |
| **MACD Line** | `ema12 - ema26` (true) | `sma12 - sma26` (approximation) | **Fl: true, Sp: lag** |
| **MACD Signal** | `EMA9 of MACD` (true) | `SMA9 of MACD` (approximation) | **Fl: true, Sp: lag** |
| **ATR14** | `mean(TR[1..14])` (true Range) | ❌ Not computed | **Fl only** |

### 6.4.2 Data Source Side-by-Side

| Aspect | Flink | Spark |
|--------|-------|-------|
| **Source** | Kafka `binance.klines.1m` | Iceberg `silver.kline_multi_timeframe` (1h only) |
| **Granularity** | 1m candles | 1h candles (aggregated) |
| **Lookback** | 60 candles (1 hour rolling) | 7 days = 168 hours |
| **State** | In-memory (deque + EMA state dict) | Window functions (no state) |
| **Multi-exchange** | Yes (per `state_key`) | Merged (single "aggregated" exchange) |

### 6.4.3 Latency Side-by-Side

| Event | Flink | Spark |
|-------|-------|-------|
| **Event in** | Kafka message | Iceberg partition (after silver ETL) |
| **Compute latency** | < 100ms (in-memory) | 30-60s (Spark job) |
| **To Redis** | < 200ms | N/A (only to Iceberg) |
| **To InfluxDB** | ~5s (batch flush) | N/A |
| **To Iceberg** | N/A | 10-30s (write commit) |
| **Total to user** | < 1s | 5-30 min (batch interval) |

### 6.4.4 Use Case Mapping

| Use Case | Best Source | Reason |
|----------|-------------|--------|
| **Live chart indicator overlay** | Flink | Real-time, accurate EMA |
| **AI Helper summary** | Flink | Fresh data, low latency |
| **WebSocket indicator stream** | Flink | Real-time push |
| **Screener (RSI<30)** | Spark | Persistent, multi-symbol query |
| **Historical comparison (1d vs 1w)** | Spark | Long history, multiple timeframes |
| **Backtesting** | Spark | Persistent, deterministic |
| **Multi-timeframe analysis** | Spark | 1h aggregation chuẩn |
| **Real-time alerts (RSI<30 trigger)** | Flink | Real-time notification |
| **Performance analytics (1h return)** | Spark | Aggregated, queryable |

### 6.4.5 Storage Side-by-Side

| Storage | Flink Writes To | Spark Writes To |
|---------|-----------------|-----------------|
| **Redis Hash** | `indicator:latest:{ex}:{sym}:{interval}` | N/A |
| **Redis ZSET** | `indicator:history:{ex}:{sym}:{interval}` (capped 10080) | N/A |
| **InfluxDB** | `indicators` measurement (15 fields) | N/A |
| **Iceberg** | N/A | `gold.momentum_indicators` (latest snapshot) |
| **Iceberg** | N/A | `gold.indicator_history` (full history) |

### 6.4.6 Schema Differences (Flink vs Spark naming)

| Field name (Flink) | Field name (Spark) | Notes |
|---------------------|---------------------|-------|
| `close` | `close_price` | Spark dùng suffix `_price` |
| `sma20` | `price_sma_20` | Spark dùng prefix `price_` |
| `sma50` | `price_sma_50` | |
| `ema12` | `price_ema_12` | Spark lưu SMA12 gắn nhãn EMA |
| `ema26` | `price_ema_26` | |
| `rsi14` | `rsi_14` | Spark dùng underscore |
| `bb_upper` | `bb_upper` | Same |
| `bb_middle` | `bb_middle` | Same |
| `bb_lower` | `bb_lower` | Same |
| `bb_width` | `bb_width` | Same |
| `macd` | `macd` | Same |
| `macd_signal` | `macd_signal` | Same |
| `macd_histogram` | `macd_histogram` | Same |
| `atr14` | (not computed) | Flink only |
| `volume_sma20` | `volume_sma_20` | Spark underscore |

**Naming convention difference:** Flink dùng `camelCase` (Redis convention), Spark dùng `snake_case` (SQL/Iceberg convention).

### 6.4.7 Field Count Difference

| Layer | Fields | Notes |
|-------|--------|-------|
| **Flink Redis Hash** | 19 fields | `timestamp, interval, close, high, low, volume, sma20, sma50, ema12, ema26, rsi14, bb_middle, bb_upper, bb_lower, bb_width, macd, macd_signal, macd_histogram, atr14, volume_sma20` |
| **Spark momentum_indicators** | 14 fields | No `atr14`, no `high/low/interval/timestamp/volume` |
| **Spark indicator_history** | 20 fields | Same as Flink + `candle_time, candle_timestamp, computed_at, _partition_date` |

### 6.4.8 Trade-off Analysis

| Trade-off | Flink Choice | Spark Choice | Verdict |
|-----------|--------------|--------------|---------|
| **Accuracy vs Simplicity** | True EMA (state required) | SMA approx (no state) | Flink wins for accuracy |
| **Latency vs Cost** | Real-time, high resource | Batch, low resource | Flink wins for latency |
| **Freshness vs History** | Last 60 candles | 7+ days | Spark wins for history |
| **Consistency vs Speed** | First 50 candles after restart unstable | Always stable | Spark wins for consistency |
| **Multi-timeframe** | Per-interval state | Single calculation, multiple uses | Spark wins for reuse |
| **Real-time alerts** | Possible | Not possible | Flink only choice |

---

## 6.5 Pipeline Sequence Diagram

### 6.5.1 Flink Indicator Pipeline

```
┌─────────────────┐
│ Binance WebSocket│
│ (kline stream)  │
└────────┬────────┘
         │ JSON message
         ▼
┌─────────────────┐
│ Producer        │ Parse JSON, produce to Kafka
└────────┬────────┘
         │ Avro record
         ▼
┌─────────────────┐
│ Kafka topic:    │ binance.klines.1m
│ 12 partitions   │
└────────┬────────┘
         │ Consumer (Flink)
         ▼
┌─────────────────┐
│ KlineWindow     │ Forward-fill gaps, aggregate 1m from 1s
│ Aggregator      │ Only emit when is_closed=True
└────────┬────────┘
         │ Closed 1m candle
         ▼
┌─────────────────┐
│ IndicatorWriter │ Compute SMA/EMA/RSI/BB/MACD/ATR
│ (FlatMap)       │ Per-symbol state in-memory
└────┬───────┬────┘
     │       │
     ▼       ▼
┌────────┐ ┌──────────┐
│ Redis  │ │ InfluxDB │
│ Hash + │ │ buffer   │
│ ZSET   │ │ (200pts) │
└────────┘ └────┬─────┘
                │ Flush 5s
                ▼
          ┌──────────┐
          │ InfluxDB │
          │ indicators│
          │ measure  │
          └──────────┘
```

### 6.5.2 Spark Indicator Pipeline

```
┌─────────────────┐
│ Iceberg Bronze  │ coin_klines (raw)
└────────┬────────┘
         │ (via Spark streaming batch)
         ▼
┌─────────────────┐
│ Iceberg Silver  │ kline_multi_timeframe
│ (5m,15m,1h,4h,1d)│
└────────┬────────┘
         │ Filter 1h, last 7 days
         ▼
┌─────────────────┐
│ calculate_      │ calculate_rsi()
│ indicators.py   │ calculate_macd()
│                 │ calculate_bollinger_bands()
│                 │ calculate_sma()
└────────┬────────┘
         │ Enriched DataFrame
         ▼
┌─────────────────┐
│ Window: latest  │ row_number() per symbol
│ per symbol      │ ORDER BY event_time DESC
└────────┬────────┘
         │ Latest snapshot
         ▼
┌─────────────────┐
│ gold.momentum_  │ Dynamic overwrite
│ indicators      │ (current partition only)
└─────────────────┘

         │ All rows (history)
         ▼
┌─────────────────┐
│ gold.indicator_ │ Append all rows
│ history         │
└─────────────────┘
```

---

## 6.6 Query Pattern Examples

### 6.6.1 Flink-side query (Redis)

**Latest indicators for BTCUSDT 1m:**
```bash
HGETALL indicator:latest:binance:BTCUSDT:1m
```

**Returns:**
```
1) "timestamp" → "1672531140000"
2) "interval" → "1m"
3) "close" → "16500.00"
4) "sma20" → "16480.50"
5) "sma50" → "16460.25"
6) "ema12" → "16490.10"
7) "ema26" → "16475.30"
8) "rsi14" → "62.5"
9) "bb_upper" → "16520.30"
10) "bb_lower" → "16440.70"
11) "macd" → "14.80"
12) "macd_signal" → "10.20"
13) "macd_histogram" → "4.60"
14) "atr14" → "35.20"
15) "volume_sma20" → "120.50"
```

**Latest indicators for ALL timeframes BTCUSDT (pipeline):**
```python
pipe = r.pipeline()
for iv in ["1m", "5m", "15m", "1h", "4h", "1d"]:
    pipe.hgetall(f"indicator:latest:binance:BTCUSDT:{iv}")
results = await pipe.execute()
```

### 6.6.2 Spark-side query (Trino)

**Latest momentum indicators:**
```sql
SELECT * FROM iceberg.crypto_lakehouse.gold_momentum_indicators
WHERE snapshot_time = (
    SELECT MAX(snapshot_time) FROM iceberg.crypto_lakehouse.gold_momentum_indicators
)
ORDER BY symbol;
```

**Symbols with RSI < 30 (oversold):**
```sql
SELECT symbol, current_price, rsi_14, volume_sma_20
FROM iceberg.crypto_lakehouse.gold_momentum_indicators
WHERE rsi_14 < 30
  AND snapshot_time = (SELECT MAX(snapshot_time) FROM iceberg.crypto_lakehouse.gold_momentum_indicators)
ORDER BY rsi_14 ASC;
```

**Indicator history for BTCUSDT 1h:**
```sql
SELECT candle_timestamp, close_price, rsi_14, macd, bb_upper, bb_lower
FROM iceberg.crypto_lakehouse.gold_indicator_history
WHERE symbol = 'BTCUSDT'
  AND interval = '1h'
  AND _partition_date >= current_date - INTERVAL '7' DAY
ORDER BY candle_time ASC;
```

---

## 6.7 Warmup & Bootstrap

### 6.7.1 Flink Warmup (Sau Restart)

**Vấn đề:** Sau Flink restart, EMA state mất. Cần 50+ candles để EMA ổn định.

**Giải pháp:**
1. **State backend** với RocksDB (persistent) — config trong Flink
2. **Savepoint** trước khi restart
3. **Cold start** chấp nhận được: 50 candles × 1m = 50 phút warmup

**Trong production:** Flink dùng RocksDB state backend → EMA state persistent qua restart. Tuy nhiên trong dev/test, có thể cần warmup.

### 6.7.2 Spark Warmup

**Không cần warmup** vì Spark dùng window functions trên full 7-day data. Cứ 7 days data mỗi lần chạy.

### 6.7.3 Bootstrap mới symbol

**Flink:**
- Khi symbol mới xuất hiện, indicator buffer (`_closes`, `_ema_state`) tự tạo
- 50 candles sau sẽ có SMA50 chính xác
- EMA được seed với close price (chưa ổn định cho ~26 candles)

**Spark:**
- Khi symbol mới, cần đủ 50 hours history trong silver
- Nếu silver chưa có → momentum_indicators có null fields

---

## 6.8 Monitoring & Alerting

### 6.8.1 Flink-side Metrics

| Metric | Source | Alert |
|--------|--------|-------|
| `indicator_writer_records_total` | Flink metrics | - |
| `indicator_writer_errors_total` | Flink metrics | > 10/min |
| `influx_buffer_size` | Flink metrics | > 500 sustained |
| `redis_p99_latency_ms` | Redis Sentinel | > 10ms |
| `ema_state_size` | Flink metrics | Memory pressure |

### 6.8.2 Spark-side Metrics

| Metric | Source | Alert |
|--------|--------|-------|
| Job duration | Airflow/Dagster | > 10 min |
| Output row count | Spark | < expected - 10% |
| Iceberg write latency | Iceberg | > 30s |
| Bronze→silver lag | Airflow | > 2 hours |

### 6.8.3 Data Quality Checks

**Flink:**
- RSI phải trong [0, 100]
- BB Lower < BB Middle < BB Upper
- Volume >= 0
- Timestamp phải tăng dần

**Spark:**
- Cùng checks
- Thêm: `price_sma_50` chỉ có sau 50 rows history

---

## 6.9 Indicator Coverage Matrix

| Timeframe | Source | Use Case |
|-----------|--------|----------|
| **1s** | ❌ Not computed | Real-time chart uses 1s klines directly |
| **1m** | ✅ Flink (real-time) | Live chart, AI summary, alerts |
| **5m** | ✅ Flink (real-time) | Short-term trading |
| **15m** | ✅ Flink (real-time) | Intraday |
| **1h** | ✅ Flink + Spark (batch) | Multi-source consistency |
| **4h** | ✅ Flink (real-time) | Swing trading |
| **1d** | ✅ Flink (real-time) | Long-term chart |
| **1w** | ✅ Flink (real-time) | Long-term chart |

**Note:** Flink chỉ tính indicators từ 1m source. Cho timeframes 5m/15m/1h/4h/1d/1w, Flink aggregate candles từ 1m rồi tính indicators riêng.

---

**Tiếp theo: Part 7 — Data Flow Diagrams & End-to-End Latency**

**Phiên bản:** 0.23.1  
**Ngày cập nhật:** 2026-06-11  
**Trạng thái:** Production

---

# PHẦN 7: DATA FLOW DIAGRAMS & END-TO-END LATENCY

---

## 7.1 Tổng quan hệ thống (System Overview)

### 7.1.1 Lambda Architecture End-to-End

```
┌────────────────────────────────────────────────────────────────────────────┐
│                              LMView Platform                                │
│                                                                              │
│  ┌──────────────┐                                                            │
│  │   Exchange   │  Binance, OKX                                              │
│  │  (Source)    │  WebSocket Public Streams                                  │
│  └──────┬───────┘                                                            │
│         │ ticker, kline, trade, depth messages                              │
│         ▼                                                                    │
│  ┌──────────────┐                                                            │
│  │   Producer   │  src/producer/main.py                                      │
│  │  (Python)    │  Threading + WebSocket clients                              │
│  └──────┬───────┘                                                            │
│         │ Avro encoded                                                       │
│         ▼                                                                    │
│  ┌──────────────────────────────────────────────────────────────┐            │
│  │                     KAFKA BROKER (KRaft)                    │            │
│  │  Topics:                                                      │            │
│  │   • binance.ticker       (1 part)                            │            │
│  │   • binance.klines.1m    (3 parts)                            │            │
│  │   • binance.klines.1s    (3 parts)                            │            │
│  │   • binance.trades       (3 parts)                            │            │
│  │   • binance.depth        (1 part)                             │            │
│  │   • okx.ticker           (1 part, opt-in)                     │            │
│  │   • okx.klines.1m        (3 parts, opt-in)                    │            │
│  │   • okx.trades           (3 parts, opt-in)                    │            │
│  └──────┬─────────────────────────────────────┬────────────────┘            │
│         │                                     │                              │
│         │ Speed Layer                         │ Batch Layer                  │
│         ▼                                     ▼                              │
│  ┌──────────────────┐               ┌──────────────────────┐                │
│  │   FLINK JOB      │               │   SPARK BATCH JOB    │                │
│  │  (PyFlink)       │               │  (Iceberg + MinIO)   │                │
│  │                  │               │                      │                │
│  │  Writers:        │               │  • bronze_to_silver  │                │
│  │  • KlineAggregator│              │  • unified indicators│                │
│  │  • KeyDBKline     │              │  • silver_to_gold    │                │
│  │  • KeyDBTicker    │              │  • market_metrics    │                │
│  │  • KeyDBTrade     │              │                      │                │
│  │  • KeyDBDepth     │              │  Tables:             │                │
│  │  • Indicator      │              │  • bronze (3)        │                │
│  │  • InfluxDBTicker │              │  • silver (2)        │                │
│  │  • InfluxDBKline  │              │  • gold (9)          │                │
│  └────┬─────────────┘               └──────┬───────────────┘                │
│         │                                  │                                │
│         ▼                                  ▼                                │
│  ┌──────────────────────────────────────────────────────────────────┐        │
│  │                      STORAGE LAYER                              │        │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌────────────────┐  │        │
│  │  │ Redis Sentinel  │  │   InfluxDB      │  │  Iceberg/MinIO │  │        │
│  │  │  (Hot cache)    │  │  (Analytics)    │  │  (Lakehouse)   │  │        │
│  │  └────────┬────────┘  └────────┬────────┘  └────────┬───────┘  │        │
│  └───────────┼─────────────────────┼────────────────────┼──────────┘        │
│              │                     │                    │                    │
│              │                     │                    │                    │
│              └─────────────────────┴────────────────────┘                    │
│                                    │                                          │
│                                    ▼                                          │
│                          ┌──────────────────────┐                            │
│                          │   SERVING LAYER      │                            │
│                          │  (FastAPI + WS)      │                            │
│                          │                      │                            │
│                          │  Routes:             │                            │
│                          │  • /api/klines       │                            │
│                          │  • /api/ticker       │                            │
│                          │  • /api/stream/*     │                            │
│                          │  • /api/indicators   │                            │
│                          │  • /api/market/*     │                            │
│                          │  • /api/auth         │                            │
│                          │  • /api/ai/*         │                            │
│                          └──────────┬───────────┘                            │
│                                     │                                         │
│                                     ▼                                         │
│                          ┌──────────────────────┐                            │
│                          │  REACT FRONTEND      │                            │
│                          │  (Vite + React 19)   │                            │
│                          │                      │                            │
│                          │  Features:           │                            │
│                          │  • Chart             │                            │
│                          │  • Watchlist         │                            │
│                          │  • AI Helper         │                            │
│                          │  • Settings          │                            │
│                          └──────────────────────┘                            │
└────────────────────────────────────────────────────────────────────────────┘
```

### 7.1.2 Data Flow Philosophy

| Principle | Implementation |
|-----------|----------------|
| **Single source of truth** | Kafka cho in-flight data, Iceberg cho historical |
| **Compute once, serve many** | Flink compute → Redis → multiple consumers (WS, REST) |
| **Multi-source fallback** | Redis → InfluxDB → Trino → REST API |
| **Schema evolution** | Avro + Schema Registry |
| **Immutable history** | Iceberg append-only với snapshot isolation |
| **Real-time + Batch** | Lambda architecture: speed layer + batch layer |

---

## 7.2 Sequence Diagrams (End-to-End)

### 7.2.1 Real-time Kline Data Flow

```
┌──────┐   ┌──────────┐   ┌──────┐   ┌─────────┐   ┌───────┐   ┌─────┐   ┌──────┐
│Binance│  │ Producer │   │Kafka │   │  Flink  │   │Redis  │   │ API │   │ React│
└──┬───┘   └────┬─────┘   └──┬───┘   └────┬────┘   └───┬───┘   └──┬──┘   └──┬───┘
   │            │            │            │            │           │         │
   │  WS kline  │            │            │            │           │         │
   │ message    │            │            │            │           │         │
   ├───────────►│            │            │            │           │         │
   │            │            │            │            │           │         │
   │            │ Parse JSON │            │            │           │         │
   │            │ → Avro     │            │            │           │         │
   │            ├───────────►│            │            │           │         │
   │            │            │            │            │           │         │
   │            │            │ Consume    │            │           │         │
   │            │            ├───────────►│            │           │         │
   │            │            │            │            │           │         │
   │            │            │            │ Aggregate │           │         │
   │            │            │            │ 1s → 1m   │           │         │
   │            │            │            │            │           │         │
   │            │            │            │ ZADD      │           │         │
   │            │            │            ├───────────►│           │         │
   │            │            │            │            │           │         │
   │            │            │            │ HSET       │           │         │
   │            │            │            ├───────────►│           │         │
   │            │            │            │            │           │         │
   │            │            │            │ Compute   │           │         │
   │            │            │            │ indicators │           │         │
   │            │            │            ├───────────►│           │         │
   │            │            │            │            │           │         │
   │            │            │            │            │ WS push  │         │
   │            │            │            │            ├──────────►│         │
   │            │            │            │            │           │         │
   │            │            │            │            │           │ Update │
   │            │            │            │            │           │ chart  │
   │            │            │            │            │           ├────────►│
   │            │            │            │            │           │         │
   ▼            ▼            ▼            ▼            ▼           ▼         ▼
  ~0ms         ~10ms        ~20ms        ~50ms        ~100ms      ~120ms   ~150ms

Total latency: Exchange → User < 200ms
```

### 7.2.2 Historical Klines Query

```
┌──────┐   ┌──────┐   ┌─────┐   ┌───────┐   ┌─────┐   ┌──────┐
│React │   │ API  │   │Redis│   │Influx │   │Trino│   │React │
└──┬───┘   └──┬───┘   └──┬──┘   └───┬───┘   └──┬──┘   └──┬───┘
   │          │          │          │          │         │
   │ GET      │          │          │          │         │
   │ /api/    │          │          │          │         │
   │ klines?  │          │          │          │         │
   │ interval=│          │          │          │         │
   │ 1d      │          │          │          │         │
   │ limit=90│          │          │          │         │
   ├─────────►│          │          │          │         │
   │          │          │          │          │         │
   │          │ Validate │          │          │         │
   │          │ params   │          │          │         │
   │          │          │          │          │         │
   │          │ GET cache│          │          │         │
   │          ├─────────►│          │          │         │
   │          │          │          │          │         │
   │          │ Miss     │          │          │         │
   │          │◄─────────┤          │          │         │
   │          │          │          │          │         │
   │          │ Query    │          │          │         │
   │          │ InfluxDB │          │          │         │
   │          ├─────────────────────►│          │         │
   │          │          │          │          │         │
   │          │◄─────────────────────┤          │         │
   │          │          │          │          │         │
   │          │ Aggregate│          │          │         │
   │          │ 1m→1d    │          │          │         │
   │          │          │          │          │         │
   │          │ Cache    │          │          │         │
   │          ├─────────►│          │          │         │
   │          │          │          │          │         │
   │          │ Return   │          │          │         │
   │          │ JSON     │          │          │         │
   │          │◄───────────────────────────────►         │
   │          │          │          │          │         │
   ▼          ▼          ▼          ▼          ▼         ▼
 0ms         5ms        10ms        200ms                  250ms

Total latency: 250ms (cache miss) or 5ms (cache hit)
```

### 7.2.3 Indicator Real-time Stream

```
┌───────┐   ┌──────┐   ┌──────────┐   ┌──────┐   ┌──────┐   ┌─────┐
│Binance│   │Kafka │   │Indicator │   │Redis │   │  WS  │   │React│
│  WS   │   │      │   │ Writer   │   │      │   │  /   │   │     │
│       │   │      │   │ (Flink)  │   │      │   │stream│   │     │
└──┬────┘   └──┬───┘   └────┬─────┘   └──┬───┘   └──┬───┘   └──┬──┘
   │           │            │            │          │         │
   │ Close     │            │            │          │         │
   │ 1m candle │            │            │          │         │
   ├──────────►│            │            │          │         │
   │           │            │            │          │         │
   │           │ Consume    │            │          │         │
   │           ├───────────►│            │          │         │
   │           │            │            │          │         │
   │           │            │ Update     │          │         │
   │           │            │ deque      │          │         │
   │           │            │            │          │         │
   │           │            │ Compute    │          │         │
   │           │            │ SMA/EMA    │          │         │
   │           │            │ RSI/BB     │          │         │
   │           │            │            │          │         │
   │           │            │ HSET       │          │         │
   │           │            ├───────────►│          │         │
   │           │            │            │          │         │
   │           │            │ ZADD       │          │         │
   │           │            │ history    │          │         │
   │           │            ├───────────►│          │         │
   │           │            │            │          │         │
   │           │            │ Buffer     │          │         │
   │           │            │ InfluxDB   │          │         │
   │           │            │            │          │         │
   │           │            │            │ WS poll  │         │
   │           │            │            │ (50ms)   │         │
   │           │            │            │◄─────────┤         │
   │           │            │            │          │         │
   │           │            │            │ HGETALL  │         │
   │           │            │            ├─────────►│         │
   │           │            │            │          │         │
   │           │            │            │ Return   │         │
   │           │            │            │◄─────────┤         │
   │           │            │            │          │         │
   │           │            │            │ Send     │         │
   │           │            │            │ JSON     │         │
   │           │            │            ├─────────►│         │
   │           │            │            │          │         │
   │           │            │            │          │ Update  │
   │           │            │            │          │ chart   │
   │           │            │            │          ├────────►│
   │           │            │            │          │         │
   ▼           ▼            ▼            ▼          ▼         ▼
 0ms          50ms        100ms        110ms      150ms     160ms

Total latency: 160ms (Binance close → React update)
```

### 7.2.4 Order Book Flow

```
┌───────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌──────┐   ┌─────┐
│Binance│   │Kafka │   │Depth │   │Redis │   │ API  │   │React│
│  WS   │   │      │   │Writer│   │      │   │      │   │     │
└──┬────┘   └──┬───┘   └──┬───┘   └──┬───┘   └──┬───┘   └──┬──┘
   │           │          │          │          │         │
   │ Depth     │          │          │          │         │
   │ diff      │          │          │          │         │
   ├──────────►│          │          │          │         │
   │           │          │          │          │         │
   │           │ Consume  │          │          │         │
   │           ├─────────►│          │          │         │
   │           │          │          │          │         │
   │           │          │ Maintain │          │         │
   │           │          │ local    │          │         │
   │           │          │ book     │          │         │
   │           │          │          │          │         │
   │           │          │ HSET     │          │         │
   │           │          ├─────────►│          │         │
   │           │          │          │          │         │
   │           │          │          │ GET      │         │
   │           │          │          │◄─────────┤         │
   │           │          │          │          │         │
   │           │          │          │ HGETALL  │         │
   │           │          │          ├─────────►│         │
   │           │          │          │          │         │
   │           │          │          │ Return   │         │
   │           │          │          │◄─────────┤         │
   │           │          │          │          │         │
   │           │          │          │ Return  │         │
   │           │          │          │ JSON    │         │
   │           │          │          │◄──────────────────┤
   │           │          │          │          │         │
   ▼           ▼          ▼          ▼          ▼         ▼
 0ms          50ms       100ms      110ms      115ms    120ms

Total latency: 120ms (Binance depth → React)
```

---

## 7.3 Cold Path (Batch) — Data Flow

### 7.3.1 Bronze → Silver → Gold

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│ Exchange │     │ Bronze   │     │ Silver   │     │ Gold     │
│  WS      │     │  Layer   │     │  Layer   │     │  Layer   │
└────┬─────┘     └────┬─────┘     └────┬─────┘     └────┬─────┘
     │               │                │                │
     │ Spark         │                │                │
     │ Streaming     │                │                │
     │ batch         │                │                │
     │               │                │                │
     ▼               ▼                ▼                ▼
  ┌─────────────────────────────────────────────────────────┐
  │              bronze.coin_klines                         │
  │  • symbol, exchange, event_time, interval               │
  │  • OHLCV, ignore flags                                  │
  │  • Partition: days(event_time)                           │
  │  • Format: Parquet + Snappy                              │
  └─────────────────────────┬───────────────────────────────┘
                            │ bronze_to_silver
                            │ • dedup
                            │ • normalize schema
                            │ • add quality_score
                            ▼
  ┌─────────────────────────────────────────────────────────┐
  │              silver.kline_multi_timeframe               │
  │  • unified Binance + OKX (5m, 15m, 1h, 4h, 1d)         │
  │  • quality_score: 0/50/100                              │
  │  • Partition: days(event_time), interval                 │
  │  • Source count, completeness flags                      │
  └─────────────────────────┬───────────────────────────────┘
                            │ silver_to_gold
                            │ calculate_indicators
                            │ aggregations
                            ▼
  ┌─────────────────────────────────────────────────────────┐
  │  gold.indicator_history (20 cols)                       │
  │  gold.momentum_indicators (latest snapshot)             │
  │  gold.market_overview                                   │
  │  gold.coin_ticker                                       │
  │  gold.market_dominance                                  │
  │  gold.volatility_ranking                                │
  │  gold.movers_ranking                                    │
  │  gold.sector_performance                                │
  │  gold.news_sentiment                                    │
  └─────────────────────────────────────────────────────────┘
                            │ Trino query
                            ▼
                      ┌──────────┐
                      │  FastAPI │
                      │ /api/    │
                      │  market  │
                      └────┬─────┘
                           │ JSON
                           ▼
                      ┌──────────┐
                      │  React   │
                      │  /market │
                      └──────────┘

Latency: 5-30 minutes (batch interval)
```

### 7.3.2 Bronze Layer Detail

```
binance.klines.1m topic (Kafka)
        │
        │  Spark Structured Streaming
        │  foreachBatch (every 1 minute)
        ▼
┌──────────────────────────────────────────────────────────────┐
│  bronze.coin_klines (Iceberg)                                │
│                                                              │
│  Schema:                                                     │
│    symbol STRING                                             │
│    exchange STRING                                           │
│    interval STRING                                           │
│    event_time BIGINT                                         │
│    open_time BIGINT                                          │
│    close_time BIGINT                                         │
│    open_price DOUBLE                                         │
│    high_price DOUBLE                                         │
│    low_price DOUBLE                                          │
│    close_price DOUBLE                                        │
│    volume DOUBLE                                             │
│    quote_volume DOUBLE                                       │
│    trade_count BIGINT                                        │
│    taker_buy_base DOUBLE                                     │
│    taker_buy_quote DOUBLE                                    │
│    ignore BOOLEAN                                            │
│    kafka_offset BIGINT                                       │
│    kafka_partition INT                                       │
│    kafka_timestamp TIMESTAMP                                 │
│    _partition_date DATE  (days(event_time))                  │
│                                                              │
│  Partition: days(event_time)                                 │
│  Format: Parquet + Snappy                                    │
│  Mode: append                                                │
└──────────────────────────────────────────────────────────────┘
```

### 7.3.3 Silver Layer Detail

```
bronze.coin_klines
        │
        │  bronze_to_silver_unified
        │  - dedup by (exchange, symbol, interval, event_time)
        │  - filter !ignore
        │  - aggregate 1m → 5m/15m/1h/4h/1d
        ▼
┌──────────────────────────────────────────────────────────────┐
│  silver.kline_multi_timeframe (Iceberg)                      │
│                                                              │
│  Schema:                                                     │
│    symbol STRING                                             │
│    exchange STRING (or "aggregated" for multi-ex)            │
│    interval STRING (5m, 15m, 1h, 4h, 1d)                    │
│    event_time BIGINT                                         │
│    open_price, high_price, low_price, close_price DOUBLE     │
│    volume, quote_volume DOUBLE                               │
│    trade_count BIGINT                                        │
│    source_exchanges ARRAY<STRING>                            │
│    quality_score INT  (0/50/100)                             │
│    is_complete BOOLEAN                                       │
│    _partition_date DATE                                      │
│                                                              │
│  Partition: days(event_time), interval                       │
│  Quality scoring:                                            │
│    100: all sources agree                                    │
│    50: partial sources                                       │
│    0: synthetic/single source                                │
└──────────────────────────────────────────────────────────────┘
```

### 7.3.4 Gold Layer Detail

```
silver.kline_multi_timeframe
        │
        │  calculate_indicators + aggregations
        ▼
┌──────────────────────────────────────────────────────────────┐
│  Gold Tables (9 tables)                                      │
│                                                              │
│  1. gold.coin_ticker                                         │
│     - latest ticker per symbol                              │
│     - 24h volume, change_pct                                 │
│                                                              │
│  2. gold.momentum_indicators                                 │
│     - latest RSI, MACD, BB                                   │
│     - per symbol snapshot                                    │
│                                                              │
│  3. gold.indicator_history                                   │
│     - 1h indicator history                                   │
│     - 7 days + computed_at                                   │
│                                                              │
│  4. gold.market_overview                                     │
│     - top gainers, losers, volatile                          │
│     - computed every 30 min                                 │
│                                                              │
│  5. gold.market_dominance                                    │
│     - BTC, ETH, others %                                    │
│     - fear_greed_index                                       │
│                                                              │
│  6. gold.volatility_ranking                                  │
│     - ATR-based volatility                                   │
│                                                              │
│  7. gold.movers_ranking                                      │
│     - gainers, losers, volume                                │
│     - multiple timeframes                                    │
│                                                              │
│  8. gold.sector_performance                                  │
│     - Layer1, DeFi, Meme, ...                                │
│                                                              │
│  9. gold.news_sentiment                                      │
│     - news aggregated by symbol                              │
│     - sentiment scoring                                      │
└──────────────────────────────────────────────────────────────┘
```

---

## 7.4 Latency Budget

### 7.4.1 Real-time Path (Exchange → User)

| Step | Component | Time | Notes |
|------|-----------|------|-------|
| 1 | Exchange WebSocket send | 0ms | Reference point |
| 2 | Producer receive | ~5ms | Network + parse |
| 3 | Producer → Kafka | ~10ms | Avro encode + produce |
| 4 | Kafka → Flink | ~10-30ms | Consumer fetch |
| 5 | Flink aggregate/writer | ~20-50ms | Compute + serialize |
| 6 | Redis write | ~5-10ms | Pipeline write |
| 7 | WS poll interval | 50ms | Sleep loop |
| 8 | HGETALL | ~5-10ms | Redis read |
| 9 | WS send to client | ~10-30ms | Network |
| 10 | React render | ~5-10ms | lightweight-charts |
| **Total** | | **~120-205ms** | p99 ~250ms |

**Optimized path (v0.23.1):**
- Step 7: 50ms (was 300ms)
- Redis pipeline: 1 round-trip
- Total: ~150-200ms p99

### 7.4.2 REST API Latency

| Endpoint | Cache Hit | Cache Miss | Cold Path |
|----------|-----------|------------|-----------|
| `/api/klines` (1m, limit=200) | 5ms | 50-100ms (Redis ZSET) | 200-500ms (InfluxDB) |
| `/api/klines` (1d, limit=365) | 5ms | 200-500ms (InfluxDB) | 1-3s (Trino) |
| `/api/ticker` (all) | 5ms | 100-200ms (Redis SCAN) | N/A |
| `/api/orderbook` | 5ms | 50-100ms (Redis) | 500ms (Binance REST) |
| `/api/trades` | 5ms | 50-100ms (Redis ZSET) | N/A |
| `/api/indicators` | 5ms | 50-100ms (Redis HGETALL) | 500ms-1s (Trino) |
| `/api/market/overview` | 30s TTL | 100-200ms (Trino) | 5-10s (Spark recompute) |
| `/api/auth/login` | N/A | 100-200ms (PostgreSQL) | N/A |

### 7.4.3 Batch Path Latency

| Stage | Latency | Frequency |
|-------|---------|-----------|
| Bronze write | < 1 minute | Real-time (foreachBatch) |
| Bronze → Silver | 5-10 min | Every 10 min (Airflow) |
| Silver → Gold indicators | 5-10 min | Every 30 min (Dagster) |
| Silver → Gold aggregations | 10-20 min | Every hour |
| Trino query | 1-3s | On-demand |

### 7.4.4 Kafka Latency

| Producer → Broker | ~5-10ms |
|------------------|---------|
| Broker → Consumer | ~10-30ms |
| End-to-end (Producer → Consumer) | ~20-50ms |
| Producer batch | 1ms (linger.ms=0) |
| Consumer poll | 100ms (default) |

### 7.4.5 Flink Latency

| Checkpoint interval | 60s (default) |
|---------------------|---------------|
| Watermark | event_time - 5s (out-of-order tolerance) |
| Window trigger | 1m tumbling (klines), 5s sliding (ticker) |
| End-to-end | ~30-50s (for 1m kline) |

---

## 7.5 Throughput Analysis

### 7.5.1 Producer Throughput

**Binance Producer:**
- ~100-200 ticker messages/giây
- ~50-100 1s kline messages/giây
- ~500-2000 trade messages/giây (high volatility)
- ~1-5 depth updates/giây

**Total Producer Output:** ~2,000-5,000 Kafka messages/giây peak

### 7.5.2 Kafka Throughput

| Topic | Partitions | Replicas | Throughput |
|-------|-----------|----------|------------|
| `binance.ticker` | 1 | 2 | ~200 msg/s |
| `binance.klines.1m` | 3 | 2 | ~2 msg/s |
| `binance.klines.1s` | 3 | 2 | ~100 msg/s |
| `binance.trades` | 3 | 2 | ~2,000 msg/s peak |
| `binance.depth` | 1 | 2 | ~5 msg/s |

**Total:** ~2,300 msg/s peak, ~50 MB/s network

### 7.5.3 Flink Throughput

| Writer | Throughput | Notes |
|--------|------------|-------|
| KlineAggregator | ~100 candles/s | 1s granularity |
| KeyDBKline | ~200 ZADD/s | After aggregation |
| KeyDBTicker | ~200 HSET/s | All symbols |
| KeyDBTrade | ~2,000 ZADD/s | All trades |
| KeyDBDepth | ~5 HSET/s | Depth updates |
| Indicator | ~2-3/s | Per 1m close |
| InfluxDBTicker | ~200 points/s | Buffered |
| InfluxDBKline | ~5 points/s | Buffered |

**Total Redis writes:** ~5,000-10,000 ops/s peak  
**Total InfluxDB writes:** ~200 points/s peak (batched 200 per 5s)

### 7.5.4 Spark Throughput

| Job | Input Size | Output Size | Duration |
|-----|-----------|-------------|----------|
| bronze_to_silver (klines) | 1M rows/day | 100K rows | 2-5 min |
| bronze_to_silver (ticker) | 500K rows/day | 50K rows | 1-2 min |
| unified_indicators | 30K rows | 30K rows | 30s |
| silver_to_gold | 100K rows | 5K rows | 1-2 min |
| calculate_all_metrics | 30K rows | 1K rows | 30s |

**Total:** ~10 min total per cycle

### 7.5.5 FastAPI Throughput

| Endpoint | RPS (steady) | RPS (peak) |
|----------|--------------|------------|
| `/api/stream/all` | 100 WS | 500 WS |
| `/api/stream/{interval}` | 200 WS | 1000 WS |
| `/api/klines` | 100 | 500 |
| `/api/ticker` | 200 | 1000 |
| `/api/orderbook` | 50 | 200 |

**Total:** ~1000 RPS peak, ~300 RPS steady

---

## 7.6 Failure Modes & Recovery

### 7.6.1 Component Failure Scenarios

| Failure | Impact | Detection | Recovery |
|---------|--------|-----------|----------|
| **Producer crash** | No new data from exchange | Kafka lag increases | Auto-restart (Docker) |
| **Kafka broker down** | Pipeline stalled | Health check fail | Sentinel re-election |
| **Flink TM crash** | Stream processing stopped | Flink metrics | Restart from checkpoint |
| **Redis master down** | Writes fail | Sentinel fail-over | Auto-promote slave |
| **InfluxDB down** | Analytics write fail | InfluxDB health | Buffer, retry |
| **Spark job fail** | Gold tables stale | Airflow alert | Re-run from last checkpoint |
| **Trino down** | Historical queries fail | Health check | Fallback to InfluxDB |
| **PostgreSQL down** | Auth fails | Health check | Read from cache |
| **FastAPI crash** | API unavailable | K8s liveness | Auto-restart pod |

### 7.6.2 Data Loss Scenarios

| Scenario | Data Loss | Mitigation |
|----------|-----------|------------|
| **Producer crash before Kafka ACK** | Yes (last 1s) | Retry with backoff |
| **Kafka broker crash before replication** | Minimal (acks=all) | Min in-sync replicas = 2 |
| **Flink crash mid-checkpoint** | Restart from checkpoint | Checkpoint interval 60s |
| **Redis crash** | Hot data lost | Master-slave replication + RDB/AOF |
| **Iceberg corruption** | Historical data at risk | Time travel + snapshots |
| **InfluxDB loss** | Analytics data lost | Iceberg has copies |

### 7.6.3 Recovery Time Objectives (RTO)

| Component | RTO | Strategy |
|-----------|-----|----------|
| **Producer** | < 30s | Docker restart |
| **Flink** | < 5 min | Restart from checkpoint |
| **Redis** | < 30s | Sentinel fail-over |
| **Spark** | < 30 min | Re-run batch job |
| **Trino** | < 5 min | Restart worker |

### 7.6.4 Recovery Point Objectives (RPO)

| Component | RPO | Strategy |
|-----------|-----|----------|
| **Producer → Kafka** | < 1s | At-least-once delivery |
| **Kafka → Flink** | < 60s | Checkpoint-based |
| **Flink → Redis** | 0 (synchronous) | At-least-once |
| **Bronze → Silver** | 0 (idempotent) | Append-only |
| **Silver → Gold** | 0 (idempotent) | Overwrite partitions |

---

## 7.7 Scaling Patterns

### 7.7.1 Horizontal Scaling

| Component | Scale Method | Limit |
|-----------|--------------|-------|
| **Producer** | Multiple instances (different symbols) | Exchange rate limits |
| **Kafka brokers** | Add brokers, rebalance | 3-5 brokers typical |
| **Flink TMs** | Add TaskManagers, increase parallelism | 10-20 TMs |
| **Redis** | Shard by symbol, sentinel cluster | 3 masters + 3 slaves |
| **Spark workers** | Add worker nodes | 10-20 workers |
| **FastAPI pods** | K8s HPA based on CPU/RPS | 50+ pods |
| **Trino workers** | Add workers | 20+ workers |

### 7.7.2 Vertical Scaling

| Component | Current | Max Recommended |
|-----------|---------|------------------|
| **Producer** | 1 CPU, 512MB | 2 CPU, 1GB |
| **Flink TM** | 4 CPU, 8GB | 8 CPU, 16GB |
| **Redis** | 4 CPU, 16GB | 8 CPU, 32GB |
| **Spark Worker** | 4 CPU, 8GB | 16 CPU, 64GB |
| **FastAPI Pod** | 1 CPU, 1GB | 2 CPU, 2GB |

### 7.7.3 Data Partitioning

| Data | Partition Key | Reason |
|------|---------------|--------|
| **Kafka messages** | `symbol` (or `exchange:symbol`) | Order per symbol |
| **Redis keys** | `ticker:latest:{exchange}:{symbol}` | Sharding friendly |
| **InfluxDB** | `symbol`, `exchange` tags | Index-based |
| **Iceberg** | `days(event_time)`, `interval`, `exchange` | Time-based queries |
| **PostgreSQL** | `user_id` (UUID) | Even distribution |

---

## 7.8 Cost Optimization

### 7.8.1 Storage Cost Reduction

| Technique | Savings | Trade-off |
|-----------|---------|-----------|
| **Iceberg partition pruning** | 60% scan reduction | Requires partition key |
| **Parquet + Snappy** | 70% size reduction vs CSV | CPU for compression |
| **TTL on Redis** | Auto-cleanup old data | Cold data lost |
| **InfluxDB retention policies** | Auto-delete after 90 days | Historical limited |
| **S3 Intelligent-Tiering** | 30% on cold storage | Slightly slower access |

### 7.8.2 Compute Cost Reduction

| Technique | Savings | Trade-off |
|-----------|---------|-----------|
| **Flink batch flush (200pts/5s)** | 80% fewer InfluxDB writes | Slight delay |
| **Spark dynamic allocation** | 50% on idle | Slow startup |
| **Trino query result cache** | 90% repeat queries | Stale data risk |
| **Redis pipeline** | 6× fewer round-trips | More memory per op |

### 7.8.3 Network Cost Reduction

| Technique | Savings | Trade-off |
|-----------|---------|-----------|
| **WebSocket compression** | 70% bandwidth | CPU overhead |
| **Avro vs JSON** | 40% size reduction | Schema registry dependency |
| **Iceberg column pruning** | 50% I/O reduction | Requires careful SELECT |
| **Redis hash instead of JSON** | 30% size | Field-level access only |

---

## 7.9 Monitoring Stack

### 7.9.1 Metrics Pipeline

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ Components   │     │  Prometheus  │     │   Grafana    │
│ (Flink,      │────►│  (scrape)    │────►│  (visualize) │
│  Redis,      │     │              │     │              │
│  Spark,      │     └──────────────┘     └──────────────┘
│  FastAPI)    │
└──────────────┘
        │
        │ Logs
        ▼
┌──────────────┐     ┌──────────────┐
│   Loki       │────►│   Grafana    │
│  (aggregate) │     │  (logs)      │
└──────────────┘     └──────────────┘
```

### 7.9.2 Key Metrics

| Metric | Component | Alert Threshold |
|--------|-----------|-----------------|
| `kafka_consumer_lag` | Flink | > 10,000 sustained |
| `flink_checkpoint_duration` | Flink | > 60s |
| `flink_restart_count` | Flink | > 5/hour |
| `redis_connected_clients` | Redis | > 1000 |
| `redis_used_memory_bytes` | Redis | > 80% of maxmemory |
| `influxdb_write_points_per_second` | InfluxDB | < expected - 50% |
| `spark_job_duration` | Spark | > expected + 50% |
| `spark_job_failure_rate` | Spark | > 10% |
| `http_request_duration_seconds` | FastAPI | p99 > 500ms |
| `ws_connections_active` | FastAPI | > 1000 |

### 7.9.3 Alert Channels

| Severity | Channel | Example |
|----------|---------|---------|
| **Critical** | PagerDuty | Redis master down |
| **Warning** | Slack | Kafka lag spike |
| **Info** | Email | Daily job report |

---

## 7.10 Capacity Planning

### 7.10.1 Current Capacity (v0.23.1)

| Component | Capacity | Headroom |
|-----------|----------|----------|
| **Producers** | 200 symbols | 2x growth OK |
| **Kafka** | 3 brokers × 4TB | 50% used |
| **Flink** | 4 TMs × 8GB | 60% used |
| **Redis** | 16GB master + slave | 40% used |
| **InfluxDB** | 100GB | 30% retention |
| **Iceberg** | 5TB MinIO | 20% used |
| **FastAPI** | 10 pods | 50% CPU |

### 7.10.2 Growth Projections

| Metric | Current | 6 months | 12 months |
|--------|---------|----------|-----------|
| **Symbols** | 200 | 500 | 1,000 |
| **Exchanges** | 2 | 4 | 6 |
| **Timeframes** | 8 | 8 | 12 |
| **Daily klines** | 2.3M | 6M | 12M |
| **Storage** | 5TB | 15TB | 30TB |
| **Concurrent WS** | 200 | 1,000 | 5,000 |

### 7.10.3 Scale-up Triggers

| Trigger | Action |
|---------|--------|
| **Redis memory > 80%** | Add shard, increase maxmemory |
| **Kafka disk > 70%** | Add broker, increase retention |
| **Flink checkpoint > 60s** | Increase parallelism, scale TM |
| **FastAPI p99 > 500ms** | Add pods, optimize queries |
| **Trino query > 30s** | Add workers, optimize SQL |

---

## 7.11 Reference Architecture Diagram

### 7.11.1 Production Topology (Docker)

```
┌────────────────────────────────────────────────────────────────────┐
│                    Production Docker Compose                         │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Source Layer (profile: dev, prod)                          │  │
│  │  • binance-producer                                          │  │
│  │  • okx-producer (ENABLE_OKX=true)                           │  │
│  │  • backfill-historical                                       │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Streaming Layer (profile: dev, prod)                       │  │
│  │  • kafka-1, kafka-2, kafka-3 (KRaft mode)                  │  │
│  │  • schema-registry (Confluent)                              │  │
│  │  • jobmanager (Flink)                                       │  │
│  │  • taskmanager-1, taskmanager-2, taskmanager-3              │  │
│  │  • iceberg-rest-catalog                                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Storage Layer (profile: dev, prod)                         │  │
│  │  • redis-sentinel-1, redis-sentinel-2, redis-sentinel-3    │  │
│  │  • redis-master, redis-slave                                │  │
│  │  • influxdb                                                  │  │
│  │  • minio (S3-compatible)                                     │  │
│  │  • postgres                                                  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Batch Layer (profile: dev, prod)                           │  │
│  │  • spark-master, spark-worker-1, spark-worker-2             │  │
│  │  • trino-coordinator, trino-worker-1, trino-worker-2        │  │
│  │  • airflow-webserver, airflow-scheduler                     │  │
│  │  • dagster-daemon, dagster-webserver                        │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Serving Layer (profile: dev, prod)                         │  │
│  │  • backend (FastAPI)                                         │  │
│  │  • frontend (Nginx → React)                                  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Monitoring (profile: monitoring)                           │  │
│  │  • prometheus                                                │  │
│  │  • grafana                                                   │  │
│  │  • loki                                                      │  │
│  │  • node-exporter                                             │  │
│  │  • kafka-exporter                                            │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  Logging (profile: logging)                                 │  │
│  │  • elasticsearch                                             │  │
│  │  • kibana                                                    │  │
│  │  • logstash                                                  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │  AI (profile: ai)                                            │  │
│  │  • litellm (optional, opt-in)                                │  │
│  │  • vllm (optional, opt-in)                                   │  │
│  │  • ai-service (scaffold)                                     │  │
│  └─────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────┘
```

### 7.11.2 Network Ports Reference

| Service | Port | Protocol | Purpose |
|---------|------|----------|---------|
| Kafka | 9092, 9093 | TCP | Broker, TLS |
| Kafka Connect | 8083 | HTTP | Schema Registry (alt) |
| Schema Registry | 8081 | HTTP | Avro schema |
| Flink JM | 8081 | HTTP | Web UI |
| Flink TM | 6121-6199 | TCP | Internal RPC |
| Redis | 6379 | TCP | Client |
| Redis Sentinel | 26379 | TCP | Sentinel |
| InfluxDB | 8086 | HTTP | API |
| MinIO | 9000, 9001 | HTTP | S3, Console |
| PostgreSQL | 5432 | TCP | SQL |
| Spark | 7077, 8080, 8081 | TCP/HTTP | Master, Master UI, Worker UI |
| Trino | 8080 | HTTP | Coordinator |
| Airflow | 8080 | HTTP | Webserver |
| Dagster | 3000, 4000 | HTTP | Webserver, Daemon |
| Prometheus | 9090 | HTTP | Metrics |
| Grafana | 3000 | HTTP | Dashboard |
| FastAPI | 8000 | HTTP | API |
| Frontend | 80, 443 | HTTP/HTTPS | Web (Nginx) |

---

## 7.12 Glossary of Acronyms

| Term | Definition |
|------|------------|
| **Avro** | Row-based data format with schema evolution |
| **CMA** | Continuous Moving Average |
| **EMA** | Exponential Moving Average |
| **Flink** | Distributed stream processing framework |
| **Iceberg** | Table format for huge analytic datasets |
| **InfluxDB** | Time-series database |
| **Kafka** | Distributed event streaming platform |
| **KeyDB** | Redis fork with multi-threading |
| **KRaft** | Kafka's built-in consensus (no Zookeeper) |
| **Lambda Architecture** | Speed + Batch + Serving layers |
| **MinIO** | S3-compatible object storage |
| **OHLCV** | Open, High, Low, Close, Volume |
| **Parquet** | Columnar storage format |
| **PyFlink** | Python API for Apache Flink |
| **RPO** | Recovery Point Objective (max data loss) |
| **RTO** | Recovery Time Objective (max downtime) |
| **SMA** | Simple Moving Average |
| **Spark** | Distributed batch processing engine |
| **Trino** | Distributed SQL query engine |
| **WAL** | Write-Ahead Log |
| **WS** | WebSocket |
| **ZSET** | Redis Sorted Set |

---

## 7.13 Kết luận toàn bộ DATA_FLOW series

### 7.13.1 Tóm tắt 7 phần

| Phần | File | Nội dung | Size |
|------|------|----------|------|
| **1** | `DATA_FLOW_01_ARCH_OVERVIEW.md` | Architecture overview + Exchange Ingestion (Binance+OKX WebSocket, threading, JSON formats, canonical mapping) | 16.3KB |
| **2** | `DATA_FLOW_02_KAFKA.md` | Kafka Broker (4 topics×12 partitions, Avro schemas, Confluent wire format, Schema Registry, partitioning, performance) | 14.4KB |
| **3** | `DATA_FLOW_03_FLINK.md` | Flink Speed Layer (8 writers, IndicatorWriter với true EMA/RSI/BB/MACD/ATR, KlineWindowAggregator gap-fill, batch-buffered, Redis patterns, InfluxDB measurements) | 31.2KB |
| **4** | `DATA_FLOW_04_SPARK_LAKEHOUSE.md` | Spark Lakehouse (Bronze 3 tables, Silver 2 tables với quality scoring, Gold 9 tables, pipeline orchestration) | 41.6KB |
| **5** | `DATA_FLOW_05_SERVING.md` | Serving Layer (FastAPI + WebSocket với Redis pipeline optimization, 20+ REST endpoints, multi-source fallback) | 49.3KB |
| **6** | `DATA_FLOW_06_INDICATORS.md` | Technical Indicators (Flink true EMA vs Spark SMA approximation, side-by-side comparison, formulas chi tiết) | 35.6KB |
| **7** | `DATA_FLOW_07_DIAGRAMS.md` | Data Flow Diagrams + End-to-End Latency (sequence diagrams, cold path, throughput, scaling, capacity planning) | 38KB+ |
| **Total** | | **7 files** | **~226KB** |

### 7.13.2 Coverage Matrix

| Topic | Part | Status |
|-------|------|--------|
| **Architecture overview** | 1 | ✅ |
| **Exchange WebSocket clients** | 1 | ✅ |
| **Kafka broker + Avro** | 2 | ✅ |
| **Flink writers (8)** | 3 | ✅ |
| **KlineWindowAggregator** | 3 | ✅ |
| **Indicator formulas (Flink)** | 3, 6 | ✅ |
| **Indicator formulas (Spark)** | 4, 6 | ✅ |
| **Bronze tables (3)** | 4 | ✅ |
| **Silver tables (2)** | 4 | ✅ |
| **Gold tables (9)** | 4 | ✅ |
| **Redis key patterns (9)** | 3 | ✅ |
| **InfluxDB measurements (3)** | 3 | ✅ |
| **Kafka topics (4)** | 2 | ✅ |
| **Avro schemas (4)** | 2 | ✅ |
| **FastAPI routes (20+)** | 5 | ✅ |
| **WebSocket routes (3)** | 5 | ✅ |
| **Multi-source fallback** | 5 | ✅ |
| **Flink vs Spark comparison** | 6 | ✅ |
| **Data flow diagrams** | 7 | ✅ |
| **End-to-end latency** | 7 | ✅ |
| **Throughput analysis** | 7 | ✅ |
| **Failure modes & recovery** | 7 | ✅ |
| **Scaling patterns** | 7 | ✅ |
| **Capacity planning** | 7 | ✅ |
| **Production topology** | 7 | ✅ |

### 7.13.3 Đặc điểm nổi bật

1. **Multi-layer architecture:** Lambda pattern với 3 layers (Speed, Batch, Serving) rõ ràng
2. **Multi-source fallback:** Mọi endpoint có chain rõ ràng (Redis → InfluxDB → Trino → REST)
3. **Schema evolution:** Avro + Iceberg hỗ trợ backward/forward compatibility
4. **Real-time + Historical:** Flink cho live (<1s), Spark cho analytics (5-30 min)
5. **Indicator accuracy trade-off:** Flink dùng true EMA (state), Spark dùng SMA approximation (stateless)
6. **WebSocket optimization:** 6× faster updates (v0.23.1) qua Redis pipeline + 50ms loop
7. **Production-ready:** Failure recovery, scaling patterns, monitoring stack documented

### 7.13.4 Caveats & Known Limitations

| Caveat | Part | Note |
|--------|------|------|
| **Flink depth drops exchange** | 1, 3, 6 | Depth processing still defaults `exchange` to binance |
| **Spark ticker dedup omits exchange** | 1, 4 | `coin_ticker` dedup không xét exchange |
| **OKX kline interval wrong** | 1, 2, 3 | OKX kline Kafka records chưa normalize interval |
| **Indicator state lost on restart** | 6 | EMA state chỉ persistent với RocksDB |
| **Spark EMA = SMA misnomer** | 4, 6 | Column name `price_ema_*` chứa SMA values |
| **Heatmap helper stale join** | 5 | `/api/market/heatmap` vẫn có join với `iceberg_catalog.gold` |
| **No frontend test script** | 5 | Frontend chỉ có typecheck + build, no unit tests |
| **Dagster Spark catalog mismatch** | 4, 7 | Dagster Spark config khác main streaming lakehouse |
| **AI mock default** | 5 | Real LLM cần `AI_ENABLE_REAL_LLM=true` + deps |

---

**HẾT PHẦN 7 — KẾT THÚC DATA_FLOW SERIES**

Tổng cộng 7 file DATA_FLOW_*.md cung cấp documentation đầy đủ và chi tiết về data flow của LMView, từ exchange ingestion đến React frontend, bao gồm tất cả storage layers, processing frameworks, serving endpoints, indicator calculations, và operational concerns.
