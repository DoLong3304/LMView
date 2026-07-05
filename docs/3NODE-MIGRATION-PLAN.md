# 3-Node Docker Swarm Migration Plan

> **Status:** Proposal for v0.28.0+
> **Current:** 2-node Swarm (core 8vCPU/32GB + worker 4vCPU/16GB, shared EFS)
> **Target:** 3-node Swarm with dedicated roles, improved reliability, and horizontal scaling

---

## 1. Why 3 Nodes?

### Current Problems (2-node)

| Problem | Impact |
|---|---|
| Worker OOM killed services (Prometheus 2GB → 4GB fix) | Pipeline downtime, manual resubmit |
| All stateful services on single core node | Single point of failure for DBs, Redis, Kafka |
| Shared EFS bottleneck for all containers | I/O contention on config reads, checkpoint writes |
| Worker too small for Flink+Spark+Trino+monitoring | 16GB RAM regularly hits limits |
| No capacity during maintenance | Draining a node = full system downtime |

### 3-Node Benefits

```
┌────────────────────────────────────────────────────────┐
│                 3-Node Docker Swarm                      │
│                                                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐ │
│  │  Node 1       │  │  Node 2       │  │  Node 3       │ │
│  │  (core)       │  │  (data)       │  │  (compute)    │ │
│  │  8vCPU 32GB   │  │  8vCPU 32GB   │  │  8vCPU 32GB   │ │
│  │               │  │               │  │               │ │
│  │ - Nginx       │  │ - PostgreSQL  │  │ - Flink TM×2  │ │
│  │ - FastAPI     │  │ - Redis Master │  │ - Spark Worker│ │
│  │ - React SPA   │  │   + Sentinel-2 │  │ - Redis       │ │
│  │ - ai-service  │  │ - Kafka ×3    │  │   Replica     │ │
│  │ - Certbot     │  │ - InfluxDB   │  │   + Sentinel-3│ │
│  │ - DuckDNS     │  │ - MinIO      │  │ - Trino       │ │
│  │ - LiteLLM     │  │ - Zookeeper  │  │ - Dagster     │ │
│  │ - Registry    │  │ - Schema Reg │  │ - Prometheus  │ │
│  │ - Redis       │  │               │  │ - Grafana     │ │
│  │   Sentinel-1  │  │               │  │ - Loki        │ │
│  │               │  │               │  │ - Node Exp.   │ │
│  └──────────────┘  └──────────────┘  └──────────────┘ │
│                                                         │
│  Shared: EFS (/mnt/efs/LMView) — code + config only     │
│  Local: Ephemeral storage — checkpoints, data dirs      │
│  Replicated: PostgreSQL streaming, Kafka replicas        │
└─────────────────────────────────────────────────────────┘
```

### Node Roles

| Role | Label | Services | Min Spec | Ideal Spec |
|---|---|---|---|---|
| **core** | `role=core` | Nginx, FastAPI, React, ai-service, registry, certbot | 4vCPU/16GB | 8vCPU/32GB |
| **data** | `role=data` | PostgreSQL, Redis Master + Sentinel-2, Kafka, InfluxDB, MinIO, Zookeeper, Schema Registry | 4vCPU/16GB | 8vCPU/32GB |
| **compute** | `role=compute` | Flink, Spark, Trino, Dagster, Prometheus, Grafana, Loki | 4vCPU/16GB | 8vCPU/32GB |

---

## 2. Infrastructure Setup

### 2.1 EC2 Instances

```bash
# Launch 3 EC2 instances in the same VPC and security group
# Type: c6i.2xlarge (8vCPU, 32GB) — or c6i.xlarge (4vCPU, 16GB) for cost
# AMI: Ubuntu 22.04 LTS
# Storage: 100GB gp3 each
# Security group: Same as current (open Swarm ports between nodes)

# Instance 1 — Core (manager)
# Instance 2 — Data (worker)  
# Instance 3 — Compute (worker)

# Tag each instance for clarity
# Name: lmview-core, lmview-data, lmview-compute
```

### 2.2 Security Group Rules

