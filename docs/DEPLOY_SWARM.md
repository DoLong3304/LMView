# LMView Docker Swarm Deployment Guide

**Multi-Node AWS EC2 Deployment for Production**

This guide covers deploying LMView to a Docker Swarm cluster spanning multiple EC2 instances with shared EFS storage.

---

## Architecture Overview

LMView uses a 2-node Swarm architecture optimized for cost and performance:

| Node | Role | Resources | Services |
|------|------|-----------|----------|
| **Core Node** | Manager | 8 vCPU, 32 GB RAM | Data storage, messaging, API, frontend, AI services |
| **Worker Node** | Worker | 4 vCPU, 16 GB RAM | Compute (Flink, Spark, Trino), monitoring, orchestration |

**Shared Storage:** EFS mounted at `/mnt/efs/LMView` on both nodes for code and config sync.

**Service Distribution:**
- **Core node (25 GB budget):** Kafka cluster, Redis Sentinel, PostgreSQL, InfluxDB, MinIO, FastAPI, Nginx, Producer, LiteLLM, FinBERT
- **Worker node (13 GB budget):** Flink (2 TaskManagers), Spark (master + 2 workers), Trino, Dagster, Prometheus, Grafana, Loki

---

## Prerequisites

### Hardware Requirements

**Core Node (Manager):**
- 8 vCPU (minimum 4)
- 32 GB RAM (minimum 24 GB)
- 100 GB root volume + EFS mount
- AWS EC2 instance type: `t3.2xlarge` or similar

**Worker Node:**
- 4 vCPU (minimum 2)
- 16 GB RAM (minimum 12 GB)
- 50 GB root volume + EFS mount
- AWS EC2 instance type: `t3.xlarge` or similar

### AWS Infrastructure

**1. VPC and Security Groups**

Both instances must be in the same VPC and security group allowing:

| Port | Protocol | Direction | Purpose |
|------|----------|-----------|---------|
| 2377 | TCP | Ingress | Swarm management (between nodes) |
| 7946 | TCP | Ingress | Swarm gossip (between nodes) |
| 7946 | UDP | Ingress | Swarm gossip (between nodes) |
| 4789 | UDP | Ingress | VXLAN overlay network (between nodes) |
| 5000 | TCP | Ingress | Local Docker registry (between nodes) |
| 80 | TCP | Ingress | HTTP (public) |
| 443 | TCP | Ingress | HTTPS (public) |
| 8080 | TCP | Ingress | FastAPI direct (optional, internal/admin) |
| 22 | TCP | Ingress | SSH (admin access) |

**2. EFS File System**

Create an EFS file system in the same region and attach to both EC2 instances:

```bash
# On both nodes, install EFS utils
sudo apt-get update
sudo apt-get install -y amazon-efs-utils

# Mount EFS (replace fs-xxxxx with your EFS ID)
sudo mkdir -p /mnt/efs/LMView
sudo mount -t efs -o tls fs-xxxxx:/ /mnt/efs/LMView

# Persist mount in /etc/fstab
echo "fs-xxxxx:/ /mnt/efs/LMView efs _netdev,tls 0 0" | sudo tee -a /etc/fstab
```

**Verify mount:**
```bash
df -h | grep /mnt/efs/LMView
```

**3. Docker Installation**

On both nodes:
```bash
# Install Docker Engine 24+ or Docker Desktop 4+
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add ubuntu user to docker group
sudo usermod -aG docker ubuntu
newgrp docker

# Verify installation
docker --version
docker info
```

---

## Pre-Deployment Setup

### 1. Initialize Docker Swarm

**On the core node (manager):**
```bash
# Get private IP address
MANAGER_IP=$(hostname -I | awk '{print $1}')
echo "Manager IP: $MANAGER_IP"

# Initialize Swarm with advertise address
docker swarm init --advertise-addr $MANAGER_IP
```

**Copy the join token** from output (looks like):
```
docker swarm join --token SWMTKN-1-xxxxx <MANAGER_IP>:2377
```

**On the worker node:**
```bash
# Paste and run the join command from manager output
docker swarm join --token SWMTKN-1-xxxxx <MANAGER_IP>:2377
```

**Verify cluster:**
```bash
# On manager node
docker node ls
```

