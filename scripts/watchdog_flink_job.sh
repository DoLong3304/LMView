#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# watchdog_flink_job.sh — Keep Flink pipeline running despite TM churn
# ─────────────────────────────────────────────────────────────────────────────
# Background-loop that polls Flink /overview every 30s. If jobs=0 AND
# slots>0, submits the pipeline.
#
# Usage:
#   bash scripts/watchdog_flink_job.sh
#
# Env vars (all optional):
#   FLINK_JM_URL   Flink JobManager URL (default http://localhost:8081)
#   REDIS_HOST     Redis hostname (default redis-master)
#   FLINK_IMAGE    Flink image tag (default localhost:5000/cryptoprice/flink:1.18.1)
#   WATCHDOG_INTERVAL  Poll interval seconds (default 30)
#   PROJECT_DIR    Project root (default: script's parent dir)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

FLINK_JM_URL="${FLINK_JM_URL:-http://localhost:8081}"
REDIS_HOST="${REDIS_HOST:-redis-master}"
FLINK_IMAGE="${FLINK_IMAGE:-localhost:5000/cryptoprice/flink:1.18.1}"
INTERVAL="${WATCHDOG_INTERVAL:-30}"

CYAN=$'\033[0;36m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'; NC=$'\033[0m'
log()  { printf "${CYAN}[watchdog]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[watchdog]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[watchdog]${NC} ⚠️  %s\n" "$*"; }

# Extract host:port from FLINK_JM_URL (strip protocol prefix)
FLINK_HOST="${FLINK_JM_URL#http://}"
FLINK_HOST="${FLINK_HOST#https://}"

submit_job() {
  log "Submitting Flink pipeline..."
  docker run --rm \
    -v "$PROJECT_ROOT:${PROJECT_ROOT}:ro" \
    "${FLINK_IMAGE}" \
    bash -c "
      flink run \
        -m ${FLINK_HOST} \
        -d \
        -pyfs ${PROJECT_ROOT}/src/processing \
        --pyFiles ${PROJECT_ROOT}/deps.zip \
        --python ${PROJECT_ROOT}/src/processing/pipeline.py
    " 2>&1 | tail -3
}

build_deps_zip() {
  if [[ ! -f "${PROJECT_ROOT}/deps.zip" ]]; then
    log "Building deps.zip..."
    docker run --rm \
      -v "$PROJECT_ROOT:${PROJECT_ROOT}:ro" \
      "${FLINK_IMAGE}" \
      bash -c "
        SRC_DIR=${PROJECT_ROOT}/src bash ${PROJECT_ROOT}/scripts/build_deps_zip.sh
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
  python3 -c "
import socket
s = socket.socket(); s.settimeout(3)
try:
    s.connect(('${REDIS_HOST}', 6379))
    cmd = '*2\r\n\$4\r\nHLEN\r\n\${len('indicator:latest:binance:SOLUSDT')}\r\nindicator:latest:binance:SOLUSDT\r\n'
    s.send(cmd.encode())
    out = s.recv(64).decode(errors='replace').strip()
    print(out.lstrip(':'))
finally:
    s.close()
" 2>&1 | tail -1
}

build_deps_zip

log "Starting watchdog loop (interval=${INTERVAL}s)..."
while true; do
  OVERVIEW=$(get_overview)
  if [[ -z "$OVERVIEW" ]]; then
    warn "Flink not reachable at ${FLINK_JM_URL}"
    sleep "${INTERVAL}"
    continue
  fi

  TASKMANAGERS=$(echo "$OVERVIEW" | python3 -c "import json,sys; print(json.load(sys.stdin).get('taskmanagers',0))")
  SLOTS_AVAIL=$(echo "$OVERVIEW" | python3 -c "import json,sys; print(json.load(sys.stdin).get('slots-available',0))")
  JOBS_RUNNING=$(get_jobs_running)

  log "TMs=$TASKMANAGERS slots_available=$SLOTS_AVAIL jobs_running=$JOBS_RUNNING"

  if [[ "$JOBS_RUNNING" == "0" && "$SLOTS_AVAIL" -gt 0 ]]; then
    warn "No Flink jobs running but $SLOTS_AVAIL slots free -> resubmitting"
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
