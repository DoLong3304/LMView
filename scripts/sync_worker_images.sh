#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# sync_worker_images.sh — Mirror missing Swarm images from manager to worker
# ─────────────────────────────────────────────────────────────────────────────
# Background:
#   Worker node (172.31.9.171) cannot pull from the manager-local registry
#   (172.31.37.193:5000). Swarm retries get "No such image" forever and
#   Flink/Spark/Trino tasks stay Shutdown-Rejected. This script automates
#   the manual recovery:
#
#     1. Try `docker pull` from worker (works once the registry firewall is
#        opened between nodes).
#     2. Fall back to `docker save` on manager → scp → `docker load` on
#        worker, then `docker tag` so Swarm's image name matches.
#
# Usage:
#   bash scripts/sync_worker_images.sh [--dry-run] [--worker USER@HOST]
#
# Defaults: worker = ubuntu@<WORKER_HOST>, registry = <REGISTRY_HOST>
# Override via env vars or CLI flags. Examples:
#   WORKER_HOST=ubuntu@10.0.1.20 REGISTRY_HOST=10.0.1.10:5000 bash scripts/sync_worker_images.sh
# ─────────────────────────────────────────────────────────────────────────────
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# ── Args ────────────────────────────────────────────────────────────────────
DRY_RUN=false
WORKER_HOST="${WORKER_HOST:-ubuntu@172.31.9.171}"
REGISTRY_HOST="${REGISTRY_HOST:-172.31.37.193:5000}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --dry-run)        DRY_RUN=true; shift ;;
    --worker)         WORKER_HOST="$2"; shift 2 ;;
    --registry)       REGISTRY_HOST="$2"; shift 2 ;;
    -h|--help)
      sed -n '2,28p' "$0"; exit 0 ;;
    *) echo "Unknown arg: $1" >&2; exit 2 ;;
  esac
done

# ── Color helpers ────────────────────────────────────────────────────────────
RED=$'\033[0;31m'; GREEN=$'\033[0;32m'; YELLOW=$'\033[1;33m'
CYAN=$'\033[0;36m'; NC=$'\033[0m'
log()  { printf "${CYAN}[sync]${NC} %s\n" "$*"; }
ok()   { printf "${GREEN}[sync]${NC} ✅ %s\n" "$*"; }
warn() { printf "${YELLOW}[sync]${NC} ⚠️  %s\n" "$*"; }
err()  { printf "${RED}[sync]${NC} ❌ %s\n" "$*" >&2; exit 1; }

run() {
  if $DRY_RUN; then
    printf "${YELLOW}[dry-run]${NC} %s\n" "$*"
  else
    eval "$@"
  fi
}

# ── Image list (must mirror docker-compose.swarm.yml images) ────────────────
# Each entry: "local_tag  remote_tag"
IMAGES=(
  "cryptoprice/flink:1.18.1            cryptoprice/flink:1.18.1"
  "cryptoprice/spark:3.5.5             cryptoprice/spark:3.5.5"
  "cryptoprice/spark-submit:local      cryptoprice/spark-submit:local"
  "cryptoprice/trino:442               cryptoprice/trino:442"
  "cryptoprice/dagster:1.8.10          cryptoprice/dagster:1.8.10"
  "cryptoprice/influx-backfill:0.25.0  cryptoprice/influx-backfill:0.25.0"
  "python:3.11-slim                    python:3.11-slim"
)

# ── Step 1: Probe worker → registry reachability ─────────────────────────────
log "Probing ${WORKER_HOST} → ${REGISTRY_HOST} reachability…"
if $DRY_RUN; then
  warn "DRY-RUN: skipping ssh probe"
else
  if ssh -o BatchMode=yes -o ConnectTimeout=5 "$WORKER_HOST" \
        "docker pull ${REGISTRY_HOST}/cryptoprice/flink:1.18.1" >/tmp/sync_probe.log 2>&1; then
    ok "Worker can pull directly from registry — manual recovery NOT needed."
    exit 0
  fi
  warn "Direct pull failed (see /tmp/sync_probe.log). Falling back to save/scp/load."
fi

# ── Step 2: docker save on manager → scp to worker ───────────────────────────
STAGE_DIR="/tmp/lmview-sync-$(date +%s)"
mkdir -p "$STAGE_DIR"

declare -A REMOTE_TAGS
for pair in "${IMAGES[@]}"; do
  local_tag="${pair%% *}"
  remote_short="${pair##* }"
  REMOTE_TAGS["$local_tag"]="$remote_short"

  archive="${STAGE_DIR}/$(echo "$remote_short" | tr '/:' '__').tgz"
  log "Saving ${local_tag} → ${archive}"
  run "docker save '${local_tag}' -o '${archive}'"

  log "Copying ${archive##*/} → ${WORKER_HOST}:${archive}"
  run "scp '${archive}' '${WORKER_HOST}:${archive}'"
done

# ── Step 3: docker load + tag on worker ─────────────────────────────────────
for pair in "${IMAGES[@]}"; do
  local_tag="${pair%% *}"
  remote_short="${REMOTE_TAGS[$local_tag]}"
  archive="${STAGE_DIR}/$(echo "$remote_short" | tr '/:' '__').tgz"

  log "Loading ${archive##*/} on ${WORKER_HOST}"
  run "ssh '${WORKER_HOST}' \"docker load -i '${archive}'\""

  remote_full="${REGISTRY_HOST}/${remote_short}"
  log "Tagging ${local_tag} → ${remote_full}"
  run "ssh '${WORKER_HOST}' \"docker tag '${local_tag}' '${remote_full}'\""
done

# ── Step 4: Verify ───────────────────────────────────────────────────────────
log "Verifying images present on worker…"
verify_cmd='docker images --format "{{.Repository}}:{{.Tag}}" | grep -E "flink:1.18|spark:3.5|trino:442|dagster:1.8|influx-backfill|python:3.11-slim" | sort'
run "ssh '${WORKER_HOST}' \"${verify_cmd}\""

# ── Step 5: Cleanup ──────────────────────────────────────────────────────────
log "Cleaning up local stage dir ${STAGE_DIR}"
run "rm -rf '${STAGE_DIR}'"
run "ssh '${WORKER_HOST}' 'rm -rf ${STAGE_DIR}'"

ok "Worker image sync complete. Next: bash scripts/restart_swarm_services.sh"