Expected output:
```
ID         HOSTNAME         STATUS  AVAILABILITY  MANAGER STATUS
xxx *      ip-172-31-21-135 Ready   Active        Leader
yyy        ip-172-31-9-171  Ready   Active
```

### 2. Configure Node Labels

Labels control service placement (which node runs which services).

**On the manager node:**
```bash
# Get node IDs
MANAGER_ID=$(docker node ls --filter "role=manager" -q)
WORKER_ID=$(docker node ls --filter "role=worker" -q)

# Set labels
docker node update --label-add role=core $MANAGER_ID
docker node update --label-add role=worker $WORKER_ID

# Verify labels
docker node inspect $MANAGER_ID | grep -A 5 Labels
docker node inspect $WORKER_ID | grep -A 5 Labels
```

### 3. Configure Insecure Registry

Each node's Docker daemon must trust the local registry at `<MANAGER_IP>:5000`.

**On BOTH nodes, run:**
```bash
# Get manager private IP (run on manager first to get IP)
MANAGER_IP="172.31.21.135"  # Replace with actual manager IP

# Run setup script
cd /mnt/efs/LMView
sudo bash scripts/setup_swarm_node.sh $MANAGER_IP

# Restart Docker daemon
sudo systemctl restart docker

# Verify configuration
cat /etc/docker/daemon.json
```

Expected content:
```json
{
  "insecure-registries": ["172.31.21.135:5000"]
}
```

### 4. Clone Repository and Configure Environment

**On the manager node** (worker will access via EFS):
```bash
cd /mnt/efs
git clone https://github.com/DoLong3304/LMView.git
cd LMView

# Copy and configure environment
cp .env.example .env
nano .env  # Edit with production values
```

**Critical environment variables:**

```bash
# Security tokens (generate strong values)
SECRET_KEY="<random-64-char-hex>"
JWT_SECRET_KEY="<random-64-char-hex>"

# Database passwords
POSTGRES_PASSWORD="<strong-password>"
INFLUXDB_ADMIN_PASSWORD="<strong-password>"

# MinIO credentials
MINIO_ROOT_PASSWORD="<strong-password>"

# Monitoring access
MONITORING_USER="admin"
MONITORING_PASSWORD="<strong-password>"

# SSL/Domain (for production HTTPS)
CERTBOT_DOMAIN="your-domain.duckdns.org"
CERTBOT_EMAIL="your-email@example.com"
DUCKDNS_TOKEN="<duckdns-token>"

# Default admin account (created at startup)
DEFAULT_ADMIN_EMAIL="admin@lmview.local"
DEFAULT_ADMIN_INITIAL_PASSWORD="<strong-password>"
DEFAULT_ADMIN_DISPLAY_NAME="Admin"
DEFAULT_ADMIN_USERNAME="admin"

# AI/LLM API keys (optional, for AI features)
DASHSCOPE_API_KEY="<your-key>"  # DashScope International
DEEPSEEK_API_KEY="<your-key>"   # DeepSeek fallback
```

**Security checklist:**
- [ ] All passwords are strong (16+ chars, mixed case, numbers, symbols)
- [ ] All secret keys are random (use `openssl rand -hex 32`)
- [ ] `.env` file permissions: `chmod 600 .env`
- [ ] Never commit `.env` to version control

---

## Deployment

### Initial Deployment

**From the manager node:**
```bash
cd /mnt/efs/LMView

# Deploy the stack (builds images, pushes to registry, deploys)
bash scripts/deploy_aws_swarm.sh
```

**What the script does:**
1. Verifies Swarm is active
2. Checks node labels (role=core, role=worker)
3. Creates local Docker registry at `<MANAGER_IP>:5000`
4. Builds all custom images with prod profile
5. Tags and pushes custom images to local registry
6. Rewrites image references in compose config
7. Deploys stack with `docker stack deploy`

**Deployment takes 5-10 minutes.** Services start in dependency order.

### Update Deployment (Without Rebuild)

When you change configuration or `.env` values only:
```bash
bash scripts/deploy_aws_swarm.sh --skip-build
```

### Rebuild and Deploy

When you change code or Dockerfiles:
```bash
bash scripts/deploy_aws_swarm.sh --build
```

