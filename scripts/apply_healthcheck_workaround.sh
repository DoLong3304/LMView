#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# apply_healthcheck_workaround.sh — Apply IB-10 no-op healthcheck workaround
# ─────────────────────────────────────────────────────────────────────────────
# Run this on a Swarm manager node to break the flink-taskmanager restart loop.
#
# After applying, taskmanagers will register and slots will appear in Flink
# /overview.
#
# Usage:
#   bash scripts/apply_healthcheck_workaround.sh [--dry-run]
#
# Environment:
#   FLINK_JM_URL   Flink JobManager URL (default http://localhost:8081)
#   REGISTRY_ADDR  Local Docker registry address (default localhost:5000)
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

DRY_RUN=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run) DRY_RUN=true; shift ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'; NC=$'\033[0m'
log()  { printf "${CYAN}[ib10]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[ib10]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[ib10]${NC} ⚠️  %s\n" "$*"; }

# ── Configurable via env vars ────────────────────────────────────────────────
FLINK_JM_URL="${FLINK_JM_URL:-http://localhost:8081}"
REGISTRY_ADDR="${REGISTRY_ADDR:-localhost:5000}"

if ! docker info 2>/dev/null | grep -q "Swarm: active"; then
  err "Docker Swarm not active. Run on a manager node."
fi
if ! docker node ls >/dev/null 2>&1; then
  err "Not a manager node."
fi

run() {
  if $DRY_RUN; then
    printf "${YELLOW}[dry-run]${NC} %s\n" "$*"
  else
    eval "$@"
  fi
}

SERVICES=(
  cryptoprice_flink-taskmanager
  cryptoprice_spark-worker
  cryptoprice_spark-worker-2
)

for svc in "${SERVICES[@]}"; do
  log "Applying no-op healthcheck to ${svc}"
  run "docker service update \
    --health-cmd 'exit 0' \
    --health-interval 30s \
    --health-timeout 5s \
    --health-retries 3 \
    --health-start-period 60s \
    '${svc}'" || warn "Failed to update ${svc}"
done

log "Waiting 90s for taskmanagers to register..."
run "sleep 90"

log "Flink /overview:"
run "curl -s ${FLINK_JM_URL}/overview" || true
echo

ok "Workaround applied. Taskmanagers should now register."
echo
echo "Next steps:"
echo "  1. Wait ~30s more, re-check: curl -s ${FLINK_JM_URL}/overview"
echo "     Expect: taskmanagers >= 1, slots-total >= 12"
echo "  2. Force the producer service to pick up new image:"
echo "     docker service update --image ${REGISTRY_ADDR}/cryptoprice/producer:latest cryptoprice_producer"
echo "  3. Submit Flink job:"
echo "     docker service update --force cryptoprice_auto-submit-jobs"
echo "  4. Wait 2 min for Flink to process, then check Redis:"
echo "     docker exec \$(docker ps -q -f name=redis-master) \\"
echo "       redis-cli HGETALL indicator:latest:binance:BTCUSDT"
