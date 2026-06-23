# LMView — 3-Node Docker Swarm Architecture

```
╔══════════════════════════════════════════════════════════════════════════════════════════════════════════╗
║                                   LMView — Real-time Crypto Technical Analysis Platform                ║
║                                    Lambda Architecture — 3-Node Docker Swarm                          ║
╚══════════════════════════════════════════════════════════════════════════════════════════════════════════╝


                                  BINANCE DATA SOURCE
                              (WebSocket + REST API)
                              ┌─────────────────────┐
                              │  Binance            │
                              │  WSS: ticker@24hr   │  ─── WS (8 shards, 671 symbols)
                              │  WSS: depth@depth   │  ─── REST fallback (depth+trades)
                              │  WSS: aggTrade      │  ─── REST kline poll (1s→1m)
                              │  REST: klines       │
                              └──────────┬──────────┘
                                         │
                                         │ WS streams + REST polling
                                         ▼


                    NODE 1 (Manager ─ role=api)         8vCPU / 32GB / EFS mount
           ┌─────────────────────────────────────────────────────────────────────────────────┐
           │                                                                                 │
           │  ┌─────────────────────┐   ┌─────────────────────┐   ┌──────────────────────┐   │
           │  │  binance-ticker-ws  │   │  binance-kline-rest │   │  binance-depth-      │   │
           │  │  WS 8 shards →     │   │  REST poll 1s→1m    │   │  trades-rest         │   │
           │  │  Redis direct      │   │  Avro → Kafka       │   │  REST poll → Redis   │   │
           │  └─────────┬───────────┘   └──────────┬──────────┘   └──────────────────────┘   │
           │            │                          │                                         │
           │  ┌─────────▼──────────────────────────▼──────────────────────────────────────┐  │
           │  │               SERVING LAYER (FastAPI)                                     │  │
           │  │  ┌────────────┐  ┌────────────┐  ┌────────────┐  ┌─────────────────────┐  │  │
           │  │  │ REST API   │  │ WebSocket  │  │ Auth + AI  │  │ Settings + Admin    │  │  │
           │  │  │ /api/*     │  │ /api/stream │  │ /api/auth  │  │ /api/settings      │  │  │
           │  │  │ klines,    │  │ real-time   │  │ /api/ai/*  │  │ /api/admin         │  │  │
           │  │  │ ticker,    │  │ push 50ms   │  │ chat,      │  │ PostgreSQL crud     │  │  │
           │  │  │ orderbook, │  │ candles     │  │ snapshots  │  │                     │  │  │
           │  │  │ trades     │  │ ticker      │  │            │  │                     │  │  │
           │  │  └────────────┘  └────────────┘  └────────────┘  └─────────────────────┘  │  │
           │  └───────────────────────────────────────────────────────────────────────────┘  │
           │                                                                                 │
           │  ┌──────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐  ┌──────────────┐  │
           │  │ PostgreSQL│  │  InfluxDB  │  │   MinIO    │  │ Kafka-1  │  │   Nginx      │  │
           │  │ :5432     │  │  :8086     │  │  :9000-1   │  │ broker 1 │  │  :80/443     │  │
           │  │ users,    │  │  candles   │  │  Iceberg   │  │ partition│  │  TLS, HSTS   │  │
           │  │ AI chat,  │  │  90 days   │  │  objects   │  │ 0,3,6,9  │  │  reverse     │  │
           │  │ catalog   │  │  warm TS   │  │  cold      │  │          │  │  proxy       │  │
           │  └──────────┘  └────────────┘  └────────────┘  └──────────┘  └──────────────┘  │
           │                                                                                 │
           │  ┌──────────────────────┐  ┌──────────────┐  ┌────────────────────────────────┐│
           │  │  Redis Sentinel-1    │  │  Prometheus  │  │  Registry  Certbot  DuckDNS     ││
           │  │  (monitor only)      │  │  + Grafana   │  │  minio-init  (utilities)        ││
           │  └──────────────────────┘  └──────────────┘  └────────────────────────────────┘│
           └─────────────────────────────────────────────────────────────────────────────────┘

                                          │
                     ┌────────────────────┼────────────────────┐
                     │ Kafka RF=3         │ Kafka RF=3         │ Kafka RF=3
                     │ partitions         │ partitions         │ partitions
                     │ 0,3,6,9 leader    │ 1,4,7,10 leader   │ 2,5,8,11 leader
                     ▼                     ▼                     ▼


                    NODE 2 (Worker ─ role=data)         8vCPU / 32GB
           ┌─────────────────────────────────────────────────────────────────────────────────┐
           │                                                                                 │
           │  ┌──────────┐  ┌────────────┐  ┌────────────────┐  ┌────────────┐              │
           │  │ Zookeeper│  │  Kafka-2   │  │ Schema Registry│  │  Redis     │              │
           │  │ :2181    │  │  broker 2  │  │ Apicurio       │  │  MASTER    │              │
           │  │ Kafka    │  │            │  │ Avro schemas   │  │  :6379     │              │
           │  │ metadata │  │            │  │                │  │ read/write │              │
           │  └──────────┘  └────────────┘  └────────────────┘  └────────────┘              │
           │                                                                                 │
           │  ┌──────────────────────┐  ┌──────────────────────┐  ┌──────────────────────┐  │
           │  │  Flink JobManager    │  │  Flink TaskManager 1 │  │  Spark Master        │  │
           │  │  :8081 (UI)         │  │  parallelism 6 tasks  │  │  :7077 cluster       │  │
           │  │  orchestrates tasks │  │  kline agg + dedup    │  │  coordinator         │  │
           │  │  checkpoint coord   │  │  indicator compute    │  │                      │  │
           │  └──────────────────────┘  └──────────────────────┘  └──────────────────────┘  │
           │                                                                                 │
           │  ┌──────────────────────┐  ┌──────────────────────┐  ┌────────────────────┐    │
           │  │  Spark Worker 1      │  │  Kafka Exporter      │  │  Redis Sentinel-2 │    │
           │  │  executors 2GB heap  │  │  metrics → Prom      │  │  (monitor only)   │    │
           │  │  Bronze/Silver jobs  │  │                      │  │                    │    │
           │  └──────────────────────┘  └──────────────────────┘  └────────────────────┘    │
           └─────────────────────────────────────────────────────────────────────────────────┘


                    NODE 3 (Worker ─ role=compute)        8vCPU / 32GB
           ┌─────────────────────────────────────────────────────────────────────────────────┐
           │                                                                                 │
           │  ┌────────────┐  ┌──────────────────────┐  ┌──────────────────────┐             │
           │  │  Kafka-3   │  │  Flink TaskManager 2 │  │  Spark Worker 2      │             │
           │  │  broker 3  │  │  parallelism 6 tasks │  │  executors 2GB heap  │             │
           │  │            │  │  kline agg + dedup   │  │  Silver/Gold jobs    │             │
           │  │            │  │  indicator compute   │  │                      │             │
           │  └────────────┘  └──────────────────────┘  └──────────────────────┘             │
           │                                                                                 │
           │  ┌──────────────────────┐  ┌──────────────┐  ┌──────────────────────────────┐  │
           │  │  Trino               │  │  Redis       │  │  Dagster Web + Daemon        │  │
           │  │  :8083              │  │  REPLICA     │  │  (data orchestration)         │  │
           │  │  SQL engine          │  │  read-only   │  │  (optional)                  │  │
           │  │  Iceberg queries     │  │  :6379       │  │                              │  │
           │  └──────────────────────┘  └──────────────┘  └──────────────────────────────┘  │
           │                                                                                 │
           │  ┌──────────────────────┐  ┌──────────────────────┐                             │
           │  │  Loki + Promtail     │  │  Redis Sentinel-3    │                             │
           │  │  centralized logging │  │  (monitor only)      │                             │
           │  └──────────────────────┘  └──────────────────────┘                             │
           └─────────────────────────────────────────────────────────────────────────────────┘


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              DATA FLOW — LAMBDA ARCHITECTURE
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  REAL-TIME PATH (SPEED LAYER):
  ┌──────────┐    ┌─────────────────┐    ┌──────────────┐    ┌──────────┐    ┌─────────────────────┐
  │ Binance  │───►│ binance-ticker- │───►│  Redis       │───►│ FastAPI  │───►│ Browser via WS      │
  │ WS @24hr │    │ ws (N1)         │    │  Master (N2) │    │ (N1)     │    │ (React SPA)         │
  │ 8 shards │    │ parse → HSET    │    │  <1ms read   │    │ poll 50ms│    │ ~200-500ms E2E      │
  └──────────┘    └─────────────────┘    └──────────────┘    └──────────┘    └─────────────────────┘

  STREAMING PATH (SPEED LAYER):
  ┌──────────┐    ┌──────────────────┐    ┌──────────┐    ┌──────────────────┐    ┌──────────────┐
  │ Binance  │───►│ binance-kline    │───►│  Kafka   │───►│  Flink (N2,N3)  │───►│  Redis       │
  │ REST     │    │ -rest (N1)       │    │  3 nodes │    │  KeyedProcessFn │    │  Master (N2) │
  │ /klines  │    │ Avro serialize   │    │ RF=3     │    │  Candle agg 1s→1m│   │  candles     │
  └──────────┘    └──────────────────┘    └──────────┘    └──────────────────┘    └──────┬───────┘
                                                                                        │
                                                                                  ┌──────▼───────┐
                                                                                  │  InfluxDB    │
                                                                                  │  (N1)        │
                                                                                  │  90 days     │
                                                                                  └──────────────┘

  BATCH PATH (LAKEHOUSE LAYER):
  ┌──────────┐    ┌──────────┐    ┌──────────────────┐    ┌──────────────────┐    ┌──────────────┐
  │  Kafka   │───►│  Spark   │───►│  Iceberg Bronze  │───►│  Iceberg Silver  │───►│  Iceberg Gold│
  │  3 nodes │    │ (N2,N3)  │    │  (MinIO N1)      │    │  (MinIO N1)      │    │  (MinIO N1)  │
  │          │    │ SS       │    │  raw Kafka data   │    │  cleaned dedup   │    │  aggregated  │
  └──────────┘    └──────────┘    └──────────────────┘    └──────────────────┘    └──────┬───────┘
                                                                                        │
                                                                                  ┌──────▼───────┐
                                                                                  │  Trino (N3)  │
                                                                                  │  SQL engine  │
                                                                                  │  historical  │
                                                                                  └──────┬───────┘
                                                                                        │
                                                                                  ┌──────▼───────┐
                                                                                  │  FastAPI     │
                                                                                  │  overview    │
                                                                                  └──────────────┘


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              REDIS SENTINEL TOPOLOGY (3 NODE HA)
══════════════════════════════════════════════════════════════════════════════════════════════════════════

                          ┌──────────────────────────────────────────────┐
                          │         Sentinel Quorum: 2/3                │
                          │         Monitor: lmview_redis               │
                          │         failover-timeout: 30s               │
                          └──────────────────────────────────────────────┘

        N1 (api)                     N2 (data)                     N3 (compute)
  ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
  │  Redis Sentinel  │◄───────►│  Redis Sentinel  │◄───────►│  Redis Sentinel  │
  │  port 26379      │         │  port 26379      │         │  port 26379      │
  │                  │         │                  │         │                  │
  │  monitor only    │         │  monitor only    │         │  monitor only    │
  └──────────────────┘         └──────────────────┘         └──────────────────┘
           │                           │                            │
           │                           │                            │
           │                ┌──────────▼──────────┐                 │
           └────────────────►   Redis MASTER      ◄─────────────────┘
                            │   (N2)              │
                            │   read/write        │
                            │   port 6379         │
                            └──────────┬──────────┘
                                       │
                                       │ asynchronous replication
                                       ▼
                            ┌──────────────────────┐
                            │   Redis REPLICA      │
                            │   (N3)               │
                            │   read-only          │
                            │   port 6379          │
                            │   slave-read-only yes│
                            └──────────────────────┘


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              KAFKA TOPIC & PARTITION LAYOUT
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  Topic               Partitions    RF    MinISR    Retention    Size
  ─────────────────────────────────────────────────────────────────────
  crypto_ticker        12           3     2         48h          ~2GB
  crypto_klines        12           3     2         48h          ~5GB
  crypto_depth         6            3     2         48h          ~1GB
  crypto_trades        6            3     2         48h          ~1GB

  Partition distribution:
         N1 (Kafka-1)        N2 (Kafka-2)        N3 (Kafka-3)
  ┌────────────────────┐ ┌────────────────────┐ ┌────────────────────┐
  │ Leader: 0,3,6,9   │ │ Leader: 1,4,7,10  │ │ Leader: 2,5,8,11  │
  │ Follower: 1,2,     │ │ Follower: 0,2,    │ │ Follower: 0,1,    │
  │          4,5,      │ │          3,5,      │ │          3,4,      │
  │          7,8,10,11 │ │          6,8,9,11  │ │          6,7,9,10 │
  └────────────────────┘ └────────────────────┘ └────────────────────┘


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              RESOURCE ESTIMATE (per node)
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  Service               N1 (api)      N2 (data)     N3 (compute)    Replicas    HA?
  ─────────────────────────────────────────────────────────────────────────────────
  Nginx                  256M           —              —              1          ✗
  FastAPI                1G             —              —              1          ✗
  PostgreSQL             1G             —              —              1          ✗
  InfluxDB               2G             —              —              1          ✗
  MinIO                  1G             —              —              1          ✗
  binance-ticker-ws      256M           —              —              1          ✗
  binance-kline-rest     256M           —              —              1          ✗
  binance-depth-rest     256M           —              —              1          ✗
  Redis Master           —              2G             —              1          ✓ (Sentinel)
  Redis Replica          —              —              1G             1          ✓
  Redis Sentinel×3       128M           128M           128M           3          ✓
  Zookeeper              —              512M           —              1          ✗
  Kafka×3                1G             1G             1G             3          ✓ (RF=3)
  Schema Registry        —              256M           —              1          ✗
  Flink JobManager       —              1G             —              1          ✗
  Flink TaskManager×2    —              2G             2G             2          ✓
  Spark Master           —              1G             —              1          ✗
  Spark Worker×2         —              2G             2G             2          ✓
  Trino                  —              —              2G             1          ✗
  Prometheus+Grafana     1.5G           —              —              1          ✗
  Loki+Promtail          —              —              640M           1          ✗
  Kafka Exporter         —              128M           —              1          ✗
  Dagster                —              —              768M           1          ✗
  Registry               512M           —              —              1          ✗
  Certbot+DuckDNS        256M           —              —              1          ✗
  ─────────────────────────────────────────────────────────────────────────────────
  TOTAL (approx)        ~11.9GB        ~10.9GB        ~11.5GB


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              DOCKER SWARM PLACEMENT CONSTRAINTS
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  # Label nodes
  docker node update --label-add role=api      <node1-id>
  docker node update --label-add role=data     <node2-id>
  docker node update --label-add role=compute  <node3-id>

  # Example placement in docker-compose.swarm.yml
  #
  # nginx:
  #   placement:
  #     constraints: [node.labels.role == api]
  #
  # kafka-1:
  #   placement:
  #     constraints: [node.labels.role == api]
  #
  # kafka-2:
  #   placement:
  #     constraints: [node.labels.role == data]
  #
  # kafka-3:
  #   placement:
  #     constraints: [node.labels.role == compute]


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              SINGLE POINTS OF FAILURE & MITIGATION
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  Component     SPOF?     Mitigation
  ─────────────────────────────────────────────────────────────────────
  PostgreSQL    Yes       pg_dump cron → S3. Future: streaming replica
  InfluxDB      Yes       Backup volume. Future: InfluxDB Enterprise
  MinIO         Yes       Backup to S3. Future: distributed MinIO (≥4 nodes)
  Nginx         Yes       Swarm auto-restart. Future: multi-replica + shared IP
  FastAPI       Yes       Swarm auto-restart. Future: 2+ replicas + nginx upstream
  Trino         Yes       Swarm auto-restart. Data in Iceberg (not local)
  Schema Reg.   Yes       Schema in Postgres DB. Restartable
  Zookeeper     Yes       Currently 1. Future: ZK ensemble 3 nodes
  Redis Master  ✓ HA     Sentinel auto-failover to replica (N3)
  Kafka         ✓ HA     RF=3, minISR=2, tolerate 1 node loss
  Flink TM      ✓ HA     2 TMs, job can recover from checkpoint
  Spark Workers ✓ HA     2 workers, job continues if 1 dies


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              STORAGE TIERS
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  Tier          Tech            Node     Access              Latency    Retention    Size
  ─────────────────────────────────────────────────────────────────────────────────────────
  Hot cache     Redis Sentinel  N2+N3    Direct key lookup   <1ms       min-hours    ~200MB
  Warm TSDB     InfluxDB 2.7    N1       Flux queries        10-50ms    90 days      ~5GB
  Cold lake     Iceberg/MinIO   N1       Trino SQL           50-500ms   indefinite   ~5.6GB
  Relational    PostgreSQL 16   N1       SQL (asyncpg)       1-10ms     indefinite   ~500MB


══════════════════════════════════════════════════════════════════════════════════════════════════════════
                              KEY PORTS
══════════════════════════════════════════════════════════════════════════════════════════════════════════

  Port    Service         Node     Access
  ────────────────────────────────────────────
  80      Nginx HTTP      N1       Internet → redirect 443
  443     Nginx HTTPS     N1       Internet
  5000    Registry        N1       Swarm internal
  5432    PostgreSQL      N1       Internal
  6379    Redis           N2+N3    Internal
  8000    FastAPI         N1       Internal
  8081    Flink UI        N2       Internal
  8083    Trino           N3       Internal
  8086    InfluxDB        N1       Internal
  9000    MinIO API       N1       Internal
  9001    MinIO Console   N1       Internal
  9090    Prometheus      N1       Internal
  3001    Grafana         N1       Internal via Nginx
  2181    Zookeeper       N2       Internal
  8085    Schema Registry N2       Internal
  9308    Kafka Exporter  N2       Internal
  26379   Redis Sentinel  N1+N2+N3 Internal

```

