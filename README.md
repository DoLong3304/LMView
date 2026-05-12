# Lambda Architecture - TradingView Style Platform 📊

[![Docker](https://img.shields.io/badge/Docker-27_Services-blue?logo=docker)](docker-compose.core.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](backend/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](frontend/)
[![Apache Flink](https://img.shields.io/badge/Apache_Flink-1.18.1-E6522C?logo=apacheflink)](src/processing/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-3.9.0-231F20?logo=apachekafka)](docker-compose.core.yml)
[![Prometheus](https://img.shields.io/badge/Prometheus-2.45-E6522C?logo=prometheus)](docker-compose.monitoring.yml)
[![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana)](docker-compose.monitoring.yml)

> **Enterprise-grade real-time crypto trading platform** with Multi-Exchange HA, News Sentiment, and Full Observability Stack

Real-time cryptocurrency data platform streaming from **Binance + OKX**, processing with **Flink + Spark** using **Lambda Architecture** (speed + batch layers), serving via **FastAPI + React** with TradingView-style charts.

---

## 🎯 Key Features

- ✅ **Multi-Exchange HA**: Binance + OKX Active-Active with mid-price aggregation
- ✅ **News Sentiment**: CryptoPanic API + VADER sentiment analysis
- ✅ **Real-time Processing**: Apache Flink streaming (< 1s latency)
- ✅ **Batch Processing**: Apache Spark for historical data
- ✅ **Full Observability**: Prometheus + Grafana + Loki (7 dashboards, 47+ panels)
- ✅ **TradingView Charts**: 12 drawing tools, multi-timeframe support
- ✅ **Profile-Based Startup**: Safe for 32GB RAM (17GB core, 18GB with monitoring)

---

## 🏗️ System Architecture

### Data Flow

```
┌─────────────────────────────────────────────────────────────────┐
│                      INGESTION LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│  Binance WebSocket  →  Kafka (crypto_ticker, crypto_kline)      │
│  OKX WebSocket      →  Kafka (crypto_ticker, crypto_kline)      │
│  CryptoPanic API    →  Kafka (crypto_news_sentiment)            │
│  Producer: Python 3.11 + websockets                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                    PROCESSING LAYER                              │
├─────────────────────────────────────────────────────────────────┤
│  Apache Flink 1.18.1 (PyFlink)                                  │
│    ├─ Speed Layer: Real-time aggregation                        │
│    ├─ Writers: KeyDB + InfluxDB                                 │
│    └─ Latency: < 1 second                                       │
│                                                                  │
│  Apache Spark 3.5 (PySpark)                                     │
│    ├─ Batch Layer: Historical processing                        │
│    ├─ Writers: Iceberg (MinIO)                                  │
│    └─ Schedule: Dagster orchestration                           │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                     STORAGE LAYER                                │
├─────────────────────────────────────────────────────────────────┤
│  KeyDB (Redis-compatible)                                       │
│    ├─ Hot cache: 1s, 1m, 5m candles                             │
│    ├─ TTL: 1-7 days                                             │
│    └─ Sentinel HA: 1 master + 2 replicas                        │
│                                                                  │
│  InfluxDB 2.7 (Time-series)                                     │
│    ├─ Warm storage: 1m-1w candles                               │
│    ├─ Retention: 90 days                                        │
│    └─ Downsampling: 1m→5m→15m→1h→4h→1d→1w                       │
│                                                                  │
│  Iceberg 1.5.2 + MinIO (Data Lake)                              │
│    ├─ Cold storage: Long-term historical                        │
│    ├─ Format: Parquet                                           │
│    └─ Query: Trino SQL                                          │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                      SERVING LAYER                               │
├─────────────────────────────────────────────────────────────────┤
│  FastAPI 0.115+ (Python 3.11)                                   │
│    ├─ REST API: /api/ticker, /api/klines, /api/historical       │
│    ├─ WebSocket: Real-time price updates                        │
│    └─ Multi-Exchange: Aggregated mid-price                      │
│                                                                  │
│  React 19 + TypeScript 5.7 (Frontend)                           │
│    ├─ TradingView-style charts (lightweight-charts)             │
│    ├─ 12 drawing tools (trendline, fib, etc.)                   │
│    └─ Multi-timeframe: 1m, 5m, 15m, 1h, 4h, 1d, 1w              │
│                                                                  │
│  Nginx 1.27 (Reverse Proxy)                                     │
│    ├─ Rate limiting: 30 req/s API, 5 req/s WebSocket           │
│    └─ SSL/TLS ready                                             │
└─────────────────────────────────────────────────────────────────┘
                              ↓
┌─────────────────────────────────────────────────────────────────┐
│                   OBSERVABILITY LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│  Prometheus 2.45 (Metrics)                                      │
│    ├─ Scrape: FastAPI, Kafka, Flink, Node                       │
│    ├─ Retention: 30 days                                        │
│    └─ Storage: ~10GB                                            │
│                                                                  │
│  Grafana 10.2 (Visualization)                                   │
│    ├─ 7 Dashboards (3 metrics + 4 logs)                         │
│    ├─ 47+ Panels                                                │
│    └─ 8 Alerting Rules                                          │
│                                                                  │
│  Loki 2.9 + Promtail (Logging)                                  │
│    ├─ Centralized logs from 27 containers                       │
│    ├─ Retention: 7 days                                         │
│    └─ Storage: ~50GB                                            │
└─────────────────────────────────────────────────────────────────┘
```

---

## 📦 Services Overview

### Core Services (21 services, 17GB RAM)

| Service | Technology | Port | Purpose |
|---------|------------|------|---------|
| **producer** | Python 3.11 | - | WebSocket → Kafka (Binance + OKX) |
| **kafka-1,2,3** | Kafka 3.9.0 | 9092-9094 | Message broker (KRaft mode) |
| **schema-registry** | Apicurio 2.6.2 | 8081 | Avro schema management |
| **flink-jobmanager** | Flink 1.18.1 | 8081 | Stream processing coordinator |
| **flink-taskmanager** | Flink 1.18.1 | - | Stream processing worker |
| **spark-master** | Spark 3.5 | 8082 | Batch processing coordinator |
| **spark-worker** | Spark 3.5 | - | Batch processing worker |
| **redis-master** | KeyDB | 6379 | Hot cache (1s, 1m, 5m candles) |
| **redis-replica-1,2** | KeyDB | 6380-6381 | Cache replicas |
| **redis-sentinel-1,2,3** | KeyDB | 26379-26381 | HA monitoring |
| **influxdb** | InfluxDB 2.7 | 8086 | Time-series DB (1m-1w candles) |
| **minio** | MinIO | 9000, 9001 | S3-compatible object storage |
| **trino** | Trino 442 | 8083 | Federated SQL query engine |
| **postgres** | PostgreSQL 16 | 5432 | Metadata DB (Dagster) |
| **dagster-daemon** | Dagster | - | Job scheduler |
| **dagster-webserver** | Dagster | 3000 | Orchestration UI |
| **fastapi** | FastAPI 0.115 | 8000 | REST + WebSocket API |
| **frontend** | React 19 | 3001 | SPA (built with Vite) |
| **nginx** | Nginx 1.27 | 80, 443 | Reverse proxy |

### Monitoring Services (4 services, +1GB RAM)

| Service | Technology | Port | Purpose |
|---------|------------|------|---------|
| **prometheus** | Prometheus 2.45 | 9090 | Metrics collection & storage |
| **grafana** | Grafana 10.2 | 3001 | Dashboards & alerting |
| **kafka-exporter** | Kafka Exporter 1.7 | 9308 | Kafka metrics exporter |
| **node-exporter** | Node Exporter 1.6 | 9100 | Host metrics exporter |

### Logging Services (2 services, +768MB RAM)

| Service | Technology | Port | Purpose |
|---------|------------|------|---------|
| **loki** | Loki 2.9 | 3100 | Log aggregation & storage |
| **promtail** | Promtail 2.9 | 9080 | Log collection from containers |

**Total: 27 services, 18.8GB RAM**

---

## 🗄️ Data Tables

### KeyDB Keys (Hot Cache, 1-7 days TTL)

```
ticker:latest:{exchange}:{symbol}     # Latest ticker (Binance/OKX)
candle:1s:{exchange}:{symbol}         # 1-second candles (1d TTL)
candle:1m:{exchange}:{symbol}         # 1-minute candles (7d TTL)
candle:5m:{exchange}:{symbol}         # 5-minute candles (7d TTL)
orderbook:{exchange}:{symbol}         # Order book snapshot
```

### InfluxDB Measurements (90 days retention)

```sql
-- Ticker data
ticker
  tags: exchange, symbol
  fields: price, volume, change_24h

-- Candle data (multi-timeframe)
kline_1m, kline_5m, kline_15m, kline_1h, kline_4h, kline_1d, kline_1w
  tags: exchange, symbol
  fields: open, high, low, close, volume, trade_count

-- Order book
depth
  tags: exchange, symbol
  fields: bids, asks, spread

-- Trades
trade
  tags: exchange, symbol
  fields: price, quantity, side
```

### Iceberg Tables (Long-term storage)

```sql
-- Bronze Layer (Raw data)
bronze.ticker       -- Raw ticker from all exchanges
bronze.kline        -- Raw klines from all exchanges
bronze.trade        -- Raw trades
bronze.depth        -- Raw order book
bronze.news         -- Raw news sentiment

-- Silver Layer (Cleaned & unified)
silver.ticker_unified          -- Deduplicated, mid-price calculated
silver.kline_multi_timeframe   -- All timeframes (1m-1w)
silver.trade_aggregated        -- Aggregated trades

-- Gold Layer (Business metrics)
gold.market_overview           -- Top gainers/losers, market stats
gold.symbol_stats_daily        -- Daily OHLCV, volatility
gold.sector_performance        -- Sector-level aggregations
```

---

## 🚀 Quick Start

### Prerequisites

- **Docker Engine** >= 24.x or Docker Desktop >= 4.x
- **RAM**: 32GB recommended (minimum 24GB)
- **Disk**: 100GB+ free space
- **CPU**: 8 cores recommended (minimum 4 cores)

### Installation

```bash
# 1. Clone repository
git clone <repository-url>
cd Lambda-Architecture-for-TradingView-Style-Platform

# 2. Create environment file
cp .env.example .env
# Edit .env and set your API keys and passwords

# 3. Start services (choose profile)
```

### Profile-Based Startup

**Option 1: Core Only (17GB RAM) - Daily Development**
```bash
docker compose --profile core up -d
```

**Option 2: Core + Monitoring (18GB RAM) - Performance Monitoring**
```bash
docker compose --profile core --profile monitoring up -d
```

**Option 3: Full Stack (18.8GB RAM) - Debugging with Logs**
```bash
docker compose --profile all up -d
```

**Option 4: Custom Combinations**
```bash
# Core + Logging only
docker compose --profile core --profile logging up -d

# Monitoring + Logging only (for testing observability)
docker compose --profile monitoring --profile logging up -d
```

### Submit Processing Jobs

```bash
# Submit Flink streaming job
docker compose -f docker-compose.core.yml exec flink-jobmanager \
  flink run -d -py /app/src/processing/pipeline.py --pyFiles /app/src

# Submit Spark streaming job (Iceberg writer)
docker compose -f docker-compose.core.yml exec spark-master \
  spark-submit --master spark://spark-master:7077 \
  /app/src/lakehouse/pipeline.py

# Verify jobs are running
docker compose -f docker-compose.core.yml exec flink-jobmanager flink list
```

---

## 🔧 Common Operations

### Check System Status

```bash
# Show all running containers
docker compose ps

# Check specific service logs
docker logs <service-name> -f

# Check Flink job status
docker compose exec flink-jobmanager flink list

# Check Kafka topics
docker compose exec kafka-1 \
  /opt/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list
```

### Access Web UIs

| Service | URL | Credentials |
|---------|-----|-------------|
| **Frontend** | http://localhost | - |
| **FastAPI Docs** | http://localhost:8080/docs | - |
| **Grafana** | http://localhost:3001 | admin/admin |
| **Prometheus** | http://localhost:9090 | - |
| **Flink UI** | http://localhost:8081 | - |
| **Spark UI** | http://localhost:8082 | - |
| **Trino UI** | http://localhost:8083 | - |
| **Dagster UI** | http://localhost:3000 | - |
| **MinIO Console** | http://localhost:9001 | minioadmin/minioadmin |
| **InfluxDB** | http://localhost:8086 | admin/password123 |

### API Examples

```bash
# Get ticker (aggregated from Binance + OKX)
curl http://localhost:8080/api/ticker/BTCUSDT | jq

# Get ticker from specific exchange
curl "http://localhost:8080/api/ticker/BTCUSDT?exchange=binance" | jq
curl "http://localhost:8080/api/ticker/BTCUSDT?exchange=okx" | jq

# Get candles
curl "http://localhost:8080/api/klines?symbol=BTCUSDT&interval=1m&limit=100" | jq

# Get historical data
curl "http://localhost:8080/api/historical?symbol=BTCUSDT&interval=1h&start_time=1715443200000&end_time=1715529600000" | jq

# Health check
curl http://localhost:8080/api/health | jq
```

### Stop Services

```bash
# Stop all services
docker compose --profile all down

# Stop specific profile
docker compose --profile core down
docker compose --profile monitoring down
docker compose --profile logging down

# Stop and remove volumes (CAUTION: deletes data)
docker compose --profile all down -v
```

### Restart Services

```bash
# Restart all services
docker compose --profile all restart

# Restart specific service
docker compose restart <service-name>

# Rebuild and restart
docker compose --profile core up -d --build <service-name>
```

---

## 📊 Monitoring & Observability

### Grafana Dashboards (7 total)

**Metrics Dashboards:**
1. **System Overview** - FastAPI metrics, latency, error rate, memory
2. **Kafka Health** - Consumer lag, brokers, throughput, partitions
3. **Flink Monitoring** - Job uptime, memory, checkpoints, throughput

**Log Dashboards:**
4. **Centralized Logs** - Overview of all services (6 panels)
5. **FastAPI Logs** - API debugging (6 panels)
6. **Kafka Logs** - Messaging monitoring (7 panels)
7. **Flink Logs** - Stream processing (8 panels)

### Alerting Rules (8 total)

**Critical Alerts:**
- Flink job restarting
- Kafka broker down
- API error rate > 5%
- System memory > 90%

**Warning Alerts:**
- Kafka consumer lag > 10,000
- API P95 latency > 1s
- Flink heap memory > 90%
- System CPU > 90%

### Log Queries (LogQL)

```logql
# All errors
{project="core"} |= "ERROR"

# FastAPI errors
{container="fastapi"} |= "ERROR" or |= "Exception"

# Kafka connection issues
{container=~"kafka-.*"} |~ "(?i)connection|timeout"

# Flink exceptions
{container=~"flink-.*"} |= "Exception"

# Error rate by container
sum by (container) (rate({project="core"} |= "ERROR" [1m]))
```

---

## 🧪 Testing

```bash
# Run unit tests
PYTHONPATH=. python -m pytest tests/unit/ -v

# Run integration tests
PYTHONPATH=. python -m pytest tests/integration/ -v

# Run all tests
PYTHONPATH=. python -m pytest tests/ -v

# Run with coverage
PYTHONPATH=. python -m pytest tests/ --cov=backend --cov-report=term-missing
```

---

## 🛠️ Troubleshooting

### High RAM Usage

```bash
# Stop logging stack first
make stop-logs

# Check RAM usage
make status

# If still high, stop monitoring
make stop-monitoring
```

### Service Not Starting

```bash
# Check logs
docker logs <service-name>

# Restart service
docker compose -f docker-compose.core.yml restart <service-name>

# Rebuild if needed
docker compose -f docker-compose.core.yml up -d --build <service-name>
```

### Kafka Consumer Lag

```bash
# Check consumer groups
docker compose -f docker-compose.core.yml exec kafka-1 \
  /opt/kafka/bin/kafka-consumer-groups.sh \
  --bootstrap-server localhost:9092 \
  --describe --all-groups

# If lag > 10000, check Flink job
docker logs flink-taskmanager | grep -i error
```

### KeyDB Connection Issues

```bash
# Check Redis Sentinel
docker compose -f docker-compose.core.yml exec redis-sentinel-1 \
  redis-cli -p 26379 SENTINEL masters

# Check master
docker compose -f docker-compose.core.yml exec redis-master redis-cli PING
```

---

## 📚 Documentation

- **[INDEX.md](docs/INDEX.md)** - Documentation navigation
- **[COMPLETE_GUIDE.md](docs/COMPLETE_GUIDE.md)** - All-in-one guide
- **[ROADMAP.md](docs/ROADMAP.md)** - Production roadmap
- **[DEPLOYMENT_GUIDE.md](docs/DEPLOYMENT_GUIDE.md)** - Deployment guide
- **[OBSERVABILITY_PLAN.md](docs/OBSERVABILITY_PLAN.md)** - Monitoring setup
- **[LOGQL_REFERENCE.md](docs/LOGQL_REFERENCE.md)** - Log query reference
- **[TRACKING.md](docs/TRACKING.md)** - Implementation history

---

## 🗺️ Roadmap

### Phase 1: Medallion Architecture (3-4 weeks)
- Bronze/Silver/Gold data layers
- Structured data lake

### Phase 2: Multi-Timeframe Storage (2-3 weeks)
- Store 1m, 5m, 15m, 1h, 4h, 1d, 1w
- Historical date picker

### Phase 3: Production Hardening (3-4 weeks) - CRITICAL
- Late data handling
- KeyDB failover
- Kafka optimization (100 partitions)
- WebSocket pooling (10K connections)

### Phase 4-6: Scalability, Cloud, Advanced Features
- Caching layer
- S3 for Iceberg
- Advanced analytics

**Timeline:** 4-5 months to full production

---

## 📝 License

[Your License Here]

---

## 🤝 Contributing

[Contributing Guidelines]

---

## 📧 Contact

[Your Contact Information]

---

**Built with ❤️ using Lambda Architecture**

**Status:** ✅ Production-Ready MVP  
**Version:** 2.0  
**Last Updated:** 2026-05-11
