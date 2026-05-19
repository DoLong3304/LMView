# Monitoring Plan - MinIO / Trino / Redis / Kafka / Spark

> **Status:** Planned  
> **Date:** 2026-05-15  
> **Services:** MinIO, Trino, Redis Sentinel HA, Kafka HA, Spark  
> **Stack:** Prometheus (scraping) + Grafana (visualization)

---

## 1. Tổng quan

Mục tiêu: Import 5 Grafana dashboard cho MinIO, Trino, Redis, Kafka, Spark. Mỗi dashboard backed bởi một exporter endpoint cung cấp đúng metrics cần thiết.

**Sơ đồ kiến trúc monitoring mới:**

```
┌──────────────────────────────────────────────────────────────────────┐
│                     Prometheus (:9090)                                │
│  scrape: minio:9000, trino:8080, redis-exporter:9121,               │
│          kafka-{1,2,3}:9999, spark-master:8090, spark-worker:8091   │
└───────────────────────┬──────────────────────────────────────────────┘
                        │ metrics
┌───────────────────────▼──────────────────────────────────────────────┐
│  Grafana (:3001)                                                     │
│  5 new dashboards: minio / trino / redis / kafka-jvm / spark         │
└──────────────────────────────────────────────────────────────────────┘

Exporter endpoints:
  MinIO native:    minio:9000/minio/v2/metrics/cluster  (auth: public)
  Trino JMX Agent: trino:9404/metrics                   (JMX→Prometheus)
  Redis Exporter:  redis-exporter:9121                  (Redis INFO)
  Kafka JMX Agent: kafka-{1,2,3}:9999/metrics          (JMX→Prometheus)
  Spark Servlet:   spark-master:8090/metrics/master/prometheus
                   spark-worker:8091/metrics/prometheus
```

---

## 2. Chi tiết từng Service

### 2.1 MinIO

**Exporter:** Native Prometheus endpoint (không cần extra container)  
**Endpoint:** `http://minio:9000/minio/v2/metrics/cluster`  
**Auth:** `MINIO_PROMETHEUS_AUTH_TYPE=public` (trong docker-compose)  
**Scrape path:** `/minio/v2/metrics/cluster`

**Metrics quan trọng:**

| Metric | Ý nghĩa | Alert threshold |
|---|---|---|
| `minio_cluster_disk_storage_used_bytes` | Tổng disk usage | > 80% capacity |
| `minio_cluster_disk_storage_available_bytes` | Disk còn trống | < 20% |
| `minio_cluster_disk_utilization_percent` | Disk utilization % | > 80% |
| `minio_s3_requests_total` | Tổng S3 requests theo operation | rate/sec |
| `minio_s3_requests_errors_total` | S3 request errors | > 1% error rate |
| `minio_s3_requests_success_total` | Successful S3 requests | rate/sec |
| `minio_s3_latency_seconds` | S3 operation latency histogram | P95 > 500ms |
| `minio_s3_traffic_bytes_total` | S3 traffic in/out | network saturation |
| `minio_system_cpu_usage` | CPU usage của MinIO process | > 80% |
| `minio_system_net_bytes_total` | Network I/O (rx/tx) | > 1 Gbps |
| `minio_bucket_object_count` | Số objects per bucket | growth rate |
| `minio_heal_time_last_activity` | Thời gian heal gần nhất | stale = problem |
| `minio_node_drive_performance` | Drive latency per node | > 100ms |

**Dashboard panels dự kiến:** Cluster uptime, CPU, Memory, Disk I/O, Network throughput, S3 request rate, S3 error rate, S3 latency P50/P95/P99, Disk utilization %, Bucket object counts, Heal activity, Per-node performance.

**Lý do:** MinIO là cold storage cho Iceberg Parquet files. Disk saturation → Spark job fail. S3 error rate tăng → data pipeline stall. Latency spike → Trino query chậm.

---

### 2.2 Trino

**Exporter:** JMX Prometheus Java Agent (bitnami/jmx-exporter) chạy bên trong Trino JVM  
**Config:** `config/jmx/trino-442.yaml`  
**JMX Agent Port:** 9404  
**Scrape path:** `/metrics`  
**Cách hook:** Thêm `-javaagent` vào `JVM_EXTRA_OPTS` trong Trino entrypoint  
**Volume mount:** `config/jmx/trino-442.yaml:/etc/trino/jmx-config.yaml:ro`

**Metrics quan trọng:**

