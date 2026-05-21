# LMView

[![Docker](https://img.shields.io/badge/Docker-27_dev_services-blue?logo=docker)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688?logo=fastapi)](backend/)
[![React](https://img.shields.io/badge/React-19.1-61DAFB?logo=react)](frontend/)
[![Apache Flink](https://img.shields.io/badge/Apache_Flink-1.18.1-E6522C?logo=apacheflink)](src/processing/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-3.9.0-231F20?logo=apachekafka)](docker-compose.yml)
[![Prometheus](https://img.shields.io/badge/Prometheus-2.45-E6522C?logo=prometheus)](config/prometheus.yml)
[![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana)](config/grafana/)

Real-time cryptocurrency technical-analysis platform built on Lambda Architecture.

---

## Highlights

- **Real-time candles** through Kafka, Flink, Redis Sentinel, FastAPI, and WebSocket.
- **Multi-timeframe charts**: `1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w`.
- **Exchange abstraction** with Binance as primary path and OKX integration under active hardening.
- **Lambda Architecture**: speed layer (Flink), batch/lakehouse layer (Spark/Iceberg), serving layer (FastAPI).
- **High availability infrastructure**: 3 Kafka brokers and Redis Sentinel with 1 master, 2 replicas, 3 Sentinels.
- **Market overview and news**: gold-table metrics, heatmaps, rankings, multi-source news and sentiment cache.
- **Trading UI**: lightweight-charts v5.2.0, drawing tools, replay mode, i18n, mock/API data mode.
- **Observability**: Prometheus, Grafana, Loki, exporters, 11 dashboards, alert rules.

---

## Overview

```text
Exchange WS/REST -> Producer -> Kafka -> Flink/Spark
                                  -> Redis + InfluxDB + Iceberg/MinIO
                                  -> FastAPI -> Nginx -> React
```

![Data Flow Diagram](docs/crypto.png)

LMView focuses on data engineering first, with a clean path for future AI/ML features: durable lakehouse data, low-latency Redis features, Trino analytics, and FastAPI serving boundaries.

---

## Usage

Primary app:

- Dev/prod Nginx: `https://localhost` after `make dev` (port 80 redirects to HTTPS; dev cert is self-signed).
- FastAPI docs: `http://localhost:8080/docs`.

API examples:

```bash
curl http://localhost:8080/api/health
curl "http://localhost:8080/api/klines?symbol=BTCUSDT&interval=1m&limit=100"
curl "http://localhost:8080/api/ticker/BTCUSDT"
curl "http://localhost:8080/api/news/latest?limit=10"
```

Web UIs:

| Service | URL |
|---|---|
| Frontend/Nginx | `https://localhost` |
| FastAPI docs | `http://localhost:8080/docs` |
| Flink | `http://localhost:8081` |
| Spark | `http://localhost:8082` |
| Trino | `http://localhost:8083` |
| InfluxDB | `http://localhost:8086` |
| Dagster | `http://localhost:3000` |
| Grafana | `http://localhost:3001` or `/grafana/` through Nginx |
| Prometheus | `http://localhost:9090` or `/prometheus/` through Nginx |
| MinIO Console | `http://localhost:9001` |

---

## Installation

Prerequisites:

- Docker Engine 24+ or Docker Desktop 4+.
- 32GB RAM recommended; 24GB minimum for full local stack.
- 100GB+ disk recommended.
- 8 CPU cores recommended.

Quick start:

```bash
git clone https://github.com/DoLong3304/LMView.git
cd LMView
cp .env.example .env
# Edit .env: set INFLUX_TOKEN, passwords, API keys, monitoring credentials.
make dev
```

Profiles:

| Command | Starts |
|---|---|
| `make dev` | Core dev stack, 27 services |
| `make monitoring` | Dev + Prometheus/Grafana/exporters |
| `make logging` | Dev + monitoring + Loki/Promtail |
| `make prod` | Production profile + monitoring + logging |

Optional backfill:

```bash
docker compose run --rm influx-backfill python /app/src/batch/backfill.py --mode populate --days 90
```

---

## Testing

```bash
make test
make test-all
make test-cov
```

Frontend checks:

```bash
cd frontend
npm run typecheck
npm run build
```

Current source contains 193 pytest test functions and 35 frontend hook test specs. `frontend/package.json` currently has no frontend test script.

---

## Documentation

| Document | Description |
|---|---|
| [SYSTEM.md](docs/SYSTEM.md) | Full system architecture, data flow, APIs, caveats |
| [CHANGELOG.md](docs/CHANGELOG.md) | Project history |
| [AGENTS.md](AGENTS.md) | AI agent workflow and coding rules |

---

## Authors

Built and maintained by D22 Fintech, PTIT students:

- [@DoLong3304](https://github.com/DoLong3304): Project Manager, DevOps and AI Engineer.
- [@StupidDuck64](https://github.com/StupidDuck64): Data Engineer.
- [@EzraaOP](https://github.com/EzraaOP): Frontend Developer.

---

Status: Active development
Version: 0.12.3
License: Not specified in this repository
