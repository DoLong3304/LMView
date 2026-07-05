# Docker Infrastructure

Docker Compose + Swarm setup for LMView (v0.28.1, 3-node).

## Compose Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Main — all services, profiles, volumes, networks (~1700 lines) |
| `docker-compose.swarm.yml` | Swarm overlay — placement, resources, configs (extends main) |
| `docker-compose.ai.yml` | AI service extension — LiteLLM, vLLM |

Deployment: `bash scripts/deploy_aws_swarm.sh`

## Dockerfiles (per service)

| Service | Dockerfile | Base Image | Purpose |
|---|---|---|---|
| fastapi | `docker/fastapi/Dockerfile` | python:3.11-slim | Backend API (NO heavy AI deps) |
| ai-service | `docker/ai-service/Dockerfile` | python:3.11-slim | Standalone AI service (torch, transformers) |
| nginx | `docker/nginx/Dockerfile` | nginx:1.27.5 | Reverse proxy + SSL |
| flink | `docker/flink/Dockerfile` | flink:1.18.1 | Flink jobmanager + taskmanager |
| spark | `docker/spark/Dockerfile` | bitnami/spark:3.5.5 | Spark master + worker |
| ticker-ws | `docker/ticker-ws/Dockerfile` | python:3.11-slim | Binance WS ticker feed (8 shards) |
| combined-stream | `docker/combined-stream/Dockerfile` | python:3.11-slim | Combined-stream Kafka producer |
| kline-rest | `docker/kline-rest/Dockerfile` | python:3.11-slim | REST kline feed (200 symbols) |
| depth-trades-rest | `docker/depth-trades-rest/Dockerfile` | python:3.11-slim | REST depth + trades feed |
| producer | `docker/producer/Dockerfile` | python:3.11-slim | Legacy producer (all WS disabled, 403 geofenced) |
| backfill | `docker/backfill/Dockerfile` | python:3.11-slim | InfluxDB backfill job |
| dagster | `docker/dagster/Dockerfile` | python:3.11-slim | Dagster orchestration |

## Profiles

| Profile | Services |
|---|---|
| `dev` | Core data + compute + fastapi-dev + nginx-dev |
| `prod` | Same as dev but fastapi-prod + nginx-prod (multi-worker, SSL) |
| `monitoring` | Prometheus, Grafana, kafka-exporter, node-exporter, redis-exporter |
| `logging` | Loki, promtail |
| `ai-api` | LiteLLM, vLLM (from docker-compose.ai.yml) |

## Logging (All Services)

Every service has capped log rotation to prevent disk fill:

```yaml
logging:
  driver: json-file
  options:
    max-size: "10m"
    max-file: "3"
```

Each container limited to **30MB** of logs. Applied via YAML anchor (`x-logging`)
referenced in all 38 services.

## Services (46 total, 38 active)

### Data Layer (data node — `role=data`)

| Service | Image | Replicas | Ports |
|---|---|---|---|
| zookeeper | cp-zookeeper:7.6.0 | 1 | 2181, 7071 |
| kafka-1 | apache/kafka:3.9.0 | 1 | 19092 |
| kafka-2 | apache/kafka:3.9.0 | 1 | 9093 |
| kafka-3 | apache/kafka:3.9.0 | 1 | 9094 |
| schema-registry | apicurio-registry-mem:2.6.2 | 1 | 8085 |
| postgres | pgvector/pgvector:pg16 | 1 | 5432 |
| redis-master | redis:7.2-alpine | 1 | 16379 |
| redis-replica-1/2 | redis:7.2-alpine | 2 | — |
| redis-sentinel-1/2/3 | redis:7.2-alpine | 3 | 26379-26381 |
| influxdb | influxdb:2.7 | 1 | 8086 |
| minio | minio:RELEASE.2025-09-07 | 1 | 9000-9001 |
| minio-init | minio/mc | 0/1 | — (one-shot) |

### Compute Layer (compute node — `role=compute`)

