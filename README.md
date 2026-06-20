# LMView

[![Docker](https://img.shields.io/badge/Docker-29_dev_services-blue?logo=docker)](docker-compose.yml)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115.6-009688?logo=fastapi)](backend/)
[![React](https://img.shields.io/badge/React-19.1-61DAFB?logo=react)](frontend/)
[![Apache Flink](https://img.shields.io/badge/Apache_Flink-1.18.1-E6522C?logo=apacheflink)](src/processing/)
[![Apache Kafka](https://img.shields.io/badge/Apache_Kafka-3.9.0-231F20?logo=apachekafka)](docker-compose.yml)
[![Prometheus](https://img.shields.io/badge/Prometheus-2.45-E6522C?logo=prometheus)](config/prometheus.yml)
[![Grafana](https://img.shields.io/badge/Grafana-10.2-F46800?logo=grafana)](config/grafana/)

Real-time cryptocurrency technical-analysis platform built on Lambda Architecture.

---

## Highlights

- **Live market data** from Binance WebSocket through Kafka, Flink, Redis Sentinel, InfluxDB, FastAPI, and WebSocket streaming.
- **Multi-timeframe charts**: `1s`, `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, `1w` with TradingView-like appearance.
- **Drawing tools**: trendline, horizontal ray, vertical line, fibonacci retracement, rectangle, circle, arrow, text.
- **Advanced chart types**: Heikin Ashi, Renko, Line Break, Kagi transforms on render.
- **Pattern recognition engine** and **alert service** (standalone, ready for UI integration).
- **Enhanced watchlist** with activity score, trend detection, RSI filter, and sortable columns.
- **Market screener** with search, price/volume/change/RSI filters and multi-column sort.
- **Market overview** with gold-table metrics, heatmaps, rankings, news, and sentiment.
- **Multi-chart layout system** (standalone, ready for integration).
- **Exchange abstraction**: Binance primary, OKX opt-in.
- **Lakehouse analytics**: Spark, Iceberg on MinIO, PostgreSQL catalog, Trino.
- **High availability**: 3 Kafka brokers, Redis Sentinel (1 master, 2 replicas, 3 sentinels).
- **AI Ask/Interact Helper**: centralized `ai_service` orchestration, local/API/none provider routing, approved-only pgvector RAG, Markdown chat, and reusable function actions.
- **Observability**: Prometheus, Grafana, Loki, 22 dashboards, 48 alert rules.
- **Docker Swarm deployment**: 2-node EC2 cluster with EFS shared storage.

---

## Quick Start

```bash
git clone https://github.com/DoLong3304/LMView.git
cd LMView
cp .env.example .env
# Edit .env: set tokens, passwords, API keys
make dev
```

Then open `http://localhost`.

---

## Architecture

```
Exchange WebSockets / REST
  -> Producer (Kafka + Direct Redis)
       -> Kafka: crypto_ticker, crypto_klines, crypto_trades, crypto_depth
       -> Redis: trade:latest (real-time primary), ticker/candle (batch-flushed)
       -> Flink: Redis + InfluxDB writers, 1s->1m aggregation
  -> Spark: Iceberg lakehouse (Bronze/Silver/Gold)
  -> FastAPI: REST + WebSocket serving
  -> Nginx: reverse proxy
  -> React: trading dashboard
```

### Real-Time Data Flow

| Stage | Source | Update Rate | Latency |
|---|---|---|---|
| Exchange → Producer | Binance WS | per event | ~50-200ms |
| Producer → Kafka | `src/producer/main.py` | per event | ~5-50ms |
| Kafka → Flink | Flink Kafka consumer | per event | ~100-500ms |
| Flink → Redis | `keydb_kline.py` (BATCH) | 500ms flush | ~500-1000ms |
| Producer → Redis | `redis_writer.py` (trade only) | per trade | ~50ms |
| Redis → WebSocket | 50ms poll loop | 50ms | ~50ms |
| WebSocket → Frontend | `subscribeAllTimeframes` | 50ms | ~10-30ms |

**Current target**: < 300ms end-to-end for real-time candle updates.

---

## Service URLs

| Service | URL | Notes |
|---|---|---|
| Frontend | `http://localhost` | Dev: plain HTTP on port 80 |
| FastAPI | `http://localhost:8080/docs` | API docs |
| Flink | `http://localhost:8081` | JobManager UI |
| Spark | `http://localhost:8082` | Master UI |
| Trino | `http://localhost:8083` | Query engine UI |
| InfluxDB | `http://localhost:8086` | Warm time-series store |
| Dagster | `http://localhost:3000` | Orchestration UI |
| Grafana | `http://localhost:3001` | Also `/grafana/` through Nginx |
| Prometheus | `http://localhost:9090` | Also `/prometheus/` through Nginx |
| MinIO | `http://localhost:9001` | Object storage console |

---

## API Examples

```bash
# Health check
curl http://localhost:8080/api/health

# Klines (candles)
curl "http://localhost:8080/api/klines?symbol=BTCUSDT&interval=1h&limit=100"

# Ticker
curl "http://localhost:8080/api/ticker/BTCUSDT"
curl "http://localhost:8080/api/ticker"

# Order book
curl "http://localhost:8080/api/orderbook/BTCUSDT/summary"

# WebSocket stream (all timeframes)
# ws://localhost:8080/api/stream/all?symbol=BTCUSDT

# Indicators
curl "http://localhost:8080/api/indicators/supported"
curl "http://localhost:8080/api/indicators/BTCUSDT?interval=1h"

# Screener
curl "http://localhost:8080/api/screener/symbols?trend=bullish"
curl "http://localhost:8080/api/screener/watchlist"

# Market overview
curl "http://localhost:8080/api/market/overview"
curl "http://localhost:8080/api/market/rankings/gainers"

# News
curl "http://localhost:8080/api/news/latest?limit=5"

# AI Helper (auth required)
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/ai/health
curl -H "Authorization: Bearer <token>" http://localhost:8080/api/ai/actions/catalog
curl -X POST -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"ask","message":"What is the RSI for BTCUSDT?"}' \
  http://localhost:8080/api/ai/chat
```

---

## Testing

**Python:**
```bash
PYTHONPATH=. python -m pytest tests/ -v
PYTHONPATH=. python -m pytest tests/ -m "unit or integration" -v
make test
make test-cov
```

**Frontend:**
```bash
cd frontend
npm run typecheck
npm run build
```

---

## Direct Redis Bypass

When Kafka and Flink are both down for 60+ seconds, the producer automatically switches to direct Redis writes for ticker data. Configure manually:

```yaml
# In docker-compose.yml producer service:
ENABLE_DIRECT_REDIS: "true"
```

This writes trade, ticker, candle, and orderbook data directly to Redis as a fallback path.

---

## Profiles

| Command | Services | Notes |
|---|---|---|
| `make dev` | 29 core services | Dev stack with hot reload |
| `make monitoring` | Dev + Prometheus/Grafana | +5 services |
| `make logging` | Dev + Loki/Promtail | +2 services |
| `make prod` | Production + monitoring + logging | SSL, certbot, DuckDNS |

---

## Documentation

| Document | Description |
|---|---|
| [docs/SYSTEM.md](docs/SYSTEM.md) | Full system architecture, data flow, APIs, caveats |
| [docs/system/](docs/system/) | Per-module detailed documentation (13 files) |
| [docs/CHANGELOG.md](docs/CHANGELOG.md) | Project history |
| [AGENTS.md](AGENTS.md) | AI agent workflow and coding rules |
| [docs/ai/AI_ARCHITECTURE.md](docs/ai/AI_ARCHITECTURE.md) | AI architecture, provider routing, RAG, actions, and safety |

---

## Version

Current: **v0.25.41** (see [CHANGELOG.md](docs/CHANGELOG.md))

---

## Service URLs & Default Credentials

All dev services are exposed on `localhost`. **For production, set every password in `.env` before first run.**

| Service | URL | Default User | Default Password | Notes |
|---|---|---|---|---|
| **Frontend** (React) | http://localhost | — | — | Main app |
| **Grafana** | http://localhost:3001 | `admin` | `admin` | Change via `GRAFANA_ADMIN_PASSWORD` env. Provisioned with 22 dashboards and 48 alert rules. Alert Center: http://localhost:3001/d/phase5-alert-center |
| **Prometheus** | http://localhost:9090 | — | — | Metrics storage; 21 scrape jobs |
| **Loki** | http://localhost:3100 | — | — | Logs (opt-in via `--profile logging`); 7-day retention |
| **FastAPI** (Swagger) | http://localhost:8080/docs | — | — | OpenAPI 3.1, JWT auth |
| **Flink Web UI** | http://localhost:8081 | — | — | JobManager; 3 streaming jobs |
| **Spark Master UI** | http://localhost:8082 | — | — | Spark Master |
| **MinIO Console** | http://localhost:9001 | `minioadmin` | `minioadmin` | S3-compatible lakehouse storage |
| **Trino** | http://localhost:8083 | — | — | Lakehouse SQL; 5 catalogs |
| **Dagster** | http://localhost:3000/dagster | — | — | Orchestration UI |
| **PostgreSQL** | localhost:5432 | `postgres` | `postgres` | Dev database; change via `POSTGRES_PASSWORD` |
| **Redis Sentinel** | localhost:26379 | — | `lmview_redis` | Master at localhost:6379 |
| **InfluxDB** | http://localhost:8086 | — | `lmview_influx` | Buckets + tokens in `.env` |
| **Promtail** | http://localhost:9080 | — | — | Log shipper; tails Docker logs → Loki |

### Production checklist

Before deploying to a public host:

- [ ] Set `GRAFANA_ADMIN_PASSWORD` to a strong random value (default `admin` is dev-only).
- [ ] Set `POSTGRES_PASSWORD`, `INFLUX_TOKEN`, `JWT_SECRET`, and all API keys.
- [ ] Disable `GF_USERS_ALLOW_SIGN_UP` (already `false` in compose).
- [ ] Configure TLS via `make prod` (uses Let's Encrypt + certbot).
- [ ] Set `LMVIEW_LOG_LEVEL=WARNING` in production to reduce log volume.
- [ ] Add a real contact point in `config/grafana/provisioning/alerting/contact-points.yml` (Slack webhook, PagerDuty key, or SMTP) — by default alerts go to Grafana's internal log only.

---

## Cloud Deployment (Docker Swarm)

**Production**: https://lmview.duckdns.org  
**Architecture**: 2-node EC2 cluster with Docker Swarm
- Core node (8 vCPU, 32 GB): storage, brokers, API, frontend, AI
- Worker node (4 vCPU, 16 GB): Flink, Spark, Trino, monitoring
- Shared EFS storage for code/config sync

**Quick Start:**
```bash
# On manager node
cd /mnt/efs/LMView
bash scripts/deploy_aws_swarm.sh
```

**Detail:** [docs/system/12-deployment.md](docs/system/12-deployment.md)

---

## Authors

Built and maintained by D22 Fintech, PTIT students:

- [@DoLong3304](https://github.com/DoLong3304) — Project Manager, DevOps and AI Engineer
- [@StupidDuck64](https://github.com/StupidDuck64) — Data Engineer
- [@EzraaOP](https://github.com/EzraaOP) — Frontend Developer

---

Status: Active development | Version: **0.25.42** | Deployed: Docker Swarm on AWS EC2