---

## Verification

### 1. Check Service Status

```bash
# List all services
docker stack services cryptoprice

# Expected: 40/41 services running (ai-service intentionally disabled)
```

**Healthy output:**
```
NAME                        REPLICAS  IMAGE                              PORTS
cryptoprice_fastapi-prod    1/1       172.31.21.135:5000/cryptoprice/...
cryptoprice_nginx-prod      1/1       172.31.21.135:5000/cryptoprice/...
cryptoprice_producer        1/1       172.31.21.135:5000/cryptoprice/...
...
```

**Check task distribution:**
```bash
docker stack ps cryptoprice --filter "desired-state=running" --format "table {{.Name}}\t{{.Node}}\t{{.CurrentState}}"
```

**Expected:**
- Core node: ~20 services (Kafka, Redis, PostgreSQL, FastAPI, Nginx, Producer, LiteLLM)
- Worker node: ~20 services (Flink, Spark, Trino, Dagster, monitoring)

### 2. Check for Failed Services

```bash
# Show failed tasks
docker stack ps cryptoprice --filter "desired-state=running" | grep -v "Running"

# View service logs
docker service logs cryptoprice_fastapi-prod --tail 50
docker service logs cryptoprice_producer --tail 50
docker service logs cryptoprice_flink-jobmanager --tail 50
```

**Common issues:**
- `Exit 137` = OOM killed (increase memory limit)
- `Exit 1` = Application error (check logs)
- `No such image` = Registry not configured or image not pushed

### 3. Test API Endpoints

```bash
# Health check (should return {"status": "healthy"})
curl -f https://lmview.duckdns.org/api/health

# Get ticker data
curl -f https://lmview.duckdns.org/api/ticker | jq '.[0]'

# List symbols
curl -f https://lmview.duckdns.org/api/symbols | jq 'length'
```

### 4. Test WebSocket Real-Time Updates

Open browser to `https://lmview.duckdns.org`:
1. Verify chart loads
2. Check toolbar price updates in real-time
3. Open browser dev console → Network → WS tab
4. Verify WebSocket connection established

### 5. Check Resource Usage

**On core node:**
```bash
docker stats --no-stream | head -20
```

**Expected:** <80% memory usage (21 GB free of 32 GB)

**On worker node (via SSH):**
```bash
ssh -i ~/.ssh/lmview-key ubuntu@<WORKER_IP>
docker stats --no-stream | head -20
```

**Expected:** <80% memory usage (3 GB free of 16 GB)

### 6. Monitor for Stability

Watch service status for 5 minutes:
```bash
watch -n 5 'docker stack ps cryptoprice --filter "desired-state=running" --format "table {{.Name}}\t{{.CurrentState}}" | head -50'
```

**Expected:** All services stay "Running", no unexpected restarts.

---

## Management Commands

### Service Logs

```bash
# Tail logs for a service
docker service logs -f cryptoprice_fastapi-prod

# Last 100 lines
docker service logs --tail 100 cryptoprice_producer

# Filter by time
docker service logs --since 10m cryptoprice_flink-taskmanager
```

### Scale Services

```bash
# Scale Flink TaskManagers (already 2 by default)
docker service scale cryptoprice_flink-taskmanager=3

# Scale Spark workers
docker service scale cryptoprice_spark-worker=3
```

### Restart a Service

```bash
# Force update (restarts all replicas)
docker service update --force cryptoprice_fastapi-prod
```

### Remove Stack

```bash
# Stop all services (preserves volumes)
docker stack rm cryptoprice

# Wait 30 seconds for cleanup
sleep 30

# Redeploy
bash scripts/deploy_aws_swarm.sh
```

### Clean Up Volumes (DESTRUCTIVE)

**⚠️ WARNING:** This deletes all data (databases, MinIO, Redis, etc.)

```bash
# List volumes
docker volume ls | grep cryptoprice

# Remove all (USE WITH CAUTION)
docker volume ls -q | grep cryptoprice | xargs docker volume rm
```

---

## Troubleshooting

### Services Won't Start on Worker Node

**Symptom:** Services placed on worker node show "No such file or directory" errors.

**Cause:** Volume mounts not using absolute EFS paths, or EFS not mounted on worker.