| Metric | Ý nghĩa | Alert threshold |
|---|---|---|
| `jvm_memory_bytes_used{area="heap"}` | Heap memory đang dùng | > 80% max |
| `jvm_memory_bytes_max{area="heap"}` | Heap max | — |
| `jvm_gc_collection_seconds_count` | Số lần GC chạy | spike = problem |
| `jvm_gc_collection_seconds_sum` | Tổng thời gian GC | > 5s/min = problem |
| `trino_executor_active_count` | Active executor threads | near max = saturated |
| `trino_executor_queued_count` | Tasks queued | > 10 = backlog |
| `trino_scheduler_queued_queries` | Queries đang queue | > 50 = bottleneck |
| `trino_query_manager_running_queries` | Queries đang chạy | max ~100 |
| `trino_query_manager_completed_queries_total` | Completed queries | rate/sec |
| `trino_query_manager_failed_queries_total` | Failed queries | > 1% = problem |
| `trino_query_manager_queued_queries` | Queries đang đợi | growing = problem |
| `trino_query_execution_time_seconds` | Query execution time distribution | P95 > 30s |
| `trino_query_queue_time_seconds` | Query queue wait time | P95 > 10s |
| `trino_cluster_idle_nodes` | Idle worker nodes | 0 = all busy |
| `trino_cluster_running_dql` | Running SELECT queries | — |
| `trino_cluster_running_dml` | Running INSERT/UPDATE | — |
| `trino_catalog_memory_bytes` | Memory per Iceberg catalog | — |

**Dashboard panels dự kiến:** Query rate (DML/DQL/DDL), success vs failure ratio, active/queued/running queries, executor threads, memory heap, GC time, query execution time P50/P95/P99, query queue wait time, failed queries by error type, worker node status, catalog memory.

**Lý do:** Trino là query engine cho historical data. Query queue tăng → user complaints. GC pause > 5s → query timeout. Memory exhaustion → OOM crash.

---

### 2.3 Redis Sentinel HA

**Exporter:** `redis_exporter` (oliver006/redis_exporter:v1.61) — sidecar container riêng  
**Endpoint:** `http://redis-exporter:9121`  
**Scrape path:** `/metrics`  
**Monitor target:** `redis-master:6379` (Sentinel tự động failover → master luôn là node active)

**Metrics quan trọng:**

| Metric | Ý nghĩa | Alert threshold |
|---|---|---|
| `redis_up` | Redis connectivity (1=up) | 0 = down |
| `redis_memory_used_bytes` | Memory đang dùng | > 2GB (config max) |
| `redis_memory_max_bytes` | Max memory configured | — |
| `redis_memory_peak_bytes` | Peak memory từng dùng | — |
| `redis_connected_clients` | Active client connections | > 1000 = saturated |
| `redis_blocked_clients` | Clients blocked on BLPOP/BRPOP | > 0 = slow consumer |
| `redis_rejected_connections_total` | Rejected connections (maxclients) | > 0 = hit limit |
| `redis_instantaneous_ops_per_sec` | Current QPS | — |
| `redis_keyspace_keys_total` | Tổng keys per DB | sudden drop = data loss |
| `redis_keyspace_expires_keys_total` | Keys có TTL | — |
| `redis_commands_total` | Commands processed (by command) | — |
| `redis_commands_duration_seconds_total` | Command latency | P99 > 10ms |
| `redis_net_input_bytes_total` | Bytes received | — |
| `redis_net_output_bytes_total` | Bytes sent | — |
| `redis_aof_last_write_status` | AOF write status | 0 = FAIL |
| `redis_rdb_changes_since_last_save` | Changes since last RDB save | — |
| `redis_sentinel_master_slaves` | Slaves connected per master | < 2 = replication lag |
| `redis_sentinel_master_ok_slaves` | Reachable slaves | < 2 = at risk |
| `redis_sentinel_master_sentinels` | Sentinel count | < 3 = quorum risk |
| `redis_sentinel_master_quorum` | Required quorum | — |

**Dashboard panels dự kiến:** Redis uptime, Memory used vs max vs peak, Memory fragmentation ratio, Connected clients, Blocked clients, Rejected connections, Key count per DB (1m interval), Key expiry rate, Commands/sec, Command latency P95, Slowlog entries, Network I/O, AOF/RDB status, Sentinel health (masters/slaves/sentinels), Replication lag.

**Lý do:** Redis là hot cache cho 1s/1m candles. Memory saturation → LRU evict active data → chart miss data. Replication lag → replica stale data. Client connection saturation → new connections refused → FastAPI fails.

---

### 2.4 Kafka HA (JVM metrics — bổ sung cho kafka-exporter)

**Exporter:** JMX Prometheus Java Agent chạy bên trong Kafka broker JVM  
**Config:** `config/jmx/kafka-17x.yaml`  
**JMX Agent Port:** 9999 (mỗi broker)  
**Scrape paths:** `kafka-1:9999/metrics`, `kafka-2:9999/metrics`, `kafka-3:9999/metrics`  
**Cách hook:** Thêm `-javaagent` vào `KAFKA_OPTS` trong docker-compose

