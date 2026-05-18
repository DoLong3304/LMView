# 📊 LMView

[![Docker](https://img.shields.io/badge/Docker-27_Services-blue?logo=docker)](docker-compose.core.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi)](backend/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react)](frontend/)
[![Apache Flink](https://img.shields.io/badge/Apache_Flink-1.18.1-E6522C?logo=apacheflink)](src/processing/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-3.9.0-231F20?logo=apachekafka)](docker-compose.core.yml)
[![Prometheus](https://img.shields.io/badge/Prometheus-2.45-E6522C?logo=prometheus)](docker-compose.monitoring.yml)
[![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana)](docker-compose.monitoring.yml)

> *Real-time cryptocurrency technical analysis platform built on Lambda Architecture.*

---

## 🌟 Highlights

- **Sub-second latency** — Flink stream processing delivers live OHLCV data in <1s
- **Multi-timeframe charts** — 1s, 1m, 5m, 15m, 1h, 4h, 1d, 1w with TradingView-style UI
- **~400 trading pairs** — All USDT spot pairs from Binance, streamed in real-time
- **Lambda Architecture** — Speed layer (Flink) + Batch layer (Spark) + Serving layer (FastAPI)
- **High Availability** — Kafka 3-node KRaft cluster, Redis Sentinel (1 master + 2 replicas + 3 sentinels)
- **Full observability** — Prometheus + Grafana (7 dashboards) + Loki centralized logging
- **12 drawing tools** — Trendlines, Fibonacci, horizontal lines, and more
- **Technical indicators** — SMA, EMA, RSI, MFI with real-time calculation

---

## ℹ️ Overview

**LMView** is a data engineering platform that streams cryptocurrency market data from exchanges, processes it through parallel real-time and batch pipelines, and serves it via a modern web interface with TradingView-style charting.

The system focuses on two engineering disciplines:
- **Data Engineering** — Lambda Architecture with Kafka, Flink, Spark, InfluxDB, Iceberg, and Redis for multi-layered data processing and storage
- **AI Engineering** — Foundation for ML/DL price prediction models and AI-driven technical analysis (roadmap)

### Architecture

```
Exchange WebSocket → Kafka HA (3 brokers) → Flink (speed) / Spark (batch)
                                                    ↓
                                    Redis (hot) / InfluxDB (warm) / Iceberg (cold)
                                                    ↓
                                          FastAPI → Nginx → React 19 SPA
```
![Data Flow Diagram](docs/crypto.png)
### ✍️ Author

Built and maintained by D22 Fintech, PTIT students:
- [@DoLong3304](https://github.com/DoLong3304):  Project Manager, DevOps and AI Engineer.
- [@StupidDuck64](https://github.com/StupidDuck64):  Data Engineer.
- [@EzraaOP](https://github.com/EzraaOP):  Frontend Developer.

---

## 🚀 Usage

Once running, access the platform at **http://localhost**:

- **Real-time charts** with live WebSocket price updates
- **Multi-timeframe** switching (1s to 1w)
- **Order book** and **recent trades** panels
- **Historical browsing** with date range picker and scroll-left loading
- **Drawing tools** for technical analysis
- **System health** monitoring card

### API Examples

```bash
# Live ticker
curl http://localhost:8080/api/ticker/BTCUSDT | jq

# OHLCV candles
curl "http://localhost:8080/api/klines?symbol=BTCUSDT&interval=1m&limit=100" | jq

# Health check
curl http://localhost:8080/api/health | jq
```

### Web UIs

| Service | URL | Credentials |
|---|---|---|
| Frontend | http://localhost | — |
| FastAPI Docs | http://localhost:8080/docs | — |
| Grafana | http://localhost/grafana/ | admin/admin |
| Prometheus | http://localhost/prometheus/ | MONITORING_USER/PASSWORD |
| Loki | http://localhost/loki/ | MONITORING_USER/PASSWORD |
| Flink | http://localhost:8081 | — |
| Dagster | http://localhost:3000 | — |
| MinIO | http://localhost:9001 | minioadmin/minioadmin |

---

## ⬇️ Installation

### Prerequisites

- **Docker Engine** >= 24.x or **Docker Desktop** >= 4.x
- **RAM:** 32GB recommended (24GB minimum)
- **Disk:** 100GB+ free space
- **CPU:** 8 cores recommended

### Quick Start

```bash
# Clone
git clone https://github.com/DoLong3304/LMView.git
cd LMView

# Configure environment
cp .env.example .env
# Edit .env — set INFLUX_TOKEN, passwords, etc.

# Start core services in dev mode
make dev

# Open http://localhost
```

### Startup Profiles

| Command | Services | RAM |
|---|---|---|
| `make dev` | Core + dev containers (hot-reload, localhost) | ~17GB |
| `make monitoring` | + Prometheus, Grafana, exporters | ~18GB |
| `make logging` | + Loki, Promtail | ~18.8GB |
| `make prod` | Core + prod containers + monitoring + logging | ~18.8GB |

### Backfill Historical Data (Optional)

```bash
# Populate 90 days of 1m candles (~30-60 min)
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode populate --days 90
```

---

## 🧪 Testing

```bash
make test          # Unit + integration tests
make test-all      # All 161 tests
make test-cov      # With coverage report
```

---

## 📚 Documentation

| Document | Description |
|---|---|
| [SYSTEM.md](docs/SYSTEM.md) | Complete system documentation — architecture, data flow, tech stack |
| [CHANGELOG.md](docs/CHANGELOG.md) | Project change history |
| [AGENTS.md](docs/AGENTS.md) | AI agent coding instructions |

---

## 💭 Feedback and Contributing

Open an [issue](https://github.com/DoLong3304/LMView/issues) for bug reports or feature requests.

See [AGENTS.md](docs/AGENTS.md) for coding guidelines if contributing with AI assistance.

---

**Status:** ✅ Active Development
**Version:** 0.11.0
**License:** [MIT](LICENSE)
