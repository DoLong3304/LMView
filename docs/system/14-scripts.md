# Scripts Reference — Operational Tooling

All operational scripts in `scripts/`, their purposes, flaws, and improvement paths.

## Script Inventory

| Script | Type | Purpose | Status |
|---|---|---|---|
| `deploy_aws_swarm.sh` | Bash (272 lines) | Full Swarm deploy: build → push → deploy | **Active, critical** |
| `auto_submit_jobs.sh` | Bash (89 lines) | Submit Flink/Spark streaming jobs | **Active, fragile** |
| `certbot_auto.sh` | Bash (98 lines) | Let's Encrypt SSL renewal | **Active** |
| `duckdns_auto.sh` | Bash (27 lines) | DuckDNS dynamic IP update | **Active** |
| `create_kafka_topics.sh` | Bash (61 lines) | Create 4 Kafka topics | One-shot |
| `submit_flink.sh` | Bash (23 lines) | Build deps.zip + submit Flink job | Redundant with auto_submit |
| `docker-reclaim.sh` | Bash (51 lines) | Disk reclamation (Spark work dirs) | WSL-specific, stale |
| `nginx_auto_reload.sh` | Bash (11 lines) | Nginx reload for cert refresh | **Active** |
| `setup_influx_retention.sh` | Bash (61 lines) | InfluxDB retention policies | One-shot, stale |
| `init_certbot.sh` | Bash (93 lines) | Initial certbot bootstrap | **Active** |
| `audit_data_coverage.py` | Python (350 lines) | Data coverage audit vs Binance top-200 | Tool, actively useful |
| `job_watchdog.py` | Python (48 lines) | Flink/Spark health → auto-resubmit | **Active, 0/1 replicas** |
| `prune_dashboards.py` | Python (124 lines) | Grafana dashboard panel cleanup | Tool |
| `run_news_sentiment_daily.py` | Python (87 lines) | News sentiment scoring job | Tool |
| `test_queries.py` | Python (32 lines) | Test PromQL expressions | Tool |
| `verify_all_via_grafana.py` | Python (186 lines) | Verify Grafana dashboards | Tool |

---

## Critical Scripts — Deep Analysis

### 1. deploy_aws_swarm.sh

**Purpose**: Complete Swarm deployment lifecycle on 2-node AWS EC2 cluster.

**Flow** (v0.28.1+):
```
Preflight checks (swarm active, node labels, .env exists)
  → Pre-build cleanup: prune dead containers + dangling images (24h) + build cache
  → Ensure registry service running
  → Build images (docker compose --profile prod build)
  → Push to local registry (tag + push custom images)
  → Render stacked compose (docker compose config)
    → Strip Swarm-incompatible keys (name, profiles, container_name, depends_on, profiles)
    → Fix port string formats
    → Rewrite image tags to registry address
  → docker stack deploy (--resolve-image never)
  → Post-deploy status output
  → Post-deploy cleanup: prune exited containers + dangling images (48h)
```

**Strengths** (v0.28.1):
- Comprehensive preflight checks (swarm, nodes, .env, compose files)
- Idempotent registry creation with timeout
- Clean compose rendering with Python inline script (YAML-aware, not sed)
- Graceful skip-build and registry-only modes
- Pre-build cleanup (prune dead containers + dangling images + build cache)
- Post-deploy cleanup (prune exited containers + old dangling images)
- Stack state snapshot + rollback on deploy failure

**Drawbacks & Bugs**:
1. **CUSTOM_IMAGES resolution is correct** — dynamic from compose config.
2. **Port normalization is safe** — Python YAML handles it, not fragile sed.
3. **Rollback exists** — snapshots pre-deploy state, auto-restores on failure.
4. **EFS path assumption** — Assumes `/mnt/efs/LMView` on all nodes. No validation.
5. **No image tag versioning** — `fastapi:latest` tag is pushed, not versioned.
   Rollback requires re-push of old code.
6. **Health check gap** — Only waits 10s after deploy. Should poll `/api/health`.
7. **Cleanup removes registry-tagged images** — `docker image prune -af` with
   `--filter until=24h` is safe, but bare `-af` removes all unused images
   including registry-tagged ones that Swarm needs with `--resolve-image never`.

