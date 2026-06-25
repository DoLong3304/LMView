# Docker Swarm Deployment

> **Note:** This doc describes the current 2-node AWS EC2 deployment.
> For the planned 3-node migration, see [`docs/3NODE-MIGRATION-PLAN.md`](../3NODE-MIGRATION-PLAN.md).

2-node AWS EC2 deployment with EFS shared storage.

## Infrastructure

### Nodes

| Node | Role | Spec | Services |
|---|---|---|---|
| Manager (Leader) | Core | 8 vCPU, 32 GB RAM | Nginx, FastAPI, Redis, Kafka, PostgreSQL, InfluxDB, MinIO, AI service, certbot |
| Worker | Compute | 4 vCPU, 16 GB RAM | Flink, Spark, Trino, Dagster, monitoring |

⚠️ Worker node `ip-172-31-9-171` terminated 2026-06-25. Node labels and IPs are
**not** hardcoded — configure via `REGISTRY_ADDR`, `FLINK_JM_URL`, etc. See
`.env.example` for all configurable vars.

### Node Labels

```bash
docker node update --label-add role=core ip-172-31-21-135
docker node update --label-add role=worker ip-172-31-9-171
```

### Storage

- **EFS shared mount**: `/mnt/efs/LMView` — code and config sync across nodes
- **Local Docker volumes**: data persistence per node (redis, postgres, influxdb, minio, kafka)
- **Local registry**: `registry:2` container on manager node (port 5000)

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

1. **Preflight checks**: Swarm active, node labels exist, .env exists, Docker 24+ Engine
2. **Build images**: `docker compose --profile prod --profile monitoring --profile logging build`
3. **Push to registry**: Tags + pushes custom images to `172.31.21.135:5000/cryptoprice/*`
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

- **EFS bind mounts**: Services with `/mnt/efs/LMView` mounts (fastapi, nginx) cannot failover to worker node without EFS mount
- **Registry**: Single point on manager node. If manager goes down, images can't be pulled
- **Monitoring**: Most monitoring services (prometheus, loki) are 0/1 — not actively collecting
- **Flink auto-submit**: 0/1 — jobs must be submitted manually
- **Certbot**: Renewal depends on port 80 being accessible from internet
