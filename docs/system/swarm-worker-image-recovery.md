# Swarm Worker Image Recovery

> Status: **Active runbook** — use whenever worker node tasks are stuck in
> `Shutdown Rejected … No such image: 172.31.37.193:5000/…` after deploy.

## Symptom

```
$ docker service ps cryptoprice_flink-jobmanager
ID    NAME                            IMAGE                                          NODE             DESIRED STATE   CURRENT STATE            ERROR
xxxx  cryptoprice_flink-jobmanager.1  172.31.37.193:5000/cryptoprice/flink:1.18.1  ip-172-31-9-171  Running        Shutdown 2 minutes ago  "No such image: …"
```

Swarm schedules the task onto the worker (`ip-172-31-9-171`), but the
worker cannot pull from the manager-local registry (`172.31.37.193:5000`).
The task loop spins forever because the registry is not exposed across nodes.

## Why the registry is unreachable

The 2-node cluster runs a registry **as a Swarm service** on the manager node
(`.efs/LMView/scripts/deploy_aws_swarm.sh` deploys `registry:2` with a
published port to the manager IP). Worker-to-manager traffic for port 5000 is
either blocked by the AWS security group or by the overlay-network policy.
There is no DNS alias, so Swarm always asks the worker to pull directly.

## Recovery path

### Option A — Direct pull (preferred, ~30 s)

Open the security group between the two private IPs:

```
Manager SG  ingress  TCP 5000  ←  Worker private IP
Worker  SG  egress  TCP 5000  ←  Manager private IP
```

Then on the worker:

```bash
docker pull 172.31.37.193:5000/cryptoprice/flink:1.18.1
# expect: Status: Downloaded newer image for …
```

If that works, the swarm will pick the image up automatically on the next
`--force`. Jump to [Restart services](#restart-services).

### Option B — Save/scp/load (fallback, ~5 min)

Use when the SG can't be changed (compliance, change freeze). Both
scripts run from the **manager** node, which has the images locally:

```bash
bash scripts/sync_worker_images.sh
bash scripts/restart_swarm_services.sh
```

`sync_worker_images.sh` does:

1. Probe `ssh ubuntu@172.31.9.171 "docker pull …"` — if that succeeds, exit 0.
2. Otherwise, for each image: `docker save` → `scp` to `${STAGE_DIR}` →
   `ssh … docker load` → `ssh … docker tag <local> <registry-prefixed>`.
3. Verify with `docker images | grep …`.

`restart_swarm_services.sh` then iterates the failing services:

| Service                       | Why it was down                                       |
| ----------------------------- | ----------------------------------------------------- |
| `flink-jobmanager` / `-taskmanager` | Image missing on worker                          |
| `spark-master` / `-worker` / `-worker-2` / `-submit` | Image missing on worker       |
| `trino`                       | Image missing on worker                               |
| `auto-submit-jobs`            | Image missing (uses flink image)                      |
| `dagster-daemon` / `-webserver` | Image missing                                      |
| `influx-backfill`             | Image missing                                         |
| `finbert-worker`              | Image missing                                         |
| `prometheus`                  | Exit 137 (OOM) — capped at `--limit-memory 256M`      |
| `ai-service`                  | Rebuilt locally as `lmview-ai-service:latest`         |

…and finishes with a UI-probe + indicator freshness check.

## Restart services

After image sync (either option), force-restart:

```bash
bash scripts/restart_swarm_services.sh --prometheus-mem 256M
```

Expected output once healthy:

```
✅ Flink reachable at http://172.31.37.193:8081/overview (HTTP 200)
✅ Spark master reachable at http://172.31.37.193:8082/ (HTTP 200)
✅ Trino reachable at http://172.31.37.193:8083/ (HTTP 200)
```

`/overview` should report `taskmanagers ≥ 1, slots-total ≥ 12`.

## Verify end-to-end

Once Flink jobs are submitted (`auto-submit-jobs` Swarm service runs
`auto_submit_jobs.sh`):

```bash
docker exec $(docker ps -q -f name=redis-master) \
  redis-cli HGETALL indicator:latest:binance:BTCUSDT
```

Required fields for a healthy indicator:

| Field          | Source            | Tolerance              |
| -------------- | ----------------- | ---------------------- |
| `sma20`        | Flink             | > 0                    |
| `ema12`        | Flink             | > 0                    |
| `rsi14`        | Flink             | 0..100                 |
| `macd`         | Flink             | any                    |
| `computed_at`  | Flink write-time  | within last 120 s      |

If `computed_at` is stale (>2 min), Flink is reading from Kafka but not
writing to Redis — check `docker logs cryptoprice_flink-taskmanager.1 | tail`
and confirm Kafka offset via:

```bash
docker exec $(docker ps -q -f name=kafka-1) kafka-consumer-groups \
  --bootstrap-server localhost:9092 \
  --group flink \
  --describe
```

## Related files

- `scripts/sync_worker_images.sh` — auto save/scp/load/tag
- `scripts/restart_swarm_services.sh` — auto force-restart + UI probe
- `docs/system/07-docker-infrastructure.md` — Swarm topology
- `docs/system/12-deployment.md` — full deploy flow
- `docs/KẾ HOẠCH KHẮC PHỤC - INDICATOR PIPELINE.md` — indicator recovery context

## Known gaps

1. **No automatic re-sync** — If a worker is replaced or a new image is
   pushed, this runbook must be re-run by hand. A scheduled cron job
   inside `job_watchdog.py` would close that gap.
2. **Prometheus memory is fixed at 256 MB** — sufficient for short
   retention but may need raising when scrape targets grow.
3. **`auto_submit_jobs.sh` does not submit Spark** — see
   `docs/system/14-scripts.md`. Lakehouse gold tables stay empty until
   that script is extended.
