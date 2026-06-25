# docs/system — LMView Module Documentation

Detailed, auto-audited documentation for every subsystem of LMView.

| Doc | Covers | Last Updated |
|---|---|---|
| [01-architecture.md](01-architecture.md) | Lambda architecture, cooperation modes, data flow critical paths | 2026-06-25 |
| [02-serving-layer.md](02-serving-layer.md) | FastAPI routes, services, middleware, candle_service deep-dive | 2026-06-25 |
| [03-data-pipeline.md](03-data-pipeline.md) | src/ — exchanges, producer, Flink processing, writers, cross-component flows | 2026-06-25 |
| [04-lakehouse-layer.md](04-lakehouse-layer.md) | Spark, Iceberg, MinIO, Trino, batch jobs | 2026-06-25 |
| [05-ai-service.md](05-ai-service.md) | ai_service/ — agents, providers, RAG, safety, actions | 2026-06-25 |
| [06-frontend.md](06-frontend.md) | React 19, services, features, components | 2026-06-25 |
| [07-docker-infrastructure.md](07-docker-infrastructure.md) | Compose files, Swarm, services, images | 2026-06-25 |
| [08-postgresql.md](08-postgresql.md) | Auth, settings, AI persistence, Iceberg catalog | 2026-06-25 |
| [09-kafka-layer.md](09-kafka-layer.md) | Brokers, topics, Avro schemas, producers | 2026-06-25 |
| [10-speed-layer.md](10-speed-layer.md) | Flink, Redis Sentinel, InfluxDB, hot cache | 2026-06-25 |
| [11-observability.md](11-observability.md) | Prometheus, Grafana, Loki, custom metrics | 2026-06-25 |
| [12-deployment.md](12-deployment.md) | Docker Swarm EC2 deployment (2-node / 3-node) | 2026-06-25 |
| [13-caveats.md](13-caveats.md) | Complete bug inventory, performance bottlenecks | 2026-06-25 |
| [14-scripts.md](14-scripts.md) | Scripts reference — deploy, certbot, duckdns, watchdog, audit | 2026-06-25 |
| [swarm-worker-image-recovery.md](swarm-worker-image-recovery.md) | Runbook: recover worker node when Swarm tasks fail with "No such image" | 2026-06-25 |
| [../3NODE-MIGRATION-PLAN.md](3NODE-MIGRATION_PLAN.md) | 3-node Docker Swarm migration proposal | 2026-06-25 |

## How to Use These Docs

1. **Start here**: [01-architecture.md](01-architecture.md) for system overview and data flow
2. **Your module**: Read the corresponding doc for your area
3. **Bugs & issues**: [13-caveats.md](13-caveats.md) has the complete bug inventory
4. **Operations**: [14-scripts.md](14-scripts.md) for deployment/maintenance scripts, [12-deployment.md](12-deployment.md) for Swarm

## Status

Generated: 2026-06-25
Release: 0.27.0
Branch: deploy/aws-swarm-2node-stable