**Lưu ý:** `kafka-exporter` (danielqsj) đã có sẵn, cung cấp consumer lag, topic metrics. JMX agent bổ sung thêm JVM-level metrics (heap, GC, threads, network).

**Metrics quan trọng (JVM):**

| Metric | Ý nghĩa | Alert threshold |
|---|---|---|
| `jvm_memory_bytes_used{area="heap"}` | Heap used | > 80% max |
| `jvm_memory_bytes_max{area="heap"}` | Heap max | — |
| `jvm_gc_collection_seconds_count` | GC count by collector | spike = problem |
| `jvm_gc_collection_seconds_sum` | Total GC time | > 10s/min = problem |
| `jvm_threads_live_threads` | Live threads | growing = leak |
| `jvm_threads_peak_threads` | Peak threads | — |
| `jvm_threads_deadlocked_threads` | Deadlocked threads | > 0 = critical |
| `kafka_server_BrokerTopicMetrics_MessagesInPerSec` | Messages in/sec | — |
| `kafka_server_BrokerTopicMetrics_BytesInPerSec` | Bytes in/sec | network saturation |
| `kafka_server_BrokerTopicMetrics_BytesOutPerSec` | Bytes out/sec | — |
| `kafka_server_BrokerTopicMetrics_FailedProduceRequestsPerSec` | Failed produce | > 0 |
| `kafka_server_BrokerTopicMetrics_FailedFetchRequestsPerSec` | Failed fetch | > 0 |
| `kafka_server_RequestMetrics_Latency` | Request latency (P50/P95/P99) | P99 > 100ms |
| `kafka_server_RequestHandlerPoolMetrics_RequestHandlerAvgIdlePercent` | Handler idle % | < 20% = saturated |
| `kafka_log_LogEndOffset` | Log end offset per partition | lag indicator |
| `kafka_cluster_partition_under_replicated` | Under-replicated partitions | > 0 = critical |
| `kafka_cluster_partition_offline` | Offline partitions | > 0 = critical |

**Dashboard panels dự kiến:** JVM Heap used/max, Heap utilization %, GC count/time, Live threads, Deadlocked threads, Messages in/sec per broker, Produce/fetch error rate, Request latency P50/P95/P99, Handler idle %, Under-replicated partitions, Offline partitions, Network I/O bytes.

**Lý do:** Kafka JVM heap exhaustion → broker OOM → data pipeline stall. GC pause > 100ms → produce latency spike. Under-replicated partitions → data at risk. Handler saturation → requests queued.

---

### 2.5 Spark

**Exporter:** Prometheus Servlet (Spark native, bật qua `metrics.properties`)  
**Config:** `config/spark/metrics.properties` (mount vào `$SPARK_HOME/conf/`)  
**Scrape paths:**  
  - Master: `spark-master:8090/metrics/master/prometheus`  
  - Worker: `spark-worker:8091/metrics/prometheus`  
**Cách hook:** Mount `metrics.properties` vào container, export `SPARK_CONF_DIR`

**Metrics quan trọng:**

| Metric | Ý nghĩa | Alert threshold |
|---|---|---|
| `spark_master_apps` | Applications registered | — |
| `spark_master_apps_completed` | Completed applications | — |
| `spark_master_apps_failed` | Failed applications | growing = problem |
| `spark_master_workers` | Active workers | 0 = no workers |
| `spark_master_cores` | Total cores registered | — |
| `spark_master_memory_mb` | Total memory registered | — |
| `spark_executor_running_tasks` | Running tasks per executor | — |
| `spark_executor_completed_tasks_total` | Completed tasks | rate |
| `spark_executor_failed_tasks_total` | Failed tasks | > 0 = job failure |
| `spark_shuffle_read_bytes_total` | Shuffle data read | — |
| `spark_shuffle_write_bytes_total` | Shuffle data written | — |
| `spark_jvm_gc_time_ms` | GC time per executor | > 5s/min |
| `spark_task_runtime_ms` | Task runtime distribution | P95 > 30s |
| `spark_streaming_batch_processing_time_seconds` | Streaming batch latency | > 60s |

**Dashboard panels dự kiến:** Applications (running/completed/failed), Active workers, Cores/memory utilization, Executor count, Running/completed/failed tasks, Shuffle read/write bytes, GC time per executor, Task runtime distribution, DAG execution metrics, Streaming batch latency (nếu có Spark Streaming).

**Lý do:** Spark chạy batch jobs (aggregate 1m→1h, Iceberg maintenance, backfill). Failed tasks → job fail → data gap. GC pressure → job slow → dagster schedule miss. Worker down → no job execution.

---

## 3. Cấu hình chi tiết

