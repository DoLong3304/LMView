# Docker Infrastructure

Docker Compose + Swarm setup for LMView.

## Compose Files

| File | Purpose |
|---|---|
| `docker-compose.yml` | Main — all services, profiles, volumes, networks (1300 lines) |
| `docker-compose.swarm.yml` | Swarm overlay — placement, resources, configs (extends main) |
| `docker-compose.ai.yml` | AI service extension — LiteLLM, vLLM |

Deployment: `bash scripts/deploy_aws_swarm.sh`

## Dockerfiles (per service)

Each service has its own Dockerfile under `docker/<service>/`:

| Service | Dockerfile | Base Image | Purpose |
|---|---|---|---|
| fastapi | `docker/fastapi/Dockerfile` | python:3.11-slim | Backend API gateway (NO heavy AI deps) |
| ai-service | `docker/ai-service/Dockerfile` | python:3.11-slim | Standalone AI service (has torch, transformers) |
| nginx | `docker/nginx/Dockerfile` | nginx:alpine | Reverse proxy + SSL |
| flink | `docker/flink/Dockerfile` | flink:1.18.1 | Flink jobmanager + taskmanager |
| spark | `docker/spark/Dockerfile` | spark:3.5.5 | Spark master + worker |
| ticker-ws | `docker/ticker-ws/Dockerfile` | python:3.11-slim | Binance WS ticker feed (8 shards) |
| combined-stream | `docker/combined-stream/Dockerfile` | python:3.11-slim | Combined-stream Kafka producer |
| kline-rest | `docker/kline-rest/Dockerfile` | python:3.11-slim | REST kline feed |
| depth-trades-rest | `docker/depth-trades-rest/Dockerfile` | python:3.11-slim | REST depth + trades feed |
| producer | `docker/producer/Dockerfile` | python:3.11-slim | Legacy producer (all WS paths disabled) |
| backfill | `docker/backfill/Dockerfile` | python:3.11-slim | InfluxDB backfill job |
| dagster | `docker/dagster/Dockerfile` | python:3.11-slim | Dagster orchestration |

| Profile | Services |
|---|---|
| `dev` | Core: zookeeper, kafka-1/2/3, schema-registry, producer, redis-master/replicas/sentinels, influxdb, minio, postgres, flink-jobmanager/taskmanager, spark-master/workers, trino, fastapi-dev, frontend-dev, nginx-dev |
| `prod` | Same as dev but fastapi-prod, nginx-prod (multi-worker, SSL) |
| `monitoring` | Prometheus, Grafana, kafka-exporter, node-exporter, redis-exporter |
| `logging` | Loki, promtail |
| `ai-api` | LiteLLM, vLLM (from docker-compose.ai.yml) |

## Services (41 total)

### Data Layer (Storage & Brokers)

| Service | Image | Replicas | Node | Ports |
|---|---|---|---|---|
| zookeeper | cp-zookeeper:7.6.0 | 1 | core | 2181, 7071 |
| kafka-1/2/3 | cryptoprice/kafka:3.9.0 | 1 each | core | 19092, 9093, 9094 |
| schema-registry | apicurio-registry-mem:2.6.2 | 1 | core | 8085 |
| postgres | pgvector/pgvector:pg16 | 1 | core | 5432 |
| redis-master | redis:7.2-alpine | 1 | core | 6379 |
| redis-replica-1/2 | redis:7.2-alpine | 1 each | core | — |
| redis-sentinel-1/2/3 | redis:7.2-alpine | 1 each | core | 26379-26381 |
| influxdb | influxdb:2.7 | 1 | core | 8086 |
| minio | minio:RELEASE.2025-09-07 | 1 | core | 9000-9001 |

### Streaming & Compute (Worker Node)

| Service | Image | Replicas | Node |
|---|---|---|---|
| flink-jobmanager | cryptoprice/flink:1.18.1 | 1 | worker |
| flink-taskmanager | cryptoprice/flink:1.18.1 | 2 | worker |
| spark-master | cryptoprice/spark:3.5.5 | 1 | worker |
| spark-worker | cryptoprice/spark:3.5.5 | 2 | worker |
| trino | cryptoprice/trino:442 | 1 | worker |
| spark-submit | cryptoprice/spark-submit:local | 0/1 | worker |

### Serving Layer (Core Node)

| Service | Image | Replicas | Node | Ports |
|---|---|---|---|---|
| fastapi-prod | cryptoprice/fastapi:latest | 1 | core | 8080 |
| nginx-prod | lmview-nginx:latest | 1 | core | 80, 443 |
| producer | cryptoprice/producer:latest | 1 | core | — |

### AI (Core Node)

| Service | Image | Replicas | Status |
|---|---|---|---|
| ai-service | python:3.11-slim | 0/1 | FastAPI service for AI |
| litellm | ghcr.io/berriai/litellm | 0/1 | Opt-in |

### Monitoring & Logging (Worker Node, opt-in)

| Service | Image | Replicas | Status |
|---|---|---|---|
| prometheus | prom/prometheus:v2.45.0 | 0/1 | Stopped |
| grafana | grafana/grafana:10.2.0 | 1/1 | Running (port 3001) |
| loki | grafana/loki:2.9.0 | 0/1 | Stopped |
| promtail | grafana/promtail:2.9.0 | 0/1 | Stopped |
| kafka-exporter | danielqsj/kafka-exporter | 1/1 | Running (port 9308) |
| node-exporter | prom/node-exporter:v1.6.1 | 0/1 | Stopped |
| redis-exporter | oliver006/redis_exporter | 0/1 | Stopped |

