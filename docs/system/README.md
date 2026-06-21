# docs/system — LMView Module Documentation

Detailed, auto-audited documentation for every subsystem of LMView.

| Doc | Covers | Last Updated |
|---|---|---|
| [01-architecture.md](01-architecture.md) | Lambda architecture, cooperation modes, data flow critical paths | 2026-06-19 |
| [02-serving-layer.md](02-serving-layer.md) | FastAPI routes, services, middleware, candle_service deep-dive | 2026-06-19 |
| [03-data-pipeline.md](03-data-pipeline.md) | src/ — exchanges, producer, Flink processing, writers, cross-component flows | 2026-06-19 |
| [04-lakehouse-layer.md](04-lakehouse-layer.md) | Spark, Iceberg, MinIO, Trino, batch jobs | 2026-06-19 |
| [05-ai-service.md](05-ai-service.md) | ai_service/ — agents, providers, RAG, safety, actions | 2026-06-19 |
| [06-frontend.md](06-frontend.md) | React 19, services, features, components | 2026-06-19 |
| [07-docker-infrastructure.md](07-docker-infrastructure.md) | Compose files, Swarm, 41 services, images | 2026-06-19 |
| [08-postgresql.md](08-postgresql.md) | Auth, settings, AI persistence, Iceberg catalog | 2026-06-19 |
| [09-kafka-layer.md](09-kafka-layer.md) | Brokers, topics, Avro schemas, producers | 2026-06-19 |
| [10-speed-layer.md](10-speed-layer.md) | Flink, Redis Sentinel, InfluxDB, hot cache | 2026-06-19 |
| [11-observability.md](11-observability.md) | Prometheus, Grafana, Loki, custom metrics | 2026-06-19 |
| [12-deployment.md](12-deployment.md) | Docker Swarm 2-node EC2 deployment | 2026-06-19 |
| [13-caveats.md](13-caveats.md) | Complete bug inventory (CI, BB, DP, IB, AI series), performance bottlenecks | 2026-06-19 |
| [14-scripts.md](14-scripts.md) | Scripts reference — deploy, certbot, duckdns, watchdog, audit | 2026-06-19 |
| [swarm-worker-image-recovery.md](swarm-worker-image-recovery.md) | Runbook: recover worker node when Swarm tasks fail with "No such image" | 2026-06-21 |

## How to Use These Docs

1. **Start here**: [01-architecture.md](01-architecture.md) for system overview and data flow
2. **Your module**: Read the corresponding doc for your area
3. **Bugs & issues**: [13-caveats.md](13-caveats.md) has the complete bug inventory
4. **Operations**: [14-scripts.md](14-scripts.md) for deployment/maintenance scripts, [12-deployment.md](12-deployment.md) for Swarm

## Status

Generated: 2026-06-19
Release: 0.25.42
Branch: deploy/aws-swarm-2node-stable