| Protocol | Port Range | Source | Purpose |
|---|---|---|---|
| TCP | 2377 | sg-xxxxx (self) | Swarm management |
| TCP | 7946 | sg-xxxxx (self) | Swarm gossip |
| UDP | 7946 | sg-xxxxx (self) | Swarm gossip |
| UDP | 4789 | sg-xxxxx (self) | VXLAN overlay |
| TCP | 5000 | sg-xxxxx (self) | Internal registry |
| TCP | 80 | 0.0.0.0/0 | HTTP |
| TCP | 443 | 0.0.0.0/0 | HTTPS |
| TCP | 22 | your-ip/32 | SSH (admin only) |
| TCP | 5432 | sg-xxxxx (self) | PostgreSQL replication |
| TCP | 6379 | sg-xxxxx (self) | Redis replication |
| TCP | 9100 | sg-xxxxx (self) | Node exporter |

### 2.3 EFS Strategy

**Current:** Single EFS filesystem mounted on all nodes, shared for everything.
**Problem:** IOPS contention, all containers reading/writing to same NFS target.

**Proposed:**
- **EFS-1 (General Purpose):** Code, config, scripts — mounted at `/mnt/efs/LMView` on all 3 nodes
- **Local SSD (Node-local):** Stateful data — PostgreSQL data, Redis RDB/AOF, Kafka logs, InfluxDB data, MinIO data, Flink checkpoints, Spark events
  - Use Docker volumes with `driver_opts` for local bind mounts
  - Or use EBS volumes attached to each node

```yaml
# docker-compose.yml (3-node)
volumes:
  postgres-data:
    driver: local
  redis-master-data:
    driver: local
  kafka-1-data:
    driver: local
  # ... etc
```

**Why local storage for stateful data:**
- 10-100x faster than NFS (EBS gp3 = 16000 IOPS vs EFS Burst = ~7000 IOPS)
- PostgreSQL WAL writes are latency-sensitive
- Kafka needs low-latency disk for page cache
- Redis fork (for RDB save) on NFS is dangerous

**Trade-off:** State is node-local — if a node fails, services must be rescheduled with empty state. Mitigations:
- PostgreSQL: Streaming replication to data node
- Kafka: Replication factor 3 across nodes
- Redis: Sentinel with replicas on different nodes
- MinIO: Erasure coding across nodes (requires 4 nodes minimum)

### 2.4 Network Setup

```bash
# Initialize Swarm on core node
docker swarm init --advertise-addr <CORE_PRIVATE_IP>

# Get join tokens
docker swarm join-token manager  # for data node (second manager)
docker swarm join-token worker   # for compute node

# On data node:
docker swarm join --token <MANAGER_TOKEN> <CORE_IP>:2377

# On compute node:
docker swarm join --token <WORKER_TOKEN> <CORE_IP>:2377

# Apply labels
docker node update --label-add role=core    <core-node-id>
docker node update --label-add role=data    <data-node-id>
docker node update --label-add role=compute <compute-node-id>
```

---

## 3. Service Placement Strategy

### 3.1 Core Node (`role=core`)

```yaml
# docker-compose.swarm.yml
nginx-prod:
  deploy:
    placement:
      constraints: [node.labels.role == core]

fastapi-prod:
  deploy:
    placement:
      constraints: [node.labels.role == core]
    mode: replicated
    replicas: 2  # can scale to 2 on core

ai-service:
  deploy:
    placement:
      constraints: [node.labels.role == core]

certbot-auto:
  deploy:
    placement:
      constraints: [node.labels.role == core]

duckdns-auto:
  deploy:
    placement:
      constraints: [node.labels.role == core]

litellm:
  deploy:
    placement:
      constraints: [node.labels.role == core]

registry:
  deploy:
    placement:
      constraints: [node.labels.role == core]
```

### 3.2 Data Node (`role=data`)

```yaml
postgres:
  deploy:
    placement:
      constraints: [node.labels.role == data]

redis-master:
  deploy:
    placement:
      constraints: [node.labels.role == data]

redis-sentinel-2:
  deploy:
    placement:
      constraints: [node.labels.role == data]

kafka-1,2,3:
  deploy:
    placement:
      constraints:
        - node.labels.role == core   # kafka-1
        - node.labels.role == data   # kafka-2
        - node.labels.role == compute  # kafka-3

zookeeper:
  deploy:
    placement:
      constraints: [node.labels.role == data]

influxdb:
  deploy:
    placement:
      constraints: [node.labels.role == data]

minio:
  deploy:
    placement:
      constraints: [node.labels.role == data]

schema-registry:
  deploy:
    placement:
      constraints: [node.labels.role == data]
```

