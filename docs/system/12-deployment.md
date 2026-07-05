# Docker Swarm Deployment

3-node AWS EC2 deployment with EFS shared storage for code/config, local volumes for stateful data.

> **Migration status:** 2-node → 3-node completed.
> Old 2-node reference: [`docs/3NODE-MIGRATION-PLAN.md`](../3NODE-MIGRATION-PLAN.md).

## Infrastructure

### Nodes

| Node | Hostname | Role | Spec | Services |
|---|---|---|---|---|
| Manager (Leader) | ip-172-31-9-72 | `role=core` | 8 vCPU, 32 GB RAM | Nginx, FastAPI, React, ai-service, producer, litellm, certbot, duckdns, registry, Redis Sentinel-1 |
| Worker 1 | ip-172-31-1-8 | `role=data` | 8 vCPU, 32 GB RAM | PostgreSQL, Redis Master + Sentinel-2, Kafka (×3), InfluxDB, MinIO, Zookeeper, Schema Registry |
| Worker 2 | ip-172-31-3-31 | `role=compute` | 8 vCPU, 32 GB RAM | Flink (1 JM + 2 TM), Spark (1M + 2W), Trino, Dagster (web + daemon), Redis Replica + Sentinel-3, Prometheus, Grafana, Loki, Promtail, node-exporter, kafka-exporter, redis-exporter |

### Node Labels

```bash
docker node update --label-add role=core    <manager-node-id>
docker node update --label-add role=data    <data-node-id>
docker node update --label-add role=compute <compute-node-id>
```

### Redis HA Topology

Redis deployed as Master–Replica–Sentinel across all 3 nodes for high availability:

| Node | Role | Service |
|---|---|---|
| core | Sentinel (quorum) | `redis-sentinel-1` |
| data | Master + Sentinel (quorum) | `redis-master`, `redis-sentinel-2` |
| compute | Replica + Sentinel (quorum) | `redis-replica-1`, `redis-sentinel-3` |

- Quorum = 2/3 sentinels → auto-failover in <30s if master dies
- Master (data) handles writes; Replica (compute) serves read-only traffic
- If data node fails, sentinels promote replica to master on compute node
- `redis-replica-2` removed per design (1 replica only)

### Storage

- **EFS shared mount** (`/mnt/efs/LMView`): Code, config, scripts — mounted on all 3 nodes
- **Local Docker volumes** (node-local): Stateful data — PostgreSQL data, Redis RDB/AOF, Kafka logs, InfluxDB data, MinIO data
  - Faster (local SSD vs NFS), safer (no NFS fork for Redis RDB)
  - Trade-off: node failure loses local data → mitigated by replication
- **Local registry**: `registry:2` container on core node (port 5000)

## Deployment Flow

```bash
# Full deploy (build + push + deploy)
bash scripts/deploy_aws_swarm.sh

# Quick deploy (skip build, use existing images)
bash scripts/deploy_aws_swarm.sh --skip-build

# Registry only (push existing images)
bash scripts/deploy_aws_swarm.sh --registry-only
```

### What deploy_aws_swarm.sh does:

1. **Preflight checks**: Swarm active, node labels exist (core + data + compute), .env exists, Docker 24+ Engine
2. **Build images**: `docker compose --profile prod --profile monitoring --profile logging build`
3. **Push to registry**: Tags + pushes custom images to `<REGISTRY_ADDR>:5000/cryptoprice/*`
4. **Deploy stack**: `docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml cryptoprice --resolve-image never --prune`
5. **Post-deploy**: Show service status

### Image Building

Custom images built from:
- `docker/fastapi/Dockerfile` → fastapi, producer
- `docker/flink/Dockerfile` → flink
- `docker/spark/Dockerfile` → spark, spark-submit
- `docker/kafka/Dockerfile` → kafka
- `docker/nginx/Dockerfile` → nginx

## SSL/TLS

- **DuckDNS**: Auto-updates IP via `duckdns-auto` service (curl every 5 min)
- **Let's Encrypt**: `certbot-auto` service handles certificate issuance/renewal
- **Certificates**: Stored in `letsencrypt` Docker volume
- **Nginx**: Serves HTTPS with HSTS, redirects HTTP

## Service URLs (Production)

| Service | URL |
|---|---|
| Frontend | https://lmview.duckdns.org |
| FastAPI Swagger | https://lmview.duckdns.org/docs |
| Grafana | https://lmview.duckdns.org/grafana/ |
| Flink UI | https://lmview.duckdns.org/flink/ |

## Makefile Targets

```bash
make swarm-deploy          # Full deploy (build + push + stack deploy)
make swarm-deploy-quick    # Quick deploy (skip build)
make swarm-push            # Build & push only
make swarm-status          # Show node/service/task status
make swarm-logs SVC=name   # Tail service logs
make swarm-restart SVC=name # Rolling restart
make swarm-down            # Remove stack (keeps registry, volumes)
```

## Rollback

A `production` branch is maintained as a snapshot for rollback:

```bash
git checkout production
bash scripts/deploy_aws_swarm.sh
```

## Known Issues

- **EFS bind mounts**: Services with `/mnt/efs/LMView` mounts (fastapi, ai-service) cannot failover to data/compute node without EFS mount
- **Registry**: Single point on core node. If core goes down, images can't be pulled
- **Monitoring**: Some services (prometheus, loki) may show 0/1 replicas — check `docker service ps`
- **Flink auto-submit**: 0/1 — jobs must be submitted manually via Flink UI or submit script
- **Certbot**: Renewal depends on port 80 being accessible from internet
- **binance-kline-rest**: Image may not exist on compute/data nodes — `--resolve-image never` expects images pre-pulled; run `sync_worker_images.sh` after deploy
