# LMView - Crypto Real-Time Data Platform 🚀

Nền tảng streaming giá crypto real-time từ **Binance WebSocket**, xử lý bằng **Apache Flink** + **Apache Spark** theo kiến trúc **Lambda Architecture**, cung cấp dữ liệu qua **FastAPI** + **React Dashboard**.

[![Docker](https://img.shields.io/badge/Docker-21_Services-blue?logo=docker)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](backend/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](frontend/)
[![Apache Flink](https://img.shields.io/badge/Apache_Flink-1.18.1-E6522C?logo=apacheflink)](src/processing/)
[![Kafka](https://img.shields.io/badge/Apache_Kafka-3.9.0-231F20?logo=apachekafka)](docker-compose.yml)

---

## 🏗️ Kiến Trúc Hệ Thống

```
┌─────────────────────────────────────────────────────────────────────┐
│                    BINANCE WEBSOCKET (400 Symbols)                   │
└─────────────────────────────┬───────────────────────────────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   KAFKA HA (3x)  │
                    │  - crypto_ticker │
                    │  - crypto_trades │
                    │  - crypto_klines │
                    │  - crypto_depth  │
                    └──────────────────┘
                     │                  │
        ┌────────────┴────────┐  ┌──────┴──────────┐
        ▼                     ▼  ▼                 ▼
  ┌─────────────┐       ┌──────────────┐    ┌────────────┐
  │   FLINK     │       │    SPARK     │    │   BATCH    │
  │  6 Writers  │       │  Streaming   │    │  Backfill  │
  │  (Real-time)│       │  (Iceberg)   │    │  (Backfill)│
  └──┬──────────┘       └──────┬───────┘    └─────┬──────┘
     │                        │                   │
     ├─────────┬──────────────┼───────────────────┤
     ▼         ▼              ▼                   ▼
  ┌─────────────────────────────────────────────────────────┐
  │        DATA LAYER (Real-time + Historical)              │
  ├──────────────────┬─────────────────┬────────────────────┤
  │ Redis Sentinel   │ InfluxDB        │ Iceberg (MinIO)    │
  │ HA (Cache)       │ (Time-series)   │ (Data Lake)        │
  │ - ticker:latest: │ - market_ticks  │ - coin_ticker      │
  │ - candle:1s:     │ - candles (1m)  │ - coin_trades      │
  │ - indicator:     │ - indicators    │ - coin_klines      │
  │ - orderbook:     │                 │                    │
  └──────────────────┴─────────────────┴────────────────────┘
     │                      │                      │
     └──────────────┬───────┴──────────┬───────────┘
                    ▼                  ▼
              ┌──────────────────────────────┐
              │    FASTAPI (Backend)         │
              │  - REST API (/api/*)         │
              │  - WebSocket /api/stream/*   │
              │  - Health check              │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │  NGINX (Reverse Proxy)       │
              │  - Frontend SPA              │
              │  - API Gateway               │
              └──────────────┬───────────────┘
                             ▼
              ┌──────────────────────────────┐
              │   REACT DASHBOARD            │
              │  - Candlestick Chart         │
              │  - Market & News             │
              │  - Order Book                │
              │  - Recent Trades             │
              └──────────────────────────────┘
```

---

## 📋 Yêu Cầu Hệ Thống

| Thành phần | Yêu cầu tối thiểu | Khuyến nghị | Ghi chú |
|:---|:---|:---|:---|
| **Docker** | 24.x | 25.x+ | Docker Desktop 4.x+ |
| **RAM** | 16 GB | 32 GB | Hiện deploy: t3a.2xlarge (32GB) |
| **Disk** | 50 GB | 100 GB | SSD gp3 tốt hơn |
| **CPU** | 4 cores | 8 cores | AMD/Intel, tối thiểu 2.5 GHz |

---

## 🚀 Khởi Động Nhanh

### 1️⃣ Chuẩn Bị Môi Trường

```bash
# Tạo file .env từ template
cp .env.example .env

# Mở và chỉnh sửa các giá trị trong .env:
# - INFLUX_ADMIN_PASSWORD
# - MINIO_ROOT_PASSWORD
# - POSTGRES_PASSWORD
# - JWT_SECRET
```

### 2️⃣ Khởi Động Services

```bash
# Build & start toàn bộ 21 services
docker compose up -d --build

# Kiểm tra trạng thái
docker compose ps
```

### 3️⃣ Submit Streaming Jobs

**Flink Streaming (6 writers → Redis Sentinel HA + InfluxDB):**
```bash
docker exec flink-jobmanager flink run -d -py /app/src/processing/pipeline.py --pyFiles /app/src
```

**Spark Streaming (3 queries → Iceberg):**
```bash
docker exec -d spark-master /opt/spark/bin/spark-submit \
  --master spark://spark-master:7077 \
  --packages "org.apache.spark:spark-sql-kafka-0-10_2.12:3.5.5,org.apache.spark:spark-avro_2.12:3.5.5,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.1,org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262" \
  --conf spark.cores.max=2 \
  /app/src/lakehouse/pipeline.py
```

### 4️⃣ Backfill Dữ Liệu Lịch Sử (Optional)

```bash
# Kéo 90 ngày dữ liệu lịch sử từ Binance
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode populate --days 90
```

---

## 🌐 Truy Cập Services

| Service | URL | Username | Password | Ghi chú |
|:---|:---|:---|:---|:---|
| **Frontend** | http://localhost:3004 | — | — | React Dashboard |
| **FastAPI** | http://localhost:8000 | — | — | REST API + WebSocket |
| **InfluxDB** | http://localhost:8086 | `$INFLUX_ADMIN_USER` | `$INFLUX_ADMIN_PASSWORD` | Time-series DB |
| **MinIO** | http://localhost:9001 | `$MINIO_ROOT_USER` | `$MINIO_ROOT_PASSWORD` | Object Storage |
| **PostgreSQL** | localhost:5432 | `$POSTGRES_USER` | `$POSTGRES_PASSWORD` | Metadata DB |
| **Flink UI** | http://localhost:8081 | — | — | Job Management |
| **Spark Master** | http://localhost:8082 | — | — | Cluster Manager |
| **Trino** | http://localhost:8083 | (any) | — | SQL Query Engine |
| **Dagster** | http://localhost:3000 | — | — | Orchestration |
| **Redis Sentinel** | localhost:6379 | — | — | Cache Layer |
| **Kafka** | localhost:9092 | — | — | Message Broker |

---

## 🔗 API Reference

### Market Data Endpoints

```bash
# Health Check
curl http://localhost:8000/api/health

# Get All Symbols
curl http://localhost:8000/api/symbols

# Get Current Price (Real-time)
curl http://localhost:8000/api/ticker
curl http://localhost:8000/api/ticker/BTCUSDT

# Get Candles (OHLCV)
curl "http://localhost:8000/api/klines?symbol=BTCUSDT&interval=1m&limit=100"

# Get Historical Candles
curl "http://localhost:8000/api/klines/historical?symbol=BTCUSDT&interval=1h&startTime=1704067200000&endTime=1706745600000&limit=500"

# Get Order Book
curl http://localhost:8000/api/orderbook/BTCUSDT

# Get Recent Trades
curl http://localhost:8000/api/trades/BTCUSDT?limit=50

# Get Technical Indicators
curl http://localhost:8000/api/indicators/BTCUSDT

# Get Market Overview
curl http://localhost:8000/api/market/overview
curl http://localhost:8000/api/market/gainers?limit=10
curl http://localhost:8000/api/market/losers?limit=10

# Get Latest News
curl "http://localhost:8000/api/news/latest?limit=20&hours=24"
```

### WebSocket Endpoint

```javascript
// Connect to real-time stream
const ws = new WebSocket('ws://localhost:8000/api/stream?symbol=BTCUSDT&interval=1s');

ws.onmessage = (event) => {
    const candle = JSON.parse(event.data);
    console.log('New candle:', candle);
    // {time, open, high, low, close, volume}
};
```

---

## 🛠️ Các Lệnh Thường Dùng

### Quản Lý Services

```bash
# Xem trạng thái tất cả services
docker compose ps

# View logs của service cụ thể
docker compose logs -f fastapi
docker compose logs -f flink-jobmanager
docker compose logs -f spark-master

# Restart service
docker compose restart fastapi

# Stop/Start toàn bộ
docker compose stop
docker compose start

# Xoá hết (⚠️ mất data)
docker compose down -v
```

### Kiểm Tra Dữ Liệu

```bash
# Redis Sentinel HA
docker exec keydb redis-cli HGETALL "ticker:latest:BTCUSDT"
docker exec keydb redis-cli KEYS "candle:*"
docker exec keydb redis-cli HGETALL "indicator:latest:BTCUSDT"

# InfluxDB
docker exec influxdb influx query 'from(bucket:"crypto") |> range(start: -1h)'

# Iceberg (via Trino)
docker exec trino trino --execute "SELECT count(*) FROM iceberg.crypto_lakehouse.coin_ticker"
docker exec trino trino --execute "SELECT * FROM iceberg.crypto_lakehouse.coin_klines LIMIT 10"

# Kafka HA
docker exec kafka /opt/kafka/bin/kafka-topics.sh --list --bootstrap-server kafka:9092
docker exec kafka /opt/kafka/bin/kafka-console-consumer.sh --topic crypto_ticker --bootstrap-server kafka:9092 --max-messages 5 --from-beginning
```

### Monitoring

```bash
# System resource usage
docker stats

# Check network connectivity
docker exec fastapi curl http://redis:6379
docker exec fastapi curl http://influxdb:8086/ready
```

---

## 📊 Resource Allocation

| Service | RAM (Config) | CPU | Notes |
|:---|:---|:---|:---|
| **Flink JobManager** | 2.3 GB | 0.5 | Scheduler + driver |
| **Flink TaskManager** | 6.0 GB | 3.0 | 2 slots, parallelism=1 |
| **Spark Master** | 1.0 GB | 0.3 | Light weight |
| **Spark Worker** | 4.0 GB | 0.1 | 2 cores max |
| **Kafka** | 1.5 GB | 2.0 | KRaft mode |
| **InfluxDB** | 1.5 GB | 0.5 | Time-series |
| **Redis Sentinel** | 1.0 GB | 0.2 | In-memory cache |
| **MinIO** | 1.0 GB | 0.1 | Object storage |
| **PostgreSQL** | 512 MB | 0.1 | Metadata |
| **Trino** | 1.0 GB | 0.5 | Query engine |
| **FastAPI** | 256 MB | 0.3 | Serving layer |
| **Nginx** | 128 MB | 0.1 | Reverse proxy |
| **Dagster** | 1.5 GB | 0.5 | Orchestration |
| **Producer** | 256 MB | 1.5 | WebSocket client |
| **Others** | — | — | |
| **TOTAL** | **~25 GB** | **~9.4** | Deployed on t3a.2xlarge |

> **Tip:** Có thể tắt Trino nếu máy chỉ có 16GB RAM: `docker compose stop trino`

---

## 🆘 Troubleshooting

### Frontend không load

```bash
# Kiểm tra Nginx logs
docker compose logs nginx

# Kiểm tra FastAPI backend
curl http://localhost:8000/api/health

# Clear browser cache (Ctrl+Shift+R hoặc Cmd+Shift+R)
```

### WebSocket connection failed

```bash
# Kiểm tra FastAPI running
docker compose ps fastapi

# Kiểm tra port 8000 mở
netstat -an | grep 8000

# Restart FastAPI
docker compose restart fastapi
```

### Redis Sentinel HA không connect

```bash
# Kiểm tra Redis running
docker exec keydb redis-cli ping

# Kiểm tra Sentinel status
docker exec redis-sentinel redis-cli -p 26379 sentinel masters
```

### Flink job không chạy

```bash
# View Flink logs
docker compose logs flink-jobmanager
docker compose logs flink-taskmanager

# View Flink Web UI
# http://localhost:8081

# Resubmit job
docker exec flink-jobmanager flink run -d -py /app/src/processing/pipeline.py --pyFiles /app/src
```

---

## 📚 Tài Liệu Chi Tiết

- [DOCUMENTATION.md](DOCUMENTATION.md) - Chi tiết các component
- [DEPLOYMENT_PLAN.md](DEPLOYMENT_PLAN.md) - Hướng dẫn deploy production
- [LAKEHOUSE_TABLES.md](LAKEHOUSE_TABLES.md) - Schema bảng Iceberg
- [REDIS_SCHEMA.md](REDIS_SCHEMA.md) - Redis key structure
- [NEWS_SYSTEM.md](NEWS_SYSTEM.md) - Hệ thống tin tức
- [ROADMAP_DETAILED.md](ROADMAP_DETAILED.md) - Kế hoạch phát triển

---

## 🤝 Đóng Góp

Pull requests được chào đón! Để thay đổi lớn, vui lòng mở issue trước để thảo luận.

---

## 📄 License

MIT License - xem file `LICENSE` để chi tiết.

---

## 📞 Liên Hệ & Hỗ Trợ

Nếu gặp vấn đề hoặc có câu hỏi, vui lòng:
- Mở issue trên GitHub
- Kiểm tra logs: `docker compose logs -f <service>`
- Xem phần Troubleshooting ở trên

---

**Cập nhật lần cuối:** May 2026  
**Status:** ✅ Production Ready (Frontend + Backend hoạt động, scroll fixed, news feed đầy đủ)