| Service | Image | Replicas | Ports |
|---|---|---|---|
| flink-jobmanager | cryptoprice/flink:1.18.1 | 1 | 8081 |
| flink-taskmanager | cryptoprice/flink:1.18.1 | 2 | — |
| spark-master | cryptoprice/spark:3.5.5 | 1 | 7077, 8082, 18080 |
| spark-worker | cryptoprice/spark:3.5.5 | 1 | — |
| spark-worker-2 | cryptoprice/spark:3.5.5 | 1 | — |
| spark-submit | cryptoprice/spark-submit:local | 1 | — |
| trino | cryptoprice/trino:442 | 1 | 8083 |
| dagster-webserver | cryptoprice/dagster:1.8.10 | 1 | 3000 |
| dagster-daemon | cryptoprice/dagster:1.8.10 | 1 | — |
| job-watchdog | docker:27.0-cli | 1 | — |

### Serving Layer (core node — `role=core`)

| Service | Image | Replicas | Ports |
|---|---|---|---|
| nginx-prod | cryptoprice/nginx:1.44.0 | 1 | 80, 443 |
| fastapi-prod | cryptoprice/fastapi:0.28.0 | 1 | 8080 |
| producer | cryptoprice/producer:0.25.0 | 1 | — (all WS disabled) |
| binance-ticker-ws | cryptoprice/binance-ticker-ws:0.1.0 | 1 | — |
| binance-kline-rest | cryptoprice/binance-kline-rest:0.1.0 | 1 | — |
| binance-depth-trades-rest | cryptoprice/binance-depth-trades-rest:0.1.0 | 1 | — |
| combined-stream-producer | cryptoprice/combined-stream:0.25.60 | 1 | — |

### AI Layer (core node — `role=core`)

| Service | Image | Replicas | Ports |
|---|---|---|---|
| ai-service | cryptoprice/ai-service:latest | 1 | 8100 |
| litellm | ghcr.io/berriai/litellm:main-latest | 1 | 4000 |
| finbert-worker | python:3.11-slim | 1 | — |

### Monitoring & Logging (compute node — `role=compute`, all active)

| Service | Image | Replicas | Ports |
|---|---|---|---|
| prometheus | prom/prometheus:v2.45.0 | 1 | 9090 |
| grafana | grafana/grafana:10.2.0 | 1 | 3001 |
| loki | grafana/loki:2.9.0 | 1 | 3100 |
| promtail | grafana/promtail:2.9.0 | 1 | — |
| kafka-exporter | danielqsj/kafka-exporter:v1.7.0 | 1 | 9308 |
| node-exporter | prom/node-exporter:v1.6.1 | 1 | 9100 |
| redis-exporter | oliver006/redis_exporter:v1.83.0 | 1 | 9121 |

### Utilities (core node — `role=core`)

| Service | Image | Replicas | Ports |
|---|---|---|---|
| registry | registry:2 | 1 | 5000 (local image registry) |
| certbot-auto | certbot/certbot:v5.6.0 | 1 | — (SSL renewal, 12h loop) |
| duckdns-auto | curlimages/curl:8.7.1 | 1 | — (DNS update, 5min loop) |
| auto-submit-jobs | cryptoprice/flink:1.18.1 | 0/1 | — (one-shot, manual) |
| influx-backfill | cryptoprice/influx-backfill:0.25.0 | 0/1 | — (one-shot, completed) |

## Docker Images (Custom, in local registry)

| Image | Size | Built From |
|---|---|---|
| `cryptoprice/ai-service:latest` | 9.34GB | python:3.11-slim + torch + transformers |
| `cryptoprice/flink:1.18.1` | 2.91GB | flink:1.18.1-slim + python + deps |
| `cryptoprice/trino:442` | 2.48GB | trino:442 + Iceberg connector |
| `cryptoprice/dagster:1.8.10` | 2.12GB | python:3.11-slim + dagster + deps |
| `cryptoprice/spark:3.5.5` | 1.59GB | bitnami/spark:3.5.5 + python + deps |
| `cryptoprice/spark-submit:local` | 1.58GB | spark:3.5.5 + submit entrypoint |
| `cryptoprice/producer:0.25.0` | 613MB | python:3.11-slim (same image as fastapi) |
| `cryptoprice/fastapi:0.28.0` | 329MB | python:3.11-slim |
| `cryptoprice/nginx:1.44.0` | 293MB | nginx:1.27.5 |
| `cryptoprice/combined-stream:0.25.60` | 254MB | python:3.11-slim |
| `cryptoprice/binance-kline-rest:0.1.0` | 243MB | python:3.11-slim |
| `cryptoprice/influx-backfill:0.25.0` | 224MB | python:3.11-slim |
| `cryptoprice/binance-ticker-ws:0.1.0` | 211MB | python:3.11-slim |
| `cryptoprice/binance-depth-trades-rest:0.1.0` | 205MB | python:3.11-slim |
| `cryptoprice/alpine:latest` | ~10MB | alpine:3.18 |