### Utilities (Core Node)

| Service | Image | Replicas | Status |
|---|---|---|---|
| registry | registry:2 | 1 | Running (port 5000) — local image registry |
| certbot-auto | certbot/certbot:v5.6.0 | 1/1 | SSL auto-renewal |
| duckdns-auto | curlimages/curl:8.7.1 | 1/1 | DuckDNS IP update |
| minio-init | minio/mc | 0/1 | One-shot bucket create |
| auto-submit-jobs | cryptoprice/flink:1.18.1 | 0/1 | Flink job submission |
| job-watchdog | docker:27.0-cli | 0/1 | Job health watchdog |
| dagster-webserver | cryptoprice/dagster:1.8.10 | 0/1 | Dagster UI (port 3000) |
| dagster-daemon | cryptoprice/dagster:1.8.10 | 0/1 | Dagster scheduler |
| influx-backfill | cryptoprice/influx-backfill:0.25.0 | 0/1 | Historical data backfill |

## Docker Images (Custom)

| Image | Source | Built From |
|---|---|---|
| `cryptoprice/fastapi:latest` | docker/fastapi/Dockerfile | python:3.11-slim |
| `cryptoprice/producer:latest` | docker/fastapi/Dockerfile (same image) | python:3.11-slim |
| `cryptoprice/kafka:3.9.0` | docker/kafka/Dockerfile | apache/kafka:3.9.0 |
| `cryptoprice/flink:1.18.1` | docker/flink/Dockerfile | flink:1.18.1-slim |
| `cryptoprice/spark:3.5.5` | docker/spark/Dockerfile | bitnami/spark:3.5.5 |
| `cryptoprice/trino:442` | docker/trino/Dockerfile (if exists) | trino:442 |
| `cryptoprice/dagster:1.8.10` | dagster Dockerfile | python:3.11-slim |
| `cryptoprice/spark-submit:local` | docker/spark/Dockerfile + submit entrypoint | bitnami/spark:3.5.5 |
| `lmview-nginx:latest` | docker/nginx/Dockerfile | nginx:1.31.0-alpine |

## Image Build & Push Flow

1. `docker compose --profile prod build` — builds all custom images
2. Images tagged as `172.31.21.135:5000/cryptoprice/*:*`
3. Push to local registry (`registry:2` on port 5000)
4. Swarm nodes pull from local registry (`--resolve-image never`)

## Node Placement Strategy

- **Core node** (8 vCPU, 32 GB): labeled `role=core`
  - Storage (redis, postgres, influxdb, minio), brokers (kafka, zookeeper), API (fastapi, nginx), producer, registry, certbot, duckdns
  - Memory budget: ~25 GB services + ~5 GB OS/buffers
- **Worker node** (4 vCPU, 16 GB): labeled `role=worker`
  - Compute (flink, spark, trino), monitoring (grafana, prometheus), logging (loki, promtail)
  - Memory budget: ~13 GB services + ~3 GB OS/buffers

## Important Configs

- **docker/fastapi/requirements.txt**: FastAPI deps including litellm, asyncpg, influxdb_client, prometheus_client
- **docker/nginx/nginx-prod.conf**: SSL, HSTS, rate limiting, proxy to fastapi, gzip, security headers
- **docker/flink/flink-conf.yaml**: TaskManager memory 1536MB, parallelism, checkpoint config
- **docker/kafka/entrypoint.sh**: ZK session timeout 10s, stale node cleanup on restart

## Health Checks

Services with health checks: zookeeper, kafka-1/2/3, postgres, redis-master/replicas/sentinels, influxdb, minio, fastapi-prod, nginx-prod, trino, spark-master

Missing health checks: producer, flink-jobmanager, taskmanager, spark-worker/worker-2, schema-registry

## Scripts

| Script | Purpose |
|---|---|
| `scripts/deploy_aws_swarm.sh` | Full deploy: build → push → deploy |
| `scripts/auto_submit_jobs.sh` | Submit Flink/Spark streaming jobs |
| `scripts/certbot_auto.sh` | SSL certificate request |
| `scripts/init_certbot.sh` | Initial certbot setup |
| `scripts/duckdns_auto.sh` | DuckDNS IP update |
| `scripts/submit_flink.sh` | Manual Flink job submission |
| `scripts/create_kafka_topics.sh` | Kafka topic creation |
| `scripts/audit_data_coverage.py` | Data coverage audit |
| `scripts/verify_all_via_grafana.py` | Verification via Grafana API |

## Known Issues

- **FastAPI image**: Both `fastapi-prod` and `producer` use the same image (`docker/fastapi/Dockerfile`). The producer runs extra deps that bloats the API image.
- **ai-service**: 0/1 — scaffolded service that exits immediately. AI runs inside FastAPI container.
- **Monitoring services**: Most are 0/1 (stopped). Only grafana, kafka-exporter running.
- **Missing health checks**: producer, flink, spark-worker, schema-registry lack health checks.
- **EFS bind mounts**: Services with `/mnt/efs/LMView` bind mounts must run on EFS-mounted node. Can't failover to worker without EFS mount.
