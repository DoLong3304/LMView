#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# restart_swarm_services.sh — Force-restart failed Swarm services and verify
# ─────────────────────────────────────────────────────────────────────────────
# Use this AFTER scripts/sync_worker_images.sh has mirrored images onto the
# worker node. It issues `docker service update --force` for every service
# that was failing with "No such image" or OOM and then prints a state table
# + UI health checks.
#
# Usage:
#   bash scripts/restart_swarm_services.sh [--dry-run] [--prometheus-mem 256M]
#
# Defaults:
#   STACK_NAME = cryptoprice
#   PROMETHEUS_MEM = 256M
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ── Args ────────────────────────────────────────────────────────────────────
DRY_RUN=false
PROMETHEUS_MEM="256M"
STACK_NAME="${STACK_NAME:-cryptoprice}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)           DRY_RUN=true; shift ;;
    --prometheus-mem)    PROMETHEUS_MEM="$2"; shift 2 ;;
    --stack)             STACK_NAME="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── Color helpers ────────────────────────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'; NC=$'\033[0m'
log()  { printf "${CYAN}[restart]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[restart]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[restart]${NC} ⚠️  %s\n" "$*"; }
err()  { printf "${RED}[restart]${NC} ❌ %s\n" "$*" >&2; }

run() {
  if $DRY_RUN; then
    printf "${YELLOW}[dry-run]${NC} %s\n" "$*"
  else
    eval "$@"
  fi
}

# ── Service list ─────────────────────────────────────────────────────────────
# Order matters: Flink first (canonical indicator), then Spark, Trino, others.
SERVICES=(
  "${STACK_NAME}_flink-jobmanager"
  "${STACK_NAME}_flink-taskmanager"
  "${STACK_NAME}_spark-master"
  "${STACK_NAME}_spark-worker"
  "${STACK_NAME}_spark-worker-2"
  "${STACK_NAME}_spark-submit"
  "${STACK_NAME}_trino"
  "${STACK_NAME}_auto-submit-jobs"
  "${STACK_NAME}_dagster-daemon"
  "${STACK_NAME}_dagster-webserver"
  "${STACK_NAME}_influx-backfill"
  "${STACK_NAME}_finbert-worker"
)

# ── Pre-flight ──────────────────────────────────────────────────────────────
log "Pre-flight: are we on a Swarm manager?"
if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
  err "Docker Swarm not active on this node. Run on manager 172.31.37.193."
fi
if ! docker node ls >/dev/null 2>&1; then
  err "Cannot query Swarm nodes — manager role required."
fi
ok "Running on Swarm manager."

# ── Step 1: Patch Prometheus memory limit if it keeps OOM-ing ───────────────
log "Patching ${STACK_NAME}_prometheus memory limit to ${PROMETHEUS_MEM}"
run "docker service update --limit-memory '${PROMETHEUS_MEM}' '${STACK_NAME}_prometheus'" || \
  warn "Failed to patch prometheus memory limit (may be unsupported on this engine)."

# ── Step 2: Force restart every failing service ─────────────────────────────
log "Force-restarting ${#SERVICES[@]} services…"
for svc in "${SERVICES[@]}"; do
  log "  → ${svc}"
  if ! docker service inspect "$svc" >/dev/null 2>&1; then
    warn "    service does not exist, skipping"
    continue
  fi
  run "docker service update --force '${svc}'" || warn "    update --force failed for ${svc}"
done

# ── Step 3: Wait for tasks to settle ─────────────────────────────────────────
log "Sleeping 25s for Swarm to reschedule tasks…"
run "sleep 25"

# ── Step 4: State table ──────────────────────────────────────────────────────
log "Service state:"
run "docker service ls --format 'table {{.Name}}\t{{.Image}}\t{{.Replicas}}\t{{.Ports}}' \
  | grep -E 'flink|spark|trino|prometheus|auto-submit|dagster|influx-backfill|finbert|ai-service'"

# ── Step 5: UI probes ────────────────────────────────────────────────────────
probe() {
  local url="$1"; local label="$2"
  local code
  code=$(curl -s -o /dev/null -w '%{http_code}' -m 5 "$url" || echo "000")
  if [[ "$code" == "200" ]]; then
    ok "${label} reachable at ${url} (HTTP ${code})"
  else
    warn "${label} NOT healthy at ${url} (HTTP ${code})"
  fi
}
log "Probing UIs…"
probe "http://172.31.37.193:8081/overview" "Flink"
probe "http://172.31.37.193:8082/"          "Spark master"
probe "http://172.31.37.193:8083/"          "Trino"

# ── Step 6: Indicator freshness (only meaningful after Flink jobs land) ─────
log "Checking Redis indicator freshness (may be empty until jobs land)…"
run "docker exec \$(docker ps -q -f name=redis-master) \
  redis-cli HGETALL 'indicator:latest:binance:BTCUSDT' || true"

ok "Restart pass complete. If services still Shutdown-Rejected, re-run sync_worker_images.sh."