**Total image storage**: ~13GB when pruned, up to 26GB with dangling images.

## Image Build & Push Flow

1. `docker compose --profile prod build` — builds custom images
2. Tagged as `172.31.9.72:5000/cryptoprice/*:*` (registry address)
3. Pushed to local registry (`registry:2` on port 5000, available at `127.0.0.1:5000`)
4. Swarm nodes pull from local registry (`--resolve-image never`)

## Storage Management

### Docker Storage Drivers
- Docker 29.6 uses **containerd** for image layer storage
- Layers stored in `/var/lib/containerd` (not `/var/lib/docker/overlay2`)
- Image metadata in `/var/lib/docker`

### Storage Budget (target)

| Category | Current | Target | Growth Control |
|---|---|---|---|
| Active images | ~13GB | ~15GB | Prune dangling after each deploy |
| Build cache | ~0GB | ~1GB | `docker builder prune -af` pre-build |
| Container logs | ~30MB | ~500MB | Log rotation (10m×3 per container) |
| Dead containers | ~0GB | ~0GB | Prune post-deploy |
| Data volumes | ~500MB | ~5GB | Protected (never pruned) |
| **Total** | **~29GB** | **~36GB** | |

### Cleanup Hooks (in deploy script)

Pre-build: `docker container prune -f` + `docker image prune -af --filter "until=24h"` + `docker builder prune -af`
Post-deploy: `docker container prune -f` + `docker image prune -af --filter "until=48h"`

## Node Placement Strategy

- **Core** (`role=core`, 8 vCPU, 32GB): Serving, data feeds, AI, utilities — ~14 containers, ~12GB
- **Data** (`role=data`, 8 vCPU, 32GB): Storage + messaging — ~15 containers, ~10GB
- **Compute** (`role=compute`, 8 vCPU, 32GB): Stream/batch processing + monitoring — ~18 containers, ~16GB

## Important Configs

- **docker/fastapi/requirements.txt**: FastAPI deps including litellm, asyncpg, influxdb_client
- **docker/nginx/nginx-prod.conf**: SSL, HSTS, rate limiting, proxy to fastapi, gzip, security headers
- **docker/nginx/entrypoint.sh**: Self-signed bootstrap cert, domain substitution, htpasswd generation
- **docker/flink/flink-conf.yaml**: TaskManager memory 2048MB, parallelism, checkpoint config
- **docker/kafka/entrypoint.sh**: ZK session timeout 10s, stale node cleanup on restart

## Health Checks

**With health checks**: zookeeper, kafka-1/2/3, postgres, redis-master/replicas/sentinels, influxdb, minio, fastapi-prod, nginx-prod, trino, spark-master, spark-worker, spark-worker-2, flink-jobmanager, dagster-webserver, dagster-daemon, binance-ticker-ws, binance-kline-rest, binance-depth-trades-rest, ai-service

**Without health checks (known gap)**: producer, schema-registry, flink-taskmanager (uses `pgrep` workaround)

## SSL/TLS

- **Domain**: `lmview.duckdns.org` → 18.140.245.176
- **Provider**: Let's Encrypt (DNS-01 via certbot-dns-duckdns plugin)
- **Valid until**: 2026-09-24
- **HSTS**: Active (`max-age=63072000; includeSubDomains`)
- **Renewal**: certbot-auto every 12h, nginx reload every 6h
- **Bootstrap**: Nginx entrypoint creates 1-day self-signed fallback cert

## Known Issues

- **FastAPI image shared with producer**: Both services use the same image (`docker/fastapi/Dockerfile`). Producer has all WS paths disabled due to Binance geofencing.
- **binance-kline-rest CPU**: 54-67% CPU from polling 200 symbols every 30s. Expected.
- **combined-stream OOM history**: Was 512M limit → OOM killed every ~1h. Now 1G, stable.
- **spark-worker healthcheck**: Had wrong port (8081 vs 8084). Fixed by service update.
- **Flink taskmanager healthcheck**: Uses `pgrep` workaround (TCP healthcheck on 6123 broken because TM uses dynamic RPC port).
- **Registry accessible at 127.0.0.1**: `localhost:5000` hangs but `127.0.0.1:5000` works (Docker port forwarding nuance).