### 3.2b Redis HA Across 3 Nodes

| Service | Role | Node |
|---|---|---|
| `redis-master` | Read/write | data |
| `redis-replica-1` | Read-only replica | compute |
| `redis-replica-2` | Removed (design: 1 replica) | — |
| `redis-sentinel-1` | Sentinel (quorum) | core |
| `redis-sentinel-2` | Sentinel (quorum) | data |
| `redis-sentinel-3` | Sentinel (quorum) | compute |

Quorum = 2/3 sentinels → nếu data node die, master mới được bầu trên compute node.

### 3.3 Compute Node (`role=compute`)

```yaml
flink-jobmanager:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

flink-taskmanager:
  deploy:
    placement:
      constraints: [node.labels.role == compute]
    replicas: 2

spark-master:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

spark-worker:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

trino:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

dagster-webserver:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

dagster-daemon:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

prometheus:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

grafana:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

loki:
  deploy:
    placement:
      constraints: [node.labels.role == compute]

# Stream producers can run anywhere (they're stateless)
binance-ticker-ws:
  deploy:
    placement:
      constraints:
        - node.labels.role == core
        - node.labels.role == compute
```

---

## 4. Migration Steps

### Phase 1: Prepare (1-2 hours)
1. [ ] Create EBS volumes for stateful services (or use local Docker volumes)
2. [ ] Set up 3rd EC2 instance with Ubuntu 22.04
3. [ ] Install Docker, join to Swarm
4. [ ] Label nodes: `role=core`, `role=data`, `role=compute`
5. [ ] Update `scripts/setup_node.sh` for 3-node config

### Phase 2: Drain & Migrate State (2-4 hours, requires downtime)
1. [ ] Stop all services: `docker stack rm cryptoprice`
2. [ ] Dump PostgreSQL data
3. [ ] Back up Redis RDB files
4. [ ] Back up Kafka data directories
5. [ ] Back up InfluxDB data
6. [ ] Back up MinIO data
7. [ ] Copy data to appropriate nodes (local EBS)
8. [ ] Update `docker-compose.swarm.yml` with new placement constraints

### Phase 3: Deploy (30 min)
1. [ ] Deploy stack: `bash scripts/deploy_aws_swarm.sh`
2. [ ] Verify each service is on its target node
3. [ ] Run smoke tests
4. [ ] Verify DNS/SSL (certbot, duckdns)

### Phase 4: Observe (1 week)
1. [ ] Monitor memory/CPU usage on each node
2. [ ] Check Flink checkpoint stability
3. [ ] Verify Redis failover works
4. [ ] Check PostgreSQL replication
5. [ ] Monitor Prometheus scrape latency

---

## 5. Compose Changes Required

### 5.1 New File: `docker-compose.3node.yml`

```yaml
# Override file for 3-node deployment
# Deploy with:
#   docker stack deploy -c docker-compose.yml -c docker-compose.3node.yml cryptoprice

version: "3.8"

networks:
  crypto-net:
    driver: overlay
    attachable: true

volumes:
  postgres-data:
    driver: local
  redis-master-data:
    driver: local
  redis-replica-1-data:
    driver: local
  redis-replica-2-data:
    driver: local
  kafka-1-data:
    driver: local
  kafka-2-data:
    driver: local
  kafka-3-data:
    driver: local
  influxdb-data:
    driver: local
  minio-data:
    driver: local
  trino-data:
    driver: local

services:
  # ── Core Node ────────────────────────────────────────────────
  nginx-prod:
    deploy:
      placement:
        constraints: [node.labels.role == core]
        
  fastapi-prod:
    deploy:
      placement:
        constraints: [node.labels.role == core]
      replicas: 2
        
  ai-service:
    deploy:
      placement:
        constraints: [node.labels.role == core]

  # ── Data Node ────────────────────────────────────────────────
  postgres:
    deploy:
      placement:
        constraints: [node.labels.role == data]
        
  redis-master:
    deploy:
      placement:
        constraints: [node.labels.role == data]
        
  kafka-1:
    deploy:
      placement:
        constraints: [node.labels.role == data]
        
  # ... etc for all data services

  # ── Compute Node ─────────────────────────────────────────────
  flink-jobmanager:
    deploy:
      placement:
        constraints: [node.labels.role == compute]
        
  # ... etc for all compute services
```