### 3.1 docker-compose.yml — Thay đổi

**MinIO:** Thêm `MINIO_PROMETHEUS_AUTH_TYPE=public` vào environment

**Kafka 1/2/3:** Thêm JMX agent:
```yaml
KAFKA_OPTS: "-javaagent:/jmx/jmx_prometheus_javaagent.jar=9999:/jmx/kafka-17x.yaml"
```
Volume: `config/jmx:/jmx:ro`

**Trino:** Thêm JMX agent:
```yaml
JVM_EXTRA_OPTS: "-javaagent:/etc/trino/jmx/jmx_prometheus_javaagent.jar=9404:/etc/trino/jmx/trino-442.yaml"
```
Volume: `config/jmx:/etc/trino/jmx:ro`

**Redis Exporter:** Container mới, profile: `["monitoring", "all"]`
- Image: `oliver006/redis_exporter:v1.61`
- Port: 9121
- Args: `--redis.addr=redis-master:6379`
- Depends on: `redis-master`

**Spark Master:** Mount `config/spark/metrics.properties` → `$SPARK_CONF_DIR/metrics.properties`

**Spark Worker:** Mount `config/spark/metrics.properties` → `$SPARK_CONF_DIR/metrics.properties`

### 3.2 prometheus.yml — scrape jobs mới

Thêm 9 scrape jobs:
- `minio` → `minio:9000/minio/v2/metrics/cluster`
- `trino` → `trino:9404/metrics`
- `redis` → `redis-exporter:9121`
- `kafka-jvm-1` → `kafka-1:9999/metrics`
- `kafka-jvm-2` → `kafka-2:9999/metrics`
- `kafka-jvm-3` → `kafka-3:9999/metrics`
- `spark-master` → `spark-master:8090/metrics/master/prometheus`
- `spark-worker` → `spark-worker:8091/metrics/prometheus`

### 3.3 Grafana Dashboards

5 file JSON mới trong `config/grafana/dashboards/`:

1. `minio-dashboard.json` — MinIO native metrics
2. `trino-dashboard.json` — Trino JMX metrics
3. `redis-dashboard.json` — Redis exporter metrics
4. `kafka-jvm-dashboard.json` — Kafka JVM metrics (bổ sung kafka-health.json)
5. `spark-dashboard.json` — Spark Prometheus servlet metrics

---

## 4. Triển khai

```bash
# Build lại monitoring stack
docker compose up -d --profile monitoring

# Verify Prometheus targets
curl http://localhost:9090/api/v1/targets | jq '.data.activeTargets[].labels.job'

# Verify exporters
curl http://localhost:9000/minio/v2/metrics/cluster | head -5  # MinIO
curl http://localhost:9121/metrics | grep redis_up              # Redis
curl http://localhost:9404/metrics | grep jvm_memory             # Trino JMX
curl http://localhost:9999/metrics | grep jvm_memory             # Kafka JMX
curl http://localhost:8090/metrics/master/prometheus | grep spark # Spark Master
```

---

## 5. Metrics không cần thiết (loại bỏ)

- **MinIO:** `minio_ilm_transition_total`, `minio_bucket_replication_latency` — ILM/replication không dùng trong infra này
- **Trino:** `trino_catalog_*` metrics cho catalogs không dùng (chỉ có `iceberg`)
- **Redis:** `redis_cluster_*` metrics — cluster mode không dùng, dùng Sentinel
- **Kafka:** `kafka_controller_*` nếu không cần controller election metrics
- **Spark:** `spark_rdd_*` metrics — RDD API không dùng (dùng DataFrame)

---

## 6. File cần tạo/sửa

| File | Action |
|---|---|
| `docs/Monitoring.md` | Tạo mới |
| `config/jmx/kafka-17x.yaml` | Tạo mới |
| `config/jmx/trino-442.yaml` | Tạo mới |
| `config/spark/metrics.properties` | Tạo mới |
| `docker-compose.yml` | Sửa (MinIO env, Kafka/Trino JMX opts, Redis exporter, Spark volumes) |
| `docker/trino/entrypoint.sh` | Sửa (thêm JMX agent) |
| `docker/spark/entrypoint.sh` | Sửa (export SPARK_CONF_DIR) |
| `config/prometheus.yml` | Sửa (thêm 9 scrape jobs) |
| `config/grafana/dashboards/minio-dashboard.json` | Tạo mới |
| `config/grafana/dashboards/trino-dashboard.json` | Tạo mới |
| `config/grafana/dashboards/redis-dashboard.json` | Tạo mới |
| `config/grafana/dashboards/kafka-jvm-dashboard.json` | Tạo mới |
| `config/grafana/dashboards/spark-dashboard.json` | Tạo mới |
| `docs/TRACKING.md` | Sửa (changelog) |