---

## Node Label & Placement Config

```yaml
# docker-compose.swarm.yml — key placement config

x-placement-api: &placement-api
  placement:
    constraints: [node.labels.role == api]

x-placement-data: &placement-data
  placement:
    constraints: [node.labels.role == data]

x-placement-compute: &placement-compute
  placement:
    constraints: [node.labels.role == compute]

services:
  # ── Node 1: API/Infra ──
  nginx:
    <<: *placement-api
  fastapi-prod:
    <<: *placement-api
  postgres:
    <<: *placement-api
  influxdb:
    <<: *placement-api
  minio:
    <<: *placement-api
  kafka-1:
    <<: *placement-api
  registry:
    <<: *placement-api
  certbot-auto:
    <<: *placement-api
  duckdns-auto:
    <<: *placement-api
  redis-sentinel-1:
    <<: *placement-api

  # ── Node 2: Data/Streaming ──
  zookeeper:
    <<: *placement-data
  kafka-2:
    <<: *placement-data
  schema-registry:
    <<: *placement-data
  redis-master:
    <<: *placement-data
  redis-sentinel-2:
    <<: *placement-data
  flink-jobmanager:
    <<: *placement-data
  flink-taskmanager:
    <<: *placement-data
  spark-master:
    <<: *placement-data
  spark-worker:
    <<: *placement-data
  kafka-exporter:
    <<: *placement-data

  # ── Node 3: Compute/Analytics ──
  kafka-3:
    <<: *placement-compute
  flink-taskmanager-2:
    <<: *placement-compute
  spark-worker-2:
    <<: *placement-compute
  trino:
    <<: *placement-compute
  redis-replica:
    <<: *placement-compute
  redis-sentinel-3:
    <<: *placement-compute
  loki:
    <<: *placement-compute
  dagster-webserver:
    <<: *placement-compute
```

---

## Deploy Commands

```bash
# Label nodes
docker node update --label-add role=api      <manager-node-id>
docker node update --label-add role=data     <worker1-node-id>
docker node update --label-add role=compute  <worker2-node-id>

# Deploy stack
docker stack deploy \
  -c docker-compose.yml \
  -c docker-compose.swarm.yml \
  cryptoprice

# Verify placement
docker stack services cryptoprice --format "table {{.Name}}\t{{.Replicas}}\t{{.Ports}}"
docker service ps cryptoprice_kafka-1 --format "table {{.Name}}\t{{.Node}}"
```
