# docs/system — LMView Module Documentation

Detailed, auto-audited documentation for every subsystem of LMView.

| Doc | Covers | Last Updated |
|---|---|---|
| [01-architecture.md](01-architecture.md) | Lambda architecture, cooperation modes, data flow critical paths | 2026-06-26 |
| [02-serving-layer.md](02-serving-layer.md) | FastAPI routes, services, middleware, candle_service deep-dive | 2026-06-25 |
| [03-data-pipeline.md](03-data-pipeline.md) | src/ — exchanges, producer, Flink processing, writers, cross-component flows | 2026-06-25 |
| [04-lakehouse-layer.md](04-lakehouse-layer.md) | Spark, Iceberg, MinIO, Trino, batch jobs | 2026-06-25 |
| [05-ai-service.md](05-ai-service.md) | ai_service/ — agents, providers, RAG, safety, actions | 2026-06-25 |
| [06-frontend.md](06-frontend.md) | React 19, services, features, components | 2026-06-25 |
| [07-docker-infrastructure.md](07-docker-infrastructure.md) | Compose files, Swarm, services, images, storage | 2026-06-26 |
| [08-postgresql.md](08-postgresql.md) | Auth, settings, AI persistence, Iceberg catalog | 2026-06-25 |
| [09-kafka-layer.md](09-kafka-layer.md) | Brokers, topics, Avro schemas, producers | 2026-06-25 |
| [10-speed-layer.md](10-speed-layer.md) | Flink, Redis Sentinel, InfluxDB, hot cache | 2026-06-25 |
| [11-observability.md](11-observability.md) | Prometheus, Grafana, Loki, custom metrics | 2026-06-25 |
| [12-deployment.md](12-deployment.md) | Docker Swarm EC2 deployment (3-node) | 2026-06-26 |
| [13-caveats.md](13-caveats.md) | Complete bug inventory, performance bottlenecks, storage management | 2026-06-26 |
| [14-scripts.md](14-scripts.md) | Scripts reference — deploy, certbot, duckdns, watchdog, audit | 2026-06-26 |
| [swarm-worker-image-recovery.md](swarm-worker-image-recovery.md) | Runbook: recover worker node when Swarm tasks fail with "No such image" | 2026-06-25 |
| [../3NODE-MIGRATION-PLAN.md](3NODE-MIGRATION_PLAN.md) | 3-node Docker Swarm migration proposal | 2026-06-25 |

## How to Use These Docs

1. **Start here**: [01-architecture.md](01-architecture.md) for system overview and data flow
2. **Your module**: Read the corresponding doc for your area
3. **Bugs & issues**: [13-caveats.md](13-caveats.md) has the complete bug inventory
4. **Operations**: [14-scripts.md](14-scripts.md) for deployment/maintenance scripts, [12-deployment.md](12-deployment.md) for Swarm

## Status

Generated: 2026-06-25
Release: 0.28.3
Branch: deploy/aws-swarm-2node-stable

## Changes Since 0.27.0

- **3-node Swarm**: data + compute nodes split from single worker
- **Storage management**: log rotation (`max-size=10m`, `max-file=3`) on all 38 services;
  pre/post-deploy cleanup hooks in deploy script
- **SSL cert**: Let's Encrypt issued via certbot-dns-duckdns plugin (valid Sep 2026)
- **spark-worker**: Fixed healthcheck port (8081→8084)
- **combined-stream**: Memory limit 512M→1G (was OOM-killing)
- **Dead container prune**: 42.6GB reclaimed on compute node
- **1s kline fixes** (v0.28.2–0.28.3):
  - BB-9: Backend merged endpoint 1s→1m fallthrough — fixed
  - BB-10: WS synthetic 1s candle when Redis empty — fixed
  - FE-1: Frontend gap defense too strict for 1s (MAX_BRIDGE_BUCKETS 5→30) — fixed
  - FE-2: Cache TTL too aggressive for 1s (500ms vs 3s) — fixed
  - FE-3: Left toolbar price lag (_livePriceMap + 500ms interval) — fixed
  - DP-9: binance-kline-ws deployed to Swarm (8/8 shards, 131+ symbols)
  - Frontend rebuild + deploy (nginx 1.44.5)
