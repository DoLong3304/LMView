#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# watchdog_flink_job.sh — Keep Flink pipeline running despite TM churn
# ─────────────────────────────────────────────────────────────────────────────
# Background-loop that:
#   1. Polls Flink /overview every 30s
#   2. If jobs-running=0 AND slots-available>0, submits the pipeline
#   3. If SOLUSDT indicator hash has 30 fields (=Flink is processing), log OK
#
# Run on any node that can reach the Flink jobmanager. Designed to run
# as a long-running container on the worker until IB-10 is fully fixed.
#
# Usage:
#   bash scripts/watchdog_flink_job.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

FLINK_JM_URL="${FLINK_JM_URL:-http://172.31.37.193:8081}"
REDIS_HOST="${REDIS_HOST:-redis-master}"
INTERVAL="${WATCHDOG_INTERVAL:-30}"

CYAN=$'\033[0;36m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'
log()  { printf "${CYAN}[watchdog]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[watchdog]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[watchdog]${NC} ⚠️  %s\n" "$*"; }

submit_job() {
  log "Submitting Flink pipeline..."
  docker run --rm \
    -v "$PROJECT_ROOT:/mnt/efs/LMView:ro" \
    172.31.37.193:5000/cryptoprice/flink:1.18.1 \
    bash -c "
      flink run \
        -m 172.31.37.193:8081 \
        -d \
        -pyfs /mnt/efs/LMView/src/processing \
        --pyFiles /mnt/efs/LMView/deps.zip \
        --python /mnt/efs/LMView/src/processing/pipeline.py
    " 2>&1 | tail -3
}

build_deps_zip() {
  if [[ ! -f "$PROJECT_ROOT/deps.zip" ]]; then
    log "Building deps.zip..."
    docker run --rm \
      -v "$PROJECT_ROOT:/mnt/efs/LMView:ro" \
      172.31.37.193:5000/cryptoprice/flink:1.18.1 \
      bash -c "
        SRC_DIR=/mnt/efs/LMView/src bash /mnt/efs/LMView/scripts/build_deps_zip.sh
      " 2>&1 | tail -3
  fi
}

get_overview() {
  curl -sf -m 5 "${FLINK_JM_URL}/overview" 2>/dev/null || echo ""
}

get_jobs_running() {
  curl -sf -m 5 "${FLINK_JM_URL}/jobs" 2>/dev/null \
    | python3 -c "import json,sys; d=json.load(sys.stdin); print(sum(1 for j in d.get('jobs',[]) if j.get('status')=='RUNNING'))" 2>/dev/null \
    || echo 0
}

check_indicator() {
  docker run --rm --network l6h3sfu6zqmf \
    172.31.37.193:5000/cryptoprice/producer:0.25.60 \
    python3 -c "
import socket
def cmd(*args):
    s = socket.socket(); s.connect(('${REDIS_HOST}', 6379))
    out = '*%d\\r\\n' % len(args)
    for a in args:
        a = str(a); out += '\$%d\\r\\n%s\\r\\n' % (len(a), a)
    s.send(out.encode())
    return s.recv(64).decode(errors='replace').strip()
print(cmd('HLEN', 'indicator:latest:binance:SOLUSDT').lstrip(':'))
" 2>&1 | tail -1
}

build_deps_zip

log "Starting watchdog loop (interval=${INTERVAL}s)..."
while true; do
  OVERVIEW=$(get_overview)
  if [[ -z "$OVERVIEW" ]]; then
    warn "Flink not reachable"
    sleep "${INTERVAL}"
    continue
  fi

  TASKMANAGERS=$(echo "$OVERVIEW" | python3 -c "import json,sys; print(json.load(sys.stdin).get('taskmanagers',0))")
  SLOTS_AVAIL=$(echo "$OVERVIEW" | python3 -c "import json,sys; print(json.load(sys.stdin).get('slots-available',0))")
  JOBS_RUNNING=$(get_jobs_running)

  log "TMs=$TASKMANAGERS slots_available=$SLOTS_AVAIL jobs_running=$JOBS_RUNNING"

  if [[ "$JOBS_RUNNING" == "0" && "$SLOTS_AVAIL" -gt 0 ]]; then
    warn "No Flink jobs running but $SLOTS_AVAIL slots free → resubmitting"
    submit_job
  fi

  INDICATOR_FIELDS=$(check_indicator)
  if [[ "${INDICATOR_FIELDS:-0}" -gt 0 ]]; then
    ok "SOLUSDT indicator has $INDICATOR_FIELDS fields (Flink pipeline processing)"
  else
    log "SOLUSDT indicator not yet populated (needs ~20 1m candles warmup)"
  fi

  sleep "${INTERVAL}"
done