**Fix:**
1. Verify EFS mounted on worker: `ssh ubuntu@<WORKER_IP> df -h | grep /mnt/efs`
2. Check `docker-compose.swarm.yml` has absolute paths `/mnt/efs/LMView/...`
3. Redeploy: `docker stack rm cryptoprice && sleep 30 && bash scripts/deploy_aws_swarm.sh`

### litellm Service OOM Killed (Exit 137)

**Symptom:** `docker service ps cryptoprice_litellm` shows repeated Exit 137.

**Cause:** Memory limit too low (2GB insufficient for LiteLLM proxy).

**Fix:** Already fixed in `docker-compose.swarm.yml` (4GB limit). Redeploy.

### auto-submit-jobs Fails with "Connection Refused"

**Symptom:** Job submission script can't reach Flink or Spark.

**Cause:** Services not using DNS service names, or jobs starting before Flink/Spark ready.

**Fix:**
1. Verify `SCHEMA_REGISTRY_URL` uses `http://schema-registry:8080` (not hardcoded IP)
2. Check Flink health: `curl http://localhost:8081/overview` (from manager node with port forward)
3. Service logs: `docker service logs cryptoprice_flink-jobmanager`

### Image Pull Errors: "image not found"

**Symptom:** Services fail with "pull access denied" or "image not found".

**Cause:** Insecure registry not configured on worker node, or images not pushed.

**Fix:**
1. On worker node: `sudo cat /etc/docker/daemon.json` → verify `insecure-registries`
2. Restart Docker: `sudo systemctl restart docker`
3. On manager: `curl http://<MANAGER_IP>:5000/v2/_catalog` → verify images listed
4. Redeploy: `bash scripts/deploy_aws_swarm.sh --build`

### Kafka Brokers Fail to Start

**Symptom:** Kafka services restart loop with "Broker failed to start".

**Cause:** Volume mount issues, JMX config missing, or insufficient memory.

**Fix:**
1. Check volumes: `docker service inspect cryptoprice_kafka-1 --format '{{json .Spec.TaskTemplate.ContainerSpec.Mounts}}'`
2. Verify JMX config exists: `ls /mnt/efs/LMView/config/jmx`
3. Check logs: `docker service logs cryptoprice_kafka-1 --tail 100`

### Services Scheduled on Wrong Node

**Symptom:** Compute services running on core node, or data services on worker.

**Cause:** Node labels not set correctly.

**Fix:**
```bash
# Check labels
docker node ls
docker node inspect <node-id> | grep -A 5 Labels

# Fix labels
MANAGER_ID=$(docker node ls --filter "role=manager" -q)
WORKER_ID=$(docker node ls --filter "role=worker" -q)
docker node update --label-add role=core $MANAGER_ID
docker node update --label-add role=worker $WORKER_ID

# Redeploy
docker stack rm cryptoprice && sleep 30 && bash scripts/deploy_aws_swarm.sh
```

---

## Maintenance

### Backup Data Volumes

```bash
# Backup all named volumes
for vol in $(docker volume ls -q | grep cryptoprice); do
  docker run --rm -v $vol:/data -v $(pwd):/backup alpine \
    tar czf /backup/${vol}.tar.gz -C /data .
done
```

### Update Application Code

```bash
cd /mnt/efs/LMView
git pull origin main
bash scripts/deploy_aws_swarm.sh --build
```

### Monitor Logs Centrally

Access Grafana at `https://lmview.duckdns.org/grafana/`:
- Username: `admin`
- Password: From `GRAFANA_ADMIN_PASSWORD` in `.env`

**Pre-configured dashboards:**
- System Overview
- FastAPI Logs
- Kafka Health
- Flink Monitoring
- Spark Jobs
- Redis Metrics

### SSL Certificate Renewal

Handled automatically by `certbot-auto` service (runs every 12 hours).

**Manual renewal:**
```bash
docker service logs cryptoprice_certbot-auto
# Check for renewal success or errors
```

---

## Performance Tuning

### Adjust Memory Limits

Edit `docker-compose.swarm.yml` and update service:
```yaml
services:
  fastapi-prod:
    deploy:
      resources:
        limits:
          memory: 1G  # Increase from 512M
```