**Cooperation**:
- Called from Makefile (`swarm-deploy`, `swarm-deploy-quick`, `swarm-push`)
- Depends on: docker-compose.yml, docker-compose.swarm.yml, docker-compose.ai.yml, .env
- Triggers: image builds → registry push → stack deploy
- Post-deploy: manual verification needed via `swarm-status`

### 2. auto_submit_jobs.sh

**Purpose**: Submit Flink streaming job after deploy/restart.

**Flow**:
```
Wait for Flink JobManager (port 8081)
  → Wait for TaskManager slots (poll /overview, timeout 120s)
  → Build deps.zip from src/common + src/processing/writers
  → flink run -d -m flink-jobmanager:8081 -py pipeline.py
  → Wait for Spark Master (port 8080) → skip Spark (no spark-submit in this container)
```

**Drawbacks & Bugs**:
1. **Spark job never submitted** — Script acknowledges "spark-submit not available", creating a permanent gap. Lakehouse pipeline never starts.
2. **deps.zip Python script** — The inline Python for building deps.zip has the same code duplicated in `submit_flink.sh`. No single source of truth.
3. **Flink slot timeout hardcoded** — 120s with no config env var. On slow worker node, slots may take longer.
4. **No job validation** — After `flink run`, script doesn't verify job is actually RUNNING. Could be in FAILED state.
5. **Port conflict** — `FLINK_HEALTH_URL` defaults to `127.0.0.1:8081` but `SPARK_HEALTH_URL` defaults to `127.0.0.1:8080` — Spark master actually runs on port 8080 inside container? Wait, the script checks Spark on port 8080, but Spark Master is published as 8082 (from compose → 8080 internal). This is a bug: Inside Swarm, Spark master is at `spark-master:8080` (internal) not `127.0.0.1:8080`.

**Cooperation**:
- Runs inside `auto-submit-jobs` service container (0/1 replicas currently)
- Depends on: Flink cluster healthy, `src/` code available
- Output: Flink job running on JobManager

### 3. certbot_auto.sh

**Purpose**: Manage Let's Encrypt SSL certificate lifecycle.

**Flow**:
```
Check DOMAIN/EMAIL configured
  → cleanup_broken_state (remove bootstrap certs, inconsistent archive)
  → cert_is_fresh? → Skip initial request OR issue_or_renew
  → Loop every SLEEP_SECS (default 12h):
      cert_is_fresh? → Skip OR issue_or_renew
```

**Strengths**:
- Comprehensive broken-state cleanup (3 edge cases: bootstrap files, Docker volume paths, inconsistent archive)
- HSTS marker file (`CERT_MARKER`) prevents enabling HSTS without real cert
- Graceful sleep when env vars not configured (no crash)

**Drawbacks & Bugs**:
1. **No renewal failure alert** — Logs failure silently, retries next interval. No Slack/email notification.
2. **Rate limit risk** — Certbot staging vs production environment not configurable. Failed renewals consume Let's Encrypt rate limit.
3. **certbot-auto** runs as Swarm service but `cleanup_broken_state` runs on every cycle — unnecessary I/O on success path.

**Cooperation**:
- Runs inside `certbot-auto` service container
- Depends on: nginx serving `.well-known/acme-challenge/` on port 80
- Creates: certificate files in `letsencrypt` volume
- Consumed by: nginx SSL configuration

### 4. duckdns_auto.sh

**Purpose**: Keep DuckDNS dynamic DNS record updated with current public IP.

**Flow**:
```
Check TOKEN/SUBDOMAINS configured
  → Loop every INTERVAL (default 300s):
      For each subdomain: curl duckdns.org/update?domains=X&token=Y&ip=
      → Log OK or failure
```

**Drawbacks & Bugs**:
1. **No public IP detection** — Uses `&ip=` (empty = auto-detect). If container sits behind NAT, auto-detect may get private IP. Should use `&ip=$(curl -s ifconfig.me)` or similar.
2. **No failure count threshold** — If 100 consecutive failures, still keeps trying silently. No escalation.
3. **Token in URL** — Logged to stdout on failure. Exposes `DUCKDNS_TOKEN` in logs.

**Cooperation**:
- Runs inside `duckdns-auto` service container
- Updates: DuckDNS DNS record → enables Let's Encrypt domain verification
- Independent of other services (no health check dependency)