### 5.2 Changes to `docker-compose.swarm.yml`

- Add `role=data` and `role=compute` label support alongside existing `role=core` and `role=worker`
- Keep backward compatibility with 2-node setups
- Use constraints that can match either `worker` or `compute` for flexible migration:
  ```yaml
  constraints:
    - node.labels.role == compute
  ```

### 5.3 Changes to `docker-compose.yml`

- Add `deploy.resources` to ALL services (not just some)
- Add `deploy.reservations.memory` for critical services
- Ensure all stateful services use local volumes (driver: local) by default
- Add `healthcheck` to services missing them (producer, flink-jobmanager, spark-worker, schema-registry per AGENTS.md)

---

## 6. PostgreSQL Streaming Replication Setup

For high-availability PostgreSQL across nodes:

```yaml
# docker-compose.3node.yml (add to data node)
postgres-primary:
  image: pgvector/pgvector:pg16
  deploy:
    placement:
      constraints: [node.labels.role == data]
  volumes:
    - postgres-primary-data:/var/lib/postgresql/data
  environment:
    POSTGRES_USER: ${POSTGRES_USER}
    POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
    POSTGRES_DB: ${POSTGRES_DB}

postgres-replica:
  image: pgvector/pgvector:pg16
  deploy:
    placement:
      constraints: [node.labels.role == core]  # cross-node replica
  volumes:
    - postgres-replica-data:/var/lib/postgresql/data
  depends_on:
    - postgres-primary
  # Uses pg_basebackup + streaming replication
```

**Alternative:** Use a managed PostgreSQL (RDS, Aurora) to avoid self-managing replication.

---

## 7. Deployment Script Updates

### Updated `scripts/deploy_aws_swarm.sh`

```bash
# Add --3node flag
# Use docker-compose.3node.yml as additional compose file
# Read node labels to determine which images to push
```

### Updated `scripts/setup_node.sh`

```bash
# Accept node role argument
# bash scripts/setup_node.sh --role data
```

---

## 8. Monitoring & Alerting for 3-Node

| Metric | Threshold | Action |
|---|---|---|
| Node memory > 80% | Warning | Scale up or redistribute services |
| Node CPU > 80% sustained | Warning | Check for CPU-bound tasks |
| Docker service replicas < desired | Critical | Check node health |
| PostgreSQL replication lag > 10s | Warning | Check network/replica |
| Kafka under-replicated partitions > 0 | Critical | Check broker health |
| Redis Sentinel quorum lost | Critical | Check sentinel nodes |
| EFS burst credits < 10% | Warning | Reduce I/O or move to local |

---

## 9. Cost Comparison

| Setup | Nodes | Spec | Monthly Cost (on-demand) | Monthly Cost (reserved 1yr) |
|---|---|---|---|---|
| Current 2-node | 2 | 8vCPU/32GB + 4vCPU/16GB | ~$250 | ~$160 |
| 3-node (c6i.xlarge) | 3 | 4vCPU/16GB × 3 | ~$210 | ~$135 |
| **Proposed 3-node** | **3** | **8vCPU/32GB × 2 + 8vCPU/32GB** | **~$420** | **~$270** |
| 3-node (mix) | 3 | 8vCPU/32GB + 4vCPU/16GB + 4vCPU/16GB | ~$290 | ~$185 |

**Recommended:** 8vCPU/32GB core + 8vCPU/32GB data + 4vCPU/16GB compute = ~$290/mo on-demand.

---

## 10. Rollback Plan

If 3-node migration causes issues:

1. **Quick rollback:** `docker stack deploy -c docker-compose.yml -c docker-compose.swarm.yml cryptoprice` (uses 2-node config)
2. **Data rollback:** Restore PostgreSQL from backup, Redis from RDB, Kafka from data copy
3. **Full rollback:** Terminate new node, restore 2-node EFS setup

---

## 11. Future Improvements

- **Kubernetes migration** (if team grows): Use EKS with same Lambda architecture
- **Managed services:** Replace self-managed Kafka with MSK, PostgreSQL with RDS
- **Multi-region:** Active-passive in us-west-2 for DR
- **GPU node:** For local LLM inference (replace LiteLLM proxy)
- **CI/CD pipeline:** GitHub Actions building and pushing to ECR
- **Terraform:** Infrastructure-as-code for the entire AWS setup