Redeploy:
```bash
bash scripts/deploy_aws_swarm.sh --skip-build
```

### Scale Horizontally

**Add more worker nodes:**
1. Launch new EC2 instance
2. Mount EFS at `/mnt/efs/LMView`
3. Install Docker
4. Configure insecure registry
5. Join Swarm: `docker swarm join --token <WORKER_TOKEN> <MANAGER_IP>:2377`
6. Set label: `docker node update --label-add role=worker <new-node-id>`
7. Scale services: `docker service scale cryptoprice_flink-taskmanager=3`

### Increase Parallelism

Edit Flink/Spark config in `docker-compose.yml`:
```yaml
environment:
  FLINK_PARALLELISM: 16  # Increase from 12
```

---

## Security Hardening

### Firewall Rules

On both nodes, restrict non-essential ports:
```bash
# Allow only necessary traffic
sudo ufw allow 22/tcp    # SSH
sudo ufw allow 80/tcp    # HTTP
sudo ufw allow 443/tcp   # HTTPS
sudo ufw allow from <MANAGER_IP> to any port 2377  # Swarm
sudo ufw allow from <WORKER_IP> to any port 2377
sudo ufw enable
```

### Secrets Management

Use Docker secrets for production:
```bash
# Create secret
echo "my-secret-password" | docker secret create postgres_password -

# Update service
docker service update \
  --secret-add postgres_password \
  cryptoprice_postgres
```

### Network Encryption

Swarm overlay networks are encrypted by default (`--opt encrypted`). Verify:
```bash
docker network inspect cryptoprice_crypto-net | grep Encrypted
```

---

## Workload Distribution Summary

### Core Node (role=core)
**Memory budget: ~25 GB of 32 GB**

| Service | Memory | Count | Purpose |
|---------|--------|-------|---------|
| Kafka brokers | 1G each | 3 | Message streaming |
| Redis cluster | 2.5G each | 6 | Hot cache (master + 2 replicas + 3 sentinels) |
| PostgreSQL | 512M | 1 | Auth/AI/settings persistence |
| InfluxDB | 4G | 1 | Time-series warm storage |
| MinIO | 1G | 1 | Object storage (Iceberg) |
| Zookeeper | 512M | 1 | Kafka coordination |
| Schema Registry | 512M | 1 | Avro schema management |
| FastAPI | 512M | 1 | API server |
| Nginx | 256M | 1 | Reverse proxy + frontend |
| Producer | 1.5G | 1 | Exchange data ingestion |
| LiteLLM | 4G | 1 | LLM proxy |
| FinBERT | 4G | 1 | News sentiment NLP |

### Worker Node (role=worker)
**Memory budget: ~13 GB of 16 GB**

| Service | Memory | Count | Purpose |
|---------|--------|-------|---------|
| Flink JobManager | 1.5G | 1 | Stream processing coordinator |
| Flink TaskManager | 3.5G each | 2 | Stream processing workers |
| Spark Master | 1.5G | 1 | Batch processing coordinator |
| Spark Workers | 1.5G each | 2 | Batch processing workers |
| Trino | 2G | 1 | SQL query engine |
| Dagster Webserver | 512M | 1 | Orchestration UI |
| Dagster Daemon | 512M | 1 | Orchestration scheduler |
| Prometheus | 1.5G | 1 | Metrics storage |
| Grafana | 256M | 1 | Dashboards UI |
| Loki | 512M | 1 | Log aggregation |
| Promtail | 256M | 1 | Log shipping |
| Exporters | 128M each | 3 | Metrics collection |

---

## Additional Resources

- **Main Documentation:** `docs/SYSTEM.md` — Full technical reference
- **Changelog:** `docs/CHANGELOG.md` — Version history
- **AI Features:** `docs/ai/` — AI/ML architecture
- **Deployment Scripts:** `scripts/deploy_aws_swarm.sh`, `scripts/setup_swarm_node.sh`
- **GitHub Repository:** https://github.com/DoLong3304/LMView

---

## Support

For issues or questions:
1. Check `docker service logs <service-name>`
2. Review this troubleshooting section
3. Open GitHub issue: https://github.com/DoLong3304/LMView/issues
4. Include: service logs, `docker node ls`, `docker stack ps cryptoprice`