### 5. create_kafka_topics.sh

**Purpose**: Create 4 Kafka topics with replication factor 3.

**Flow**:
```
Wait 10s for brokers
  → For each topic: kafka-topics.sh --create --if-not-exists
  → Verify topics list
  → Describe each topic
```

**Drawbacks & Bugs**:
1. **Static 10s sleep** — Should poll brokers' health instead of arbitrary sleep.
2. **Topic config hardcoded** — `retention.ms=172800000` (48h), `segment.ms=3600000` (1h) not configurable.
3. **Only for 3-broker setup** — Hardcoded replication factor 3. Won't work in single-broker dev.

**Cooperation**:
- One-shot setup required before producer or Flink start
- Depends on: all 3 Kafka brokers healthy
- Precondition for: producer, Flink jobs, Spark streaming

### 6. job_watchdog.py

**Purpose**: Monitor Flink/Spark jobs and auto-resubmit if unhealthy.

**Flow**:
```
Loop every CHECK_INTERVAL_SEC (default 300s):
  → Check Flink health: GET /jobs/overview → any RUNNING/CREATED/RESTARTING?
  → Check Spark health: GET /json/
  → If either unhealthy: bash auto_submit_jobs.sh
```

**Drawbacks & Bugs**:
1. **Currently 0/1 replicas** — Not running in production. Jobs never auto-recover.
2. **Resubmits even if Flink is fine but Spark is down** — Runs `auto_submit_jobs.sh` which only handles Flink, so Spark stays down.
3. **No back-off** — If Flink is permanently down, resubmits every 300s forever with no back-off or escalation.
4. **No health check on container** — Docker doesn't know if watchdog is working.

### 7. audit_data_coverage.py

**Purpose**: Data quality audit — compare subscribed symbols vs Binance volume-ranked top 200.

**Output**:
- Symbol comparison (alphabetical vs volume-ranked)
- Redis ticker key count
- Redis 1s/1m kline coverage
- InfluxDB 7d candle coverage
- Human-readable summary with pass/fail verdict

**Strengths**:
- Well-structured with clear sections
- Graceful degradation (handles missing redis-py, influxdb-client)
- JSON output option for automated monitoring
- Actionable recommendations

**Drawbacks & Bugs**:
1. **Redis URL hardcoded default** — `redis://localhost:6379` not valid in Swarm (should be `redis-master:6379`).
2. **InfluxDB token** — Must be passed via CLI arg, easy to miss.
3. **Not integrated into monitoring** — Runs as standalone script, not scheduled or wired to Prometheus.

---

## Cross-Script Dependency Graph

```
deploy_aws_swarm.sh
  ├── docker compose build
  ├── docker push → registry
  ├── docker stack deploy
  └── sleeping 10s

Makefile targets call deploy_aws_swarm.sh

auto_submit_jobs.sh (called from job_watchdog.py or manually)
  ├── wait flink-jobmanager:8081
  ├── build deps.zip (src/common + src/processing/writers)
  ├── flink run pipeline.py
  └── skip Spark (no spark-submit in container)

create_kafka_topics.sh (one-shot, pre-Flink)
  └── kafka-topics.sh → 4 topics with RF=3

certbot_auto.sh
  ├── cleanup_broken_state()
  ├── certbot certonly --webroot
  └── loop renewal (12h)

duckdns_auto.sh
  └── curl duckdns.org/update (5min loop)

nginx_auto_reload.sh
  └── nginx -s reload (cert renewal pickup)
```

## Critical Script Gaps

1. **No single orchestration entry point** — `deploy_aws_swarm.sh` deploys stack but auto_submit_jobs runs separately. New Swarm nodes joining mid-deployment aren't handled.
2. **No health-check-based auto-healing** — `job_watchdog.py` exists but isn't deployed (0/1). Flink job failures require manual intervention.
3. **Duplicate deps.zip logic** — Two scripts (`auto_submit_jobs.sh` line 28-44, `submit_flink.sh` line 3-28) have the same deps.zip building code. Should be a shared script.
4. **Scripts assume specific paths** — `/app/src`, `/opt/flink`, `/opt/kafka` — break if container paths change.
5. **No centralized logging** — Scripts write to stdout only. In Swarm, logs are visible via `docker service logs` but no structured format for Loki.
